"""DB 테이블 (SQLModel). 스키마를 바꾸면 alembic 마이그레이션을 함께 만든다.

    alembic revision --autogenerate -m "설명"   → alembic/versions/ 확인·수정 후
    alembic upgrade head

워크스페이스(테넌트) 중심 구조
----------------------------
- 워크스페이스에 속하는 테이블은 모두 workspace_id 를 직접 가진다 (WorkspaceScoped).
  상위 테이블을 조인해야 워크스페이스를 알 수 있는 구조를 만들지 않는다 —
  조회 때 필터 하나로 격리가 끝나고, 빠뜨렸는지 검사하기도 쉽다.
- 조회·수정은 repositories/ 의 함수로만 한다 (scope.py 가 workspace_id 필터를 강제한다).

이 모델은 domain.Article 도, API 스키마도 아니다. 수집 결과는 repositories/contents.py 가
Article → Content 로 옮겨 담는다.

규칙: 시각은 UTCDateTime(UTC aware), 선택지는 str_enum(문자열 컬럼), JSON 은 sa.JSON.
PostgreSQL 전용 타입(JSONB, ARRAY, 네이티브 ENUM)은 쓰지 않는다.
"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.types import UTCDateTime, str_enum, utcnow
from app.domain.enums import (
    CollectionPath,
    JobStatus,
    JobTrigger,
    KeywordOrigin,
    ScheduleType,
    SourceType,
    WorkspaceType,
)

# 제약 이름을 고정한다. SQLite 에서 alembic batch 모드로 제약을 지우려면 이름이 있어야 한다.
SQLModel.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _created_at() -> datetime:
    return Field(default_factory=utcnow, sa_type=UTCDateTime, nullable=False)


def _time(**kw) -> datetime | None:
    return Field(default=None, sa_type=UTCDateTime, **kw)


class Workspace(SQLModel, table=True):
    """테넌트. 개인 유저는 1인 워크스페이스, 회사 유저는 회사 워크스페이스에 속한다."""
    __tablename__ = "workspaces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    type: WorkspaceType = Field(sa_type=str_enum(WorkspaceType))
    plan: str = Field(default="free", max_length=20)
    created_at: datetime = _created_at()


class WorkspaceScoped(SQLModel):
    """워크스페이스에 속하는 테이블의 공통 컬럼. repositories/scope.py 가 이 클래스만 받는다."""
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", ondelete="RESTRICT", index=True)


class Source(WorkspaceScoped, table=True):
    """수집 설정의 단위. 유형별 설정은 config(JSON) — schemas/source_config.py 로 검증한 값만 넣는다."""
    __tablename__ = "sources"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    type: SourceType = Field(sa_type=str_enum(SourceType))
    is_active: bool = True

    # ── 일정 (계산·실행은 스케줄러 단계) ──
    schedule_type: ScheduleType = Field(default=ScheduleType.MANUAL, sa_type=str_enum(ScheduleType))
    schedule_time: str | None = Field(default=None, max_length=5)   # "HH:MM", DISPLAY_TZ 기준 (timeutil.schedule_at)
    cron_expr: str | None = Field(default=None, max_length=100)     # 있으면 schedule_type 보다 우선
    next_run_at: datetime | None = _time(index=True)

    # ── 최근 실행 ──
    last_collected_at: datetime | None = _time()
    last_status: JobStatus | None = Field(default=None, sa_type=str_enum(JobStatus))
    # 수집한 글 중 가장 늦은 발행 시각 (CollectResult.latest_published).
    # 다음 실행의 since 로 넘긴다. 요청을 줄이는 값이 아니라, 수집이 조회 기간보다 오래
    # 멈췄을 때 그 공백까지 창을 넓히는 값이다 (processors/date_filter.filter_recent).
    last_published_at: datetime | None = _time()

    # ── 정제 기준 ──
    min_body_length: int
    allow_non_korean: bool = False

    config: dict = Field(default_factory=dict, sa_type=sa.JSON)
    created_at: datetime = _created_at()
    updated_at: datetime = _created_at()


class SourceKeyword(WorkspaceScoped, table=True):
    """뉴스 키워드 소스의 검색어. 저장 전 공백을 정리한다 (repositories/sources.normalize_keyword)."""
    __tablename__ = "source_keywords"
    __table_args__ = (sa.UniqueConstraint("source_id", "keyword", name="uq_source_keywords_source_id_keyword"),)

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="sources.id", ondelete="CASCADE", index=True)
    keyword: str = Field(max_length=100)
    origin: KeywordOrigin = Field(default=KeywordOrigin.MANUAL, sa_type=str_enum(KeywordOrigin))
    created_at: datetime = _created_at()


class CollectionJob(WorkspaceScoped, table=True):
    """수집 1회 기록."""
    __tablename__ = "collection_jobs"

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="sources.id", ondelete="RESTRICT", index=True)
    trigger: JobTrigger = Field(sa_type=str_enum(JobTrigger))
    status: JobStatus = Field(default=JobStatus.QUEUED, sa_type=str_enum(JobStatus))
    queued_at: datetime = _created_at()
    started_at: datetime | None = _time()
    finished_at: datetime | None = _time()
    duration_sec: float | None = None
    collected_count: int = 0                     # 이번 실행에서 새로 저장한 콘텐츠 수
    # CollectResult.stats 그대로 (키는 한국어, 유형마다 다르다)
    stage_counts: dict = Field(default_factory=dict, sa_type=sa.JSON)
    error_message: str | None = Field(default=None, sa_type=sa.Text)


class JobApiResponse(WorkspaceScoped, table=True):
    """외부 API 원본 응답. 검색 결과는 시점마다 달라 나중에 재현할 수 없으므로 남긴다.

    보존 기간 미정 — created_at 기준으로 일괄 삭제할 수 있게 인덱스를 둔다.
    """
    __tablename__ = "job_api_responses"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="collection_jobs.id", ondelete="CASCADE", index=True)
    keyword: str = Field(max_length=100)
    response: list = Field(default_factory=list, sa_type=sa.JSON)   # 네이버 items 원본
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime, nullable=False, index=True)


class Content(WorkspaceScoped, table=True):
    """수집된 콘텐츠. 시스템만 만든다 (유저 수정 없음).

    같은 워크스페이스에서는 url_hash 로 한 번만 저장한다. 다른 워크스페이스는 따로 저장한다.
    원본 HTML 은 저장하지 않는다.
    """
    __tablename__ = "contents"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", "url_hash", name="uq_contents_workspace_id_url_hash"),
        sa.Index("ix_contents_workspace_id_collected_at", "workspace_id", "collected_at"),
        sa.Index("ix_contents_workspace_id_published_at", "workspace_id", "published_at"),
        sa.Index("ix_contents_workspace_id_source_id", "workspace_id", "source_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="sources.id", ondelete="RESTRICT")
    first_job_id: int = Field(foreign_key="collection_jobs.id", ondelete="RESTRICT")
    collection_path: CollectionPath = Field(sa_type=str_enum(CollectionPath))

    url: str = Field(sa_type=sa.Text)
    normalized_url: str = Field(sa_type=sa.Text)       # processors/deduplication.canonical_url
    url_hash: str = Field(max_length=64)               # normalized_url 의 sha256 (hex)

    title: str = Field(default="", sa_type=sa.Text)
    publisher: str = Field(default="", max_length=200)  # 언론사·사이트명 (Article.press)
    published_at: datetime | None = _time()             # 모르면 NULL
    summary: str = Field(default="", sa_type=sa.Text)
    board_url: str = Field(default="", sa_type=sa.Text)

    raw_body: str = Field(default="", sa_type=sa.Text)       # Article.body (정제 전)
    cleaned_body: str = Field(default="", sa_type=sa.Text)   # Article.body_clean
    body_length: int = 0                                      # len(cleaned_body)
    collected_at: datetime = _created_at()


class ContentKeywordHit(WorkspaceScoped, table=True):
    """어떤 키워드로 몇 위에서 찾았는지. 키워드마다 처음 찾은 기록만 남는다."""
    __tablename__ = "content_keyword_hits"
    __table_args__ = (sa.UniqueConstraint("content_id", "keyword", name="uq_content_keyword_hits_content_id_keyword"),)

    id: int | None = Field(default=None, primary_key=True)
    content_id: int = Field(foreign_key="contents.id", ondelete="CASCADE", index=True)
    # 키워드를 소스에서 빼도 기록은 남긴다 (keyword 문자열로 보존)
    source_keyword_id: int | None = Field(default=None, foreign_key="source_keywords.id", ondelete="SET NULL")
    keyword: str = Field(max_length=100)
    rank: int                                    # 검색 결과 순위 (1부터)
    job_id: int = Field(foreign_key="collection_jobs.id", ondelete="RESTRICT", index=True)
    found_at: datetime = _created_at()
