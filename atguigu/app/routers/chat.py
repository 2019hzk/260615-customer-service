from typing import Any

from fastapi import APIRouter

from atguigu.app.dependencies import ChatServiceDep, UserDep
from atguigu.app.schemas import ChatMessageRequest

router = APIRouter(prefix="/api/v1", tags=["聊天路由、发送聊天消息、历史对话加载"])


@router.post("/chat/messages")
async def process_chat_message_endpoint(
        payload: ChatMessageRequest,
        service: ChatServiceDep,
        user_info: UserDep
) -> dict[str, Any]:
    """
    职责：处理聊天消息路由请求
    1. 必须要有用户信息【身份：令牌】
    2. 角色（权限）"user" or  "admin" or "staff"
    :return:
    """

    conversation_info = await service.process_chat_message(payload, user_info.user_id)
    return conversation_info
