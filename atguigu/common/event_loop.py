import asyncio
import selectors
from typing import Coroutine


def run_async(coro: Coroutine):
    """
    职责：利用自己的创建的事件循环执行协程对象
    :param coro:
    :return:
    """

    asyncio.run(coro, loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
