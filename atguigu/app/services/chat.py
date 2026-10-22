from datetime import timedelta
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from atguigu.app.models.enums import MessageRole, ConversationMode, TurnStatus
from atguigu.app.models.models import Message, Conversation, ConversationTurn
from atguigu.app.schemas import ChatMessageRequest
from atguigu.app.services.admin import HandoffService
from atguigu.app.services.realtime import RealtimeService
from atguigu.common.settings import get_settings
from atguigu.common.utils import get_utcnow, get_uid


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()
        self._realtime_service = RealtimeService(session)
        self._handoff_service = HandoffService(session)

    async def get_chat_history(self, user_id: str) -> dict[str, Any]:
        """
        职责：获取历史对话
        返回当前用户所有的会话下对应的消息
        user_001: 之前会话 conv1(msg1/msg2/msg3: CLOSED)  当前会话conv2(msg4/msg5/msg6:[AI/QUEUED/HUMAN])
        :param user_id:
        :return:
        """

        # 1. 获取会话
        current_conversation = await  self._get_or_create_conversation(user_id)

        # 1. 定义查询当前用户所有的会话下对应的消息SQL语句
        stmt = (select(Message).join(Conversation, Conversation.id == Message.conversation_id).where(
            Conversation.user_id == user_id)
                .order_by(Message.id))

        # 2. 执行SQL语句
        records = (await self._session.scalars(stmt)).all()

        # 3. 构建最终前端需要的消息结构
        messages = [
            {
                "conversation_id": record.conversation_id,
                "role": record.role,
                "content": record.content
            }
            for record in records
        ]
        await self._session.commit()
        # 4. 返回
        return {
            "conversation_id": current_conversation.id,  # 当前会话ID
            "conversation_mode": current_conversation.mode,  # 当前会话模式
            "messages": messages
        }

    async def process_chat_message(self, payload: ChatMessageRequest, user_id: str):
        """
        职责：
        处理用户的消息
        1. 获取会话
        2. 创建消息
        3. 根据会话模式[AI OR QUEUED HUMAN]，选择是否需要创建Turn、实时通知客服
        4. 最终提交
        :param payload:
        :param user_id:
        :return:
        """

        # 1. 重复消息校验
        stmt = select(Message).where(Message.message_id == payload.message_id)

        message = await self._session.scalar(stmt)

        if message:
            return

        # 2. 获取会话
        conversation = await self._get_or_create_conversation(user_id)

        # 3. 创建消息
        message = Message(
            message_id=payload.message_id,
            conversation_id=conversation.id,
            role=MessageRole.USER,
            message_type=payload.type,
            content=payload.content
        )

        # 4. 保存消息到数据库
        self._session.add(message)
        # 5. 修改会话的最后一次活跃时间
        conversation.last_active_at = get_utcnow()

        # 6. 会话模式分流
        if conversation.mode == ConversationMode.AI:
            # a) 创建Turn
            await self._get_or_create_turn(conversation)

        else:  # QUEUE  HUMAN
            # b) 实时通知【管理端】
            self._realtime_service.add_event(message, conversation, notify_user=False, notify_staff=True)

        # 7. 统一提交
        await self._session.commit()

    async def _get_or_create_conversation(self, user_id: str) -> Conversation:
        """
        职责：获取或者创建有效的会话（CLOSED：无效的不需要）
        :param user_id:
        :return:
        """
        # 1. 定义有效会话SQL语句
        stmt = select(Conversation).where(Conversation.user_id == user_id,
                                          Conversation.mode != ConversationMode.CLOSED).with_for_update()

        # 2. 查询有效会话
        conversation = await self._session.scalar(stmt)

        # 3. 判断会话是否存在
        if conversation:
            # AI(校验AI模式下会话超时) QUEUED HUMAN(人工无需校验超时)
            # a) 校验一下是否过期了【懒加载思想】 如果会话过期了，修改会话的模式为CLOSED 如果会话没过期【有效】，可以直接返回
            timeout = timedelta(minutes=self._settings.conversation_idle_timeout_minutes)
            if conversation.mode == ConversationMode.AI and get_utcnow() - conversation.last_active_at >= timeout:
                conversation.mode = ConversationMode.CLOSED
            else:
                return conversation
        # id 单独赋值的原因是 后面message需要关联会话ID
        conversation = Conversation(id=get_uid("conv"), user_id=user_id, mode=ConversationMode.AI)

        # 4.保存会话到数据库
        self._session.add(conversation)

        # 5. 返回有效的会话
        return conversation

    async def _get_or_create_turn(self, conversation: Conversation) -> ConversationTurn:
        """
        职责：
        创建获取不创建处于COLLECTIONG状态的Turn
        返回turn
        :param conversation:
        :return:
        """
        # 1. 定义查询轮次的SQL语句
        stmt = select(ConversationTurn).where(ConversationTurn.conversation_id == conversation.id,
                                              ConversationTurn.status == TurnStatus.COLLECTING)

        # 2. 查询处于能收集消息状态的轮次
        collecting_turn = await self._session.scalar(stmt)

        # 3. 如果没有查询到待收集状态的轮次
        if collecting_turn is None:
            # a) 创建待收集状态的Turn
            collecting_turn = ConversationTurn(conversation_id=conversation.id,
                                               status=TurnStatus.COLLECTING,
                                               collect_until=get_utcnow() + timedelta(
                                                   milliseconds=self._settings.message_merge_delay_ms)
                                               )
            # b) 保存轮次到数据库中
            self._session.add(collecting_turn)
        return collecting_turn

    async def claim_turn(self) -> tuple[ConversationTurn, dict[str, Any], str] | None:
        """
        职责：
        1. 领取轮次
        1.1 领取不到，直接返回None
        1.2 领取到，构建AI Service需要的请求数据（payload）
        2. 返回 领取到的轮次、payload、用户ID
        :return:
        """

        # 1. 领取轮次
        # a) 定义领取轮次的SQL语句
        stmt = select(ConversationTurn).where(
            ConversationTurn.status == TurnStatus.COLLECTING,
            ConversationTurn.collect_until <= get_utcnow()
        )
        # b) 执行SQL语句
        claimed_turn = await self._session.scalar(stmt)

        # 2. 如果没有领取到，直接返回None
        if claimed_turn is None:
            return None

        # 3. 查询当前轮次对应的会话
        conversation = await  self._session.scalar(
            select(Conversation).where(Conversation.id == claimed_turn.conversation_id).with_for_update())

        # 4. 查询当前会话对应的用户角色最新消息ID
        latest_user_message_id = await self._get_latest_user_message_id(str(conversation.id))

        # 3. 修改轮次的状态（RUNNING）以及当前轮次的快照消息ID
        claimed_turn.status = TurnStatus.RUNNING
        claimed_turn.snapshot_message_id = latest_user_message_id  # 确定本轮消息的下限
        claimed_turn.attempts += 1

        # 4. 构建payload  # 1. 当前会话ID 2.当前消息  3.本轮之外的消息【Q:用户消息/A【普通AI回复、人工回复】】历史消息留下30条
        payload: dict[str, Any] = await self._build_request_payload(claimed_turn, conversation)

        # 5. 提交(数据修改)
        await self._session.commit()

        # 6. 返回
        return claimed_turn, payload, cast(str, conversation.user_id)

    async def _get_latest_user_message_id(self, conversation_id: str) -> int:
        """
        职责：找到当前轮次对应会话的最新用户角色的消息ID
        :param conversation_id:
        :return:
        """

        stmt = select(func.max(Message.id)).where(Message.conversation_id == conversation_id,
                                                  Message.role == MessageRole.USER
                                                  )

        return await self._session.scalar(stmt)

    async def _build_request_payload(self,
                                     claimed_turn: ConversationTurn,
                                     conversation: Conversation) -> dict[str, Any]:
        """
        职责：构建AI Service需要的数据
        1. 当前消息---[Messages表中的主键ID [消息上限ID]   [消息下限ID] ]
        2. 历史消息---[截取、反转]
        :param claimed_turn:
        :param conversation:
        :return:
        """

        # 1. 构建当前消息
        # a) 定义当前消息的SQL语句
        stmt = select(func.max(Message.id)).where(Message.conversation_id == conversation.id,
                                                  Message.role != MessageRole.USER
                                                  )
        # b) 执行SQL语句获取消息上线ID
        latest_reply_id = await self._session.scalar(stmt) or 0

        # c) 定义查询当前轮次的消息的SQL语句
        messages_stmt = select(Message).where(
            Message.conversation_id == conversation.id,
            Message.id > latest_reply_id,
            Message.id <= claimed_turn.snapshot_message_id
        ).order_by(Message.id)

        # d)  执行SQL语句获取当前轮次的消息
        current_messages = (await self._session.scalars(messages_stmt)).all()

        # 2. 构建历史消息(决策：消息的条数：30条 消息最近（最新）)
        # a) 定义构建历史消息的SQL语句
        history_stmt = select(Message).where(
            Message.conversation_id == conversation.id,
            Message.id < current_messages[0].id).order_by(Message.id.desc()).limit(30)

        # b) 执行SQL语句获取历史消息
        history_messages = reversed((await self._session.scalars(history_stmt)).all())

        # 3. 返回载荷数据
        return {
            "conversation_id": conversation.id,
            "messages": [
                {
                    "role": message.role,
                    "type": message.message_type,
                    "content": message.content
                }
                for message in current_messages
            ],
            "history": [
                {
                    "type": history.message_type,
                    "role": history.role,
                    "content": history.content
                }
                for history in history_messages

            ]
        }

    async def finish_turn(self,
                          claimed_turn: ConversationTurn,
                          run_result: dict[str, Any] | None,
                          error: Exception | None):
        """
        职责：结算
        1. 修改轮次状态【COMPLETED FAILED SUPERSEDED】
        COMPLETED：  1. run_result有结果，error没有结果  2. 处理轮次期间，"没有"新的消息进入到会话
        SUPERSEDED： 1. run_result有结果，error没有结果  2. 处理轮次期间，"有"新的消息进入到会话
        FAILED：    1. run_result没有结果，error有结果  2. 重试次数达到了最大值

        2. 保存AI Service给的结果【类型1:普通AI 回复结果，类型2:转人工请求的回复结果】
        2.1 普通AI 回复结果；------最终保存到2张表即可
            保存到messages表【role:AI】 实时通知给用户【保存到realtime_events】表
        2.2 转人工请求 回复结果；------最终保存到3张表即可
            保存到messages表【role:AI】
            实时通知给“用户端”【保存到realtime_events】表；实时通知给“客服端”【保存到realtime_events】 让前端在客服端刷新工单列表【通知信号而已】
            创建工单信息（初始化工单记录：handoffs）

        :param claimed_turn:
        :param run_result:
        :param error:
        :return:
        """
        conversation = await self._session.scalar(
            select(Conversation).where(Message.conversation_id == claimed_turn.conversation_id).with_for_update())

        latest_user_message_id = await self._get_latest_user_message_id(str(conversation.id))

        # 1. 校验快照版本是否一致
        if claimed_turn.snapshot_message_id != latest_user_message_id:
            claimed_turn.status = TurnStatus.SUPERSEDED
            await   self._session.commit()
            return

        # 2. 异常
        if error is not None:
            # a）继续重试
            if claimed_turn.attempts < self._settings.ai_worker_max_attempts:
                claimed_turn.status = TurnStatus.COLLECTING
                claimed_turn.collect_until = get_utcnow() + self._settings.ai_worker_retry_delay_seconds  # AI-Service请求时间长一些
            # b) 不可以重试
            else:
                claimed_turn.status = TurnStatus.FAILED
                # 存储失败消息到messages表以及将失败的消息给用户
                await self._save_ai_reply(conversation, {"kind": "error", "text": "AI 服务不可用，请稍后重试."})

            await   self._session.commit()
            return

        # 3. 正常 （保存AI 回复或者转人工的请求）
        claimed_turn.status = TurnStatus.COMPLETED

        # 3.1 转人工的请求
        if run_result['reply_type'] == "REQUEST_HANDOFF":
            # a) 创建人工工单记录
            self._handoff_service.create_handoff()
            # b) 修改会话的模式 队列模式
            conversation.mode = ConversationMode.QUEUED

        # 3.2 普通AI 回复
        await self._save_ai_reply(conversation, run_result)

        # 4. 提交
        await   self._session.commit()

    async def _save_ai_reply(self,
                             conversation: Conversation,
                             content: dict[str, Any]):
        """
        职责：
        1. 存储AI 正常回复的消息 转人工的请求
        2. 存储realtime_events表
        :param conversation:
        :param content:
        :return:
        """

        # 1. 构建消息(对内)
        message = Message(
            message_id=get_uid("msg"),
            conversation_id=conversation.id,
            role=MessageRole.AI,
            message_type="text",
            content=content
        )
        conversation.last_active_at = get_utcnow()
        self._session.add(message)

        # 2. 构建实时的事件(对内)
        self._realtime_service.add_event(message,
                                         conversation,
                                         notify_user=True,
                                         notify_staff=conversation.mode == ConversationMode.QUEUED
                                         )
