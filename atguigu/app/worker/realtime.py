"""

容器启动的时候，负责从realtime_events表中获取到未发布的事件

"""
import asyncio
import json
import logging

from redis import RedisError

from atguigu.app.services.realtime import RealtimeService
from atguigu.common.event_loop import run_async
from atguigu.infrastructure.db import async_session_factory
from atguigu.infrastructure.redis import redis_client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from atguigu.common.settings import get_settings


class RealtimeWorker:

    def __init__(self):
        self._settings = get_settings()
        self._session_factory = async_session_factory
        self._redis_client = redis_client

    async def start(self):
        logger.info("RealTime Worker 已经启动")
        while True:
            pulled = await self.pull_next_event()
            if not pulled:
                await asyncio.sleep(self._settings.realtime_worker_poll_interval_seconds)

    async def pull_next_event(self) -> bool:
        """
        职责：获取未发布的事件
        :return:
        """

        async  with   self._session_factory() as session:
            # 1. 实例化realtime service
            realtime_service = RealtimeService(session)

            # 2. 获取未发布的事件
            event = await realtime_service.get_unpublish_event()
            if event is None:
                return False

            # 3.获取发送数据
            event_json = json.dumps(event.data, ensure_ascii=False)

            # 4. 发送事件
            try:
                await self._redis_client.publish(event.target, event_json)
            except RedisError as error:
                logger.exception("Redis发布者出现了异常%s", str(error))
                return False

            # 5.更新发布时间
            await realtime_service.mark_published(event)
            return True


realtime_worker = RealtimeWorker()

if __name__ == '__main__':
    run_async(realtime_worker.start())
