"""

统一定义服务层的组件
ChatService组件
"""
from typing import Annotated

from fastapi import Depends, Header

from atguigu.app.schemas import CurrentUser
from atguigu.app.services.auth import require_authorized_user
from atguigu.app.services.chat import ChatService


def get_chat_service():
    return ChatService()


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


def require_user_role(authorization: Annotated[str | None, Header()] = None) -> CurrentUser:
    return require_authorized_user(authorization, "user")


UserDep = Annotated[CurrentUser, Depends(require_user_role)]
