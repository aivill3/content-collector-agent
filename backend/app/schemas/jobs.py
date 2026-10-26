"""수집 작업 API 의 요청·응답. 시각은 DISPLAY_TZ ISO 8601 (DisplayDateTime).

stage_counts 는 CollectResult.stats 그대로다 — 키는 한국어이고 소스 유형마다 다르다
(뉴스: 검색·중복 제거 후·기간 필터 후·신규·본문 확보·정제 통과 / 게시판: 목록… / URL: 입력…).
화면의 단계 이름으로 옮기는 일은 프론트(lib/api.ts)가 한다.
"""
from pydantic import Field

from app.db.models import CollectionJob, Source
from app.domain.enums import JobStatus, JobTrigger, SourceType
from app.schemas.base import CamelModel, DisplayDateTime

MAX_JOB_LIMIT = 500


class JobListParams(CamelModel):
    """GET /api/jobs 쿼리. 이름은 camelCase (sourceId ...)."""
    source_id: int | None = None
    status: JobStatus | None = None
    days: int | None = Field(None, ge=1)    # 오늘을 포함한 최근 N일 (등록 시각 queued_at, DISPLAY_TZ 날짜)
    limit: int = Field(100, ge=1, le=MAX_JOB_LIMIT)


class JobListItem(CamelModel):
    id: int
    source_id: int
    source_name: str
    source_type: SourceType | None   # 소스를 찾지 못하면 null
    trigger: JobTrigger
    status: JobStatus
    queued_at: DisplayDateTime
    started_at: DisplayDateTime | None
    finished_at: DisplayDateTime | None
    duration_sec: float | None
    collected_count: int             # 새로 저장한 콘텐츠 수
    stage_counts: dict[str, int]
    error_message: str | None

    @classmethod
    def of(cls, j: CollectionJob, source: Source | None) -> "JobListItem":
        return cls(
            id=j.id, source_id=j.source_id,
            source_name=source.name if source else "", source_type=source.type if source else None,
            trigger=j.trigger, status=j.status, queued_at=j.queued_at, started_at=j.started_at,
            finished_at=j.finished_at, duration_sec=j.duration_sec, collected_count=j.collected_count,
            stage_counts=j.stage_counts or {}, error_message=j.error_message,
        )
