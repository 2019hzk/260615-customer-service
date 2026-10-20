from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from atguigu.app.models.enums import MessageRole, ConversationMode, TurnStatus
from atguigu.app.models.models import Message, Conversation, ConversationTurn
from atguigu.app.schemas import ChatMessageRequest
from atguigu.app.services.realtime import RealtimeService
from atguigu.common.settings import get_settings
from atguigu.common.utils import get_utcnow, get_uid


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()
        self._realtime_service = RealtimeService(session)

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
        stmt = select(Conversation).where(Conversation.user_id == user_id, Conversation.mode != ConversationMode.CLOSED)

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
