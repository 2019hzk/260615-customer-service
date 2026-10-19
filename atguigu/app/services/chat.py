from typing import Any

from atguigu.app.schemas import ChatMessageRequest


class ChatService:

    async def process_chat_message(self, payload: ChatMessageRequest, user_id: str) -> dict[str, Any]:

        return {"conversation_id": "con_1112222", "mode": "AI"}
