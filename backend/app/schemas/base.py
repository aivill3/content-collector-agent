"""API 스키마 공통 — JSON 필드는 camelCase, 파이썬 속성은 snake_case.

프론트엔드(frontend/lib/types.ts)가 camelCase 를 쓰므로 변환은 여기서 한 번만 한다.

시각은 DISPLAY_TZ 로 바꿔 오프셋이 붙은 ISO 8601 문자열로 내보낸다 (2026-09-30T14:20:00+09:00).
    DB 의 datetime(UTC)  → DisplayDateTime 필드
    수집기의 날짜 문자열 → display_iso() 로 변환해 str 필드
"""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

from app.core.timeutil import to_display_iso
from app.processors.date_filter import parse_dt


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# JSON 으로 내보낼 때만 문자열로 바꾼다 (파이썬 안에서는 datetime 그대로)
DisplayDateTime = Annotated[datetime, PlainSerializer(to_display_iso, return_type=str, when_used="json")]


def display_iso(value: str) -> str:
    """수집기가 채운 날짜 문자열(Article.published) → DISPLAY_TZ ISO 8601. 못 읽으면 빈 값."""
    dt = parse_dt(value)
    return to_display_iso(dt) if dt else ""
