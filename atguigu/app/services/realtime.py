from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.models.models import Message, Conversation, RealtimeEvent

""""
异步场景(压榨CPU)：
1. IO：读文件、写文件
2. 网络请求：（httpx:http/https）第三方
"""


class RealtimeService:

    def __init__(self, session: AsyncSession):
        self._session = session

    def add_event(self,
                  message: Message,
                  conversation: Conversation,
                  *,
                  notify_user: bool = False,
                  notify_staff: bool = False):
        """
        职责：像realtime_events表中插入实时发送的记录
        target:[用户端、管理端【客服】]

        :return:
        """

        # 1. 构建发送目标
        targets: list[str] = []
        if notify_user:
            targets.append(conversation.user_id)
        if notify_staff:
            targets.append("staff")

        # 2. 发送给某个通道的数据
        event_data = {
            "conversation_mode": conversation.mode,
            "role": message.role,
            "content": message.content
        }

        # 3. 插入实时的事件到realtime_events中
        for target in targets:
            self._session.add(RealtimeEvent(target=target, data=event_data))

        # 4. 不要提交
