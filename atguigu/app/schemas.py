from typing import Literal, Any

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message_id: str
    type: Literal["text", "object"]
    content: dict[str, Any]


class CurrentUser(BaseModel):
    user_id: str
    role: Literal["user", "staff", "admin"] = "user"


class ReplyRequest(BaseModel):
    text: str
