"""
从Redis的通道中获取对应的事件数据 然后通过ws发送给客户端[前端]
"""
import asyncio
import logging
from typing import Any

from atguigu.app.services.auth import decode_token
from atguigu.infrastructure.redis import redis_client

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
from fastapi import APIRouter, WebSocket, status

router = APIRouter()

@router.websocket("/api/v1/realtime")
async def realtime_endpoint(websocket: WebSocket):
    """
    接口调用时机：用户端以及客服端页面一加载就会被调用到

    1. 获取当前是哪个端，然后确定用户的角色，最后根据用户的角色，订阅对应的通道
    2. 接收该通道的数据，然后调用websocket的发送事件数据的方法即可

    :param websocket:
    :return:
    """
    # 1. 建立好ws长连接
    await websocket.accept()  # 将http连接升级为ws连接，并且告诉客户端该长连接建立好

    # 2. 获取用户【普通用户 or 客服用户】的令牌
    try:
        auth_info: dict[str, Any] = await websocket.receive_json()
        current_user_token = auth_info['token']
    except Exception as exc:
        logger.error(f"获取用户身份信息失败:{str(exc)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="未获取到用户的身份信息")
        return

    # 3. 获取用户信息
    current_user = decode_token(current_user_token)

    # 4. 根据用户的角色选择通道
    target = current_user.user_id if current_user.role == "user" else "staff"

    # 3.用redis的pub/sub完成订阅
    async  with redis_client.pubsub() as pubsub:
        # a) 订阅路由后的通道
        pubsub.subscribe(target)

        # b) 推送订阅通道成功的事件
        await websocket.send_json({"event_type": "connected"})

        # c) 获取订阅通道的数据   # CancelError
        async def forward_event():
            async for item in pubsub.listen():
                if item['type'] == "message":
                    event_data = item['data']
                    await websocket.send_text(event_data)  # 将通道的数据用ws发送给客户端

        # d) 服务端不断的监听客户端是否关闭了连接  # WebsocketDisconnected Error
        async def disconnected():
            while True:
                await websocket.receive_text()

        # e) 定义异步后台任务列表，并且将两个协程任务对象交给事件循环线程（底层是一个线程 通过while True 不停地执行协程任务）
        tasks = [
            asyncio.create_task(forward_event()),
            asyncio.create_task(disconnected())
        ]
        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)  # 并发执行两个协程任务 并且等这两个任务都执行完，才不会阻塞

        for task in pending:
            task.cancel()  # 只是发送取消任务的信号而已，并没有真正让协程任务取消不执行

        # f) 等待取消任务一定被取消掉，并且某一个协程任务出现了异常，直接吃掉，不会raise到外部
        await asyncio.gather(*tasks, return_exceptions=True)
