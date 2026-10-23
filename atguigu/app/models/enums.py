from enum import StrEnum, Enum


class ConversationMode(StrEnum):
    """
    会话模式
    """
    AI = "AI"
    QUEUED = "QUEUED"
    HUMAN = "HUMAN"
    CLOSED = "CLOSED"


class MessageRole(StrEnum):
    """
    消息角色
    """

    USER = "USER"
    AI = "AI"
    HUMAN = "HUMAN"


class TurnStatus(StrEnum):
    """
    轮次状态
    """
    COLLECTING = "COLLECTING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class HandoffStatus(StrEnum):
    """
    工单状态描述
    """
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
