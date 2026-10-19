from datetime import UTC, datetime
from uuid import uuid4


def get_utcnow() -> datetime:
    return datetime.now(UTC)


def get_uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
