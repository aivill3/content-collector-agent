"""SQLite·PostgreSQL 에서 똑같이 동작하는 컬럼 타입."""
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy.types import TypeDecorator

from app.core.timeutil import utcnow  # noqa: F401  (models·repositories 가 여기서 가져간다)


class UTCDateTime(TypeDecorator):
    """timezone-aware UTC 로 저장하고 읽는다.

    SQLite 는 시간대를 저장하지 않아 읽으면 naive datetime 이 된다. 쓸 때 UTC 로 바꿔
    시간대를 떼고, 읽을 때 UTC 를 다시 붙인다. PostgreSQL(timestamptz)도 같은 값이 된다.
    naive datetime 은 받지 않는다 — 어느 시간대 시각인지 알 수 없기 때문이다.
    표시 시간대(DISPLAY_TZ) 변환은 app/core/timeutil.py 가 한다.
    """
    impl = sa.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("시간대가 없는 datetime 은 저장하지 않습니다 (UTC 로 넘길 것)")
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def str_enum(enum_cls: type[Enum], length: int = 20) -> sa.Enum:
    """Python Enum ↔ 문자열 컬럼. DB 네이티브 ENUM·CHECK 제약을 만들지 않는다."""
    return sa.Enum(
        enum_cls,
        native_enum=False,
        create_constraint=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
    )
