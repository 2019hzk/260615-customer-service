from sqlalchemy.ext.asyncio import AsyncSession


class HandoffService:

    def __init__(self, session: AsyncSession):
        self._session = session

    def create_handoff(self):
        """
        职责：初始化工单记录
        :return:
        """
        pass
