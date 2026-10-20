from typing import Any

from fastapi import APIRouter,status

from atguigu.app.dependencies import ChatServiceDep, UserDep
from atguigu.app.schemas import ChatMessageRequest

router = APIRouter(prefix="/api/v1", tags=["聊天路由、发送聊天消息、历史对话加载"])


@router.post("/chat/messages",status_code=status.HTTP_204_NO_CONTENT)
async def process_chat_message_endpoint(
        payload: ChatMessageRequest,
        service: ChatServiceDep,
        user_info: UserDep
):
    """
    职责：处理聊天消息路由请求
    1. 必须要有用户信息【身份：令牌】
    2. 角色（权限）"user" or  "admin" or "staff"
    :return:
    """
    await service.process_chat_message(payload, user_info.user_id)


@router.get("/chat/history")
async def get_chat_history(
        service: ChatServiceDep,
        user_info: UserDep) -> dict[str, Any]:
    """
    职责：获取用户的历史对话
    :return:
    """

    chat_history = await service.get_chat_history(user_info.user_id)

    return chat_history
