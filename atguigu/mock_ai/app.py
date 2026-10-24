import asyncio
from typing import Any

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Mock AI Service (v2.0)")


@app.post("/internal/v1/agent/runs")
async def start_run(request: dict[str, Any]) -> dict[str, Any]:
    """根据测试关键词模拟 AI 的扁平响应结果。"""
    await asyncio.sleep(0.1)

    text = str(request["messages"][-1]["content"].get("text", ""))

    if "我要转人工" in text:
        return {
            "reply_type": "REQUEST_HANDOFF",
            "text": "已收到您的请求，正在为您安排人工客服，请稍候。",
            "handoff_summary": "用户主动申请人工服务，请客服查看历史会话并接入处理。",
        }

    return {
        "reply_type": "ANSWER",
        "text": f"模拟 AI 回复：'您好，请问有什么可以帮助您？",
    }


if __name__ == "__main__":
    uvicorn.run("atguigu.mock_ai.app:app", host="0.0.0.0", port=8002)
