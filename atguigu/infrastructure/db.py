"""
1. 创建引擎
2. 创建session工厂以及获取session对象
"""
from typing import AsyncGenerator
from logging import getLogger

logger = getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from atguigu.common.settings import get_settings

async_engine: AsyncEngine = create_async_engine(
    url=get_settings().database_url,
    echo=False
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    async_engine,
    expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """
    职责：利用异步生成器对象返回异步session对象
    为什么用yield 不用return
    :return:
    """

    async  with  async_session_factory() as session:
        try:
            yield session  # 请求处理完，fastapi自动执行yield后面逻辑（上下文的释放资源动作）
        except Exception as e:
            logger.error(f"操作数据库出现异常 原因:{str(e)}")
            await session.rollback()
            raise e  # 交给调用方
