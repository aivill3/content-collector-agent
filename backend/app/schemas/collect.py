"""수집 실행(지금 수집) API 의 요청·응답."""
from pydantic import Field

from app.schemas.base import CamelModel


class CollectRequest(CamelModel):
    source_ids: list[int] | None = Field(None, max_length=100)   # 없으면 사용 중인 소스 전부


class CollectResponse(CamelModel):
    job_ids: list[int]            # 새로 등록한 대기 작업
    queued: int
    skipped: int                  # 이미 대기·실행 중이라 건너뛴 소스 수
