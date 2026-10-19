import uvicorn

from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings


async def start_uvicorn():
    server = uvicorn.Server(
        config=uvicorn.Config(
            app="atguigu.app.app:app",
            host=get_settings().api_host,
            port=get_settings().api_port,
            loop="none"  # 保证一定使用外部自定义的事件循环
        )
    )

    await server.serve()


if __name__ == '__main__':
    # uvicorn.run("atguigu.app:app", host="", port=5000)  # 没有用到自己定义的事件循环
    run_async(start_uvicorn())
