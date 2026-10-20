from atguigu.app.models.models import Base
from atguigu.common.event_loop import run_async

from atguigu.infrastructure.db import async_engine


async def init_database() -> None:
    """创建当前服务 ORM 模型声明的数据库表和索引。"""
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    run_async(init_database())
