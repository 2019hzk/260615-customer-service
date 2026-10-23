"""

AI Worker:负责领取轮次，调用AI Service，检查AI Service的结果，清算（修改轮次的状态以及保存相应的回复）

"""
import httpx
import logging
import asyncio
from typing import Any

from atguigu.app.schemas import CurrentUser
from atguigu.app.services.auth import encode_token
from atguigu.app.services.chat import ChatService
from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings
from atguigu.infrastructure.db import async_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIWorker:

    def __init__(self):
        self._settings = get_settings()
        self._session_factory = async_session_factory

    async def start(self):
        """
        启动消费者 负责一直 领取轮次，调用AI Service 清算
        :return:
        """
        logger.info("AI Worker 已经启动")
        while True:
            claimed_turn = await self._process_next_turn()
            if claimed_turn is False:
                await asyncio.sleep(self._settings.ai_worker_poll_interval_ms / 1000)

    async def _process_next_turn(self) -> bool:
        """
        职责：负责领取轮次、调用AI Service   清算Turn
        :return:
        """
        async  with  self._session_factory() as session:
            # 1. 实例化chat_service对象
            chat_service = ChatService(session)

            # 2. 领取turn
            claimed = await chat_service.claim_turn()
            if claimed is None:
                return False

            claimed_turn, payload, user_id = claimed

            # 3. 调用AI Service
            run_result, error = await self._call_ai_service(payload, user_id)

            # 4. 清算Turn(修改Turn的状态、保存普通AI回复 以及转人工请求的回复)
            await chat_service.finish_turn(claimed_turn, run_result, error)

            return True

    async def _call_ai_service(self,
                               payload: dict[str, Any],
                               user_id: str) -> tuple[dict[str, Any] | None, Exception | None]:
        """
        职责：调用AI Service以及获取AI Service结果
        返回值： 正常：AI  Service返回结果，Exception=None
        返回值： 异常：AI  Service返回None，Exception=失败原因
        :param payload:
        :param user_id:
        :return:
        """

        # 1. 构建请求头
        # a) 用户身份信息
        user_token = encode_token(CurrentUser(user_id=user_id))
        # b) 服务调用信任信息
        internal_service_token = self._settings.internal_service_token
        headers = {
            "Authorization": f"Bearer {user_token}",
            "X-Internal-Service-Token": internal_service_token
        }

        # 2. 发送请求
        # b) 构建超时
        timeout = httpx.Timeout(self._settings.ai_timeout_seconds, connect=5)

        # c) 发送请求
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                response = await client.post(
                    f"{self._settings.ai_service_url}/internal/v1/agent/runs",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                # 3. 获取响应结果
                return response.json(), None
        except Exception as exc:
            logger.exception("会话 %s 调用 AI Service 失败: %s", payload["conversation_id"], exc)
            return None, exc


ai_woker = AIWorker()

if __name__ == '__main__':
    run_async(ai_woker.start())
