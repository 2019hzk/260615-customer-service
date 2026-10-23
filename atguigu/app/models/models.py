from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from atguigu.common.utils import get_uid, get_utcnow
from atguigu.app.models.enums import ConversationMode, TurnStatus, HandoffStatus


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index(
            "uq_open_conversation_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("mode IN ('AI', 'QUEUED', 'HUMAN')"),  # 同一个用户会话模式是有效的只能有一个 但是有效的某一个可以和关闭的会话模式共存
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("conv"))
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    mode: Mapped[str] = mapped_column(String(20), default=ConversationMode.AI, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow, onupdate=get_utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(80), unique=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        Index("uq_collecting_turn_per_conversation", "conversation_id", unique=True,
              postgresql_where=text("status = 'COLLECTING'")),

        Index("uq_executing_turn_per_conversation", "conversation_id", unique=True,
              postgresql_where=text("status = 'RUNNING'"))
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("turn"))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default=TurnStatus.COLLECTING, index=True)
    snapshot_message_id: Mapped[int | None] = mapped_column(Integer)
    collect_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)


class RealtimeEvent(Base):
    """等待实时推送 Worker 发布的实时消息事件。为了持久化"""

    __tablename__ = "realtime_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    target: Mapped[str] = mapped_column(String(80), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class Handoff(Base):
    """记录一次人工客服工单及其处理状态。"""

    __tablename__ = "handoffs"
    __table_args__ = (
        Index("uq_open_handoff_per_conversation", "conversation_id", unique=True,
              postgresql_where=text("status IN ('WAITING', 'ACTIVE')")),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("handoff"))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=HandoffStatus.WAITING, index=True)
    staff_id: Mapped[str | None] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)
