import asyncio
import redis.asyncio as redis

CHANNEL = "test_channel"


async def subscriber():
    """订阅者：负责接收消息"""
    r = redis.Redis(host="192.168.200.199", port=6379, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL)
    print(f"【订阅者】已成功订阅频道: {CHANNEL}")

    async for message in pubsub.listen():
        # print(message)
        if message["type"] == "message":
            data = message["data"]
            print(f"【订阅者】收到消息: {data}")
            if data == "QUIT":
                break

    await pubsub.aclose()
    await r.aclose()


async def publisher():
    """发布者：负责发送消息"""
    r = redis.Redis(host="192.168.200.199", port=6379, decode_responses=True)
    await asyncio.sleep(1)  # 等待订阅者就绪

    for i in range(1, 4):
        msg = f"Hello Redis {i}"
        print(f"【发布者】发送: {msg}")
        await r.publish(CHANNEL, msg)
        await asyncio.sleep(1)

    # 发送退出指令
    await r.publish(CHANNEL, "QUIT")
    await r.aclose()


async def main():
    # 同时并发运行订阅者和发布者
    await asyncio.gather(subscriber(), publisher())


if __name__ == "__main__":
    asyncio.run(main())
