import asyncio
import selectors
from asyncio import WindowsSelectorEventLoopPolicy

from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.exc import MissingGreenlet

from atguigu.common.settings import get_settings

# ==================== 1. 基础配置与 User 模型定义 ====================

engine = create_async_engine(url=get_settings().database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column(default=18)

    def __repr__(self) -> str:
        return f"User(id={self.id}, name='{self.name}', age={self.age})"


# ==================== 2. CRUD ====================

async def crud_demo(session: AsyncSession):
    print("\n1. 新增")
    user = User(name="张三", age=20)
    session.add(user)
    await session.commit()  # 直接 commit，内部会自动先 flush
    print(f"创建成功: {user}")

    print("\n2. 查询")
    stmt = select(User).where(User.name == "张三")
    db_user = await session.scalar(stmt)  # one or none
    print(f"查询结果: {db_user}")

    print("\n3. 修改")
    if db_user:
        db_user.age = 25
        await session.commit()
    print(f"修改后: {db_user}")

    # print("\n4. 删除")
    # if db_user:
    #     await session.delete(db_user)
    #     await session.commit()


# ==================== 3.expire_on_commit=True 与 False ====================

async def compare_expire_on_commit():
    # 1. expire_on_commit=True
    SessionExpireTrue = async_sessionmaker(engine, expire_on_commit=True)

    async with SessionExpireTrue() as session:
        user_tom = User(name="Tom", age=18)
        session.add(user_tom)

        # commit 成功后，因为 expire_on_commit=True，SQLAlchemy 会把 user_tom 内存里的属性全部清空（标记为过期）
        await session.commit()
        try:
            # 此时访问 user_a.id 或 user_a.name，SQLAlchemy 发现属性已过期，
            # 就会尝试在后台偷偷发起一次同步 SQL 查询去数据库重新拉取最新值。
            # 但在异步 (AsyncSession) 中不允许隐式发起同步 IO
            print(f"尝试在 commit 后直接读取属性: user_tom.id = {user_tom.id}")
        except MissingGreenlet as e:
            print(f"原因：commit 后属性已过期，异步环境禁止隐式发起同步查询！\n   报错详情: {e}")

        # 如果非要在 expire_on_commit=True 下读取，必须手动 await session.refresh(user_tom) 显式发起异步查询：
        await session.refresh(user_tom)
        print(f" {user_tom}\n")

    # 2. expire_on_commit=False
    SessionExpireFalse = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionExpireFalse() as session:
        user_jack = User(name="Jack", age=22)
        session.add(user_jack)

        # commit 成功后，因为 expire_on_commit=False，user_jack 内存里的属性依然保留，不会被清空
        await session.commit()

        # 此时直接读取属性，直接从 Python 内存里拿，不发任何 SQL
        print(f"直接读取成功，无需额外查询数据库: user_b.id = {user_jack.id}, 完整对象 = {user_jack}")


async def main():
    # 1. 初始化建表
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    # 2. 运行CRUD
    # async with AsyncSessionLocal() as session:
    #     await crud_demo(session)

    # 3. 运行 expire_on_commit 对比
    await compare_expire_on_commit()
    #
    # await engine.dispose()


if __name__ == "__main__":
    # 1. window下默认的事件循环【ProactorEventLoop】不能和psycopg驱动兼容。

    # asyncio.run(main())
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())  # 方案一
    asyncio.run(main())
    # asyncio.run(main(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))  # 方案二

    # asyncio.run(main(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
