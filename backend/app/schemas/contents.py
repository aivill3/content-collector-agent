"""콘텐츠 조회 API 의 요청·응답. 시각은 DISPLAY_TZ ISO 8601 (DisplayDateTime).

목록 항목에는 본문을 넣지 않는다 (한 페이지가 수 MB 가 될 수 있다). 본문은 상세에서만.
"""
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.db.models import Content, ContentKeywordHit
from app.domain.enums import CollectionPath
from app.repositories.contents import excerpt_of
from app.schemas.base import CamelModel, DisplayDateTime

MAX_PAGE_SIZE = 100

DateField = Literal["collected_at", "published_at"]


class ContentListParams(CamelModel):
    """GET /api/contents 쿼리. 이름은 camelCase (sourceId, collectionPath, dateField ...)."""
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=MAX_PAGE_SIZE)
    source_id: int | None = None
    collection_path: CollectionPath | None = None
    # 기간 — DISPLAY_TZ 날짜, 양끝 포함. 한쪽만 줘도 된다
    from_: date | None = Field(None, alias="from")
    to: date | None = None
    # 오늘을 포함한 최근 N일 (timeutil.recent_days). from·to 와 함께 쓰지 않는다
    days: int | None = Field(None, ge=1)
    date_field: DateField = "collected_at"
    q: str = Field("", max_length=100)      # 제목 검색
    sort: DateField = "collected_at"
    order: Literal["desc", "asc"] = "desc"

    @model_validator(mode="after")
    def _range(self):
        if self.from_ and self.to and self.to < self.from_:
            raise ValueError("기간의 끝(to)이 시작(from)보다 앞섭니다")
        if self.days and (self.from_ or self.to):
            raise ValueError("days 는 from·to 와 함께 쓸 수 없습니다")
        return self


class ContentListItem(CamelModel):
    id: int
    title: str
    url: str
    publisher: str
    summary: str                     # 검색 API 설명 등 (게시판·URL 은 빈 값이 많다)
    excerpt: str                     # 정제 본문 앞부분 (repositories.contents.EXCERPT_LEN 자) — 목록의 요약 줄
    collection_path: CollectionPath
    source_id: int
    source_name: str
    published_at: DisplayDateTime | None
    collected_at: DisplayDateTime
    keywords: list[str]              # 이 콘텐츠를 찾은 키워드 (찾은 순서)
    body_length: int

    @classmethod
    def of(cls, c: Content, *, source_name: str, keywords: list[str], excerpt: str) -> "ContentListItem":
        return cls(
            id=c.id, title=c.title, url=c.url, publisher=c.publisher, summary=c.summary, excerpt=excerpt,
            collection_path=c.collection_path,
            source_id=c.source_id, source_name=source_name, published_at=c.published_at,
            collected_at=c.collected_at, keywords=keywords, body_length=c.body_length,
        )


class ContentListResult(CamelModel):
    items: list[ContentListItem]
    total: int
    page: int
    size: int
    page_count: int


class ContentHit(CamelModel):
    keyword: str
    rank: int
    job_id: int
    found_at: DisplayDateTime

    @classmethod
    def of(cls, h: ContentKeywordHit) -> "ContentHit":
        return cls(keyword=h.keyword, rank=h.rank, job_id=h.job_id, found_at=h.found_at)


class ContentDetail(ContentListItem):
    board_url: str
    first_job_id: int
    cleaned_body: str
    raw_body: str
    hits: list[ContentHit]

    @classmethod
    def of_detail(cls, c: Content, *, source_name: str, hits: list[ContentKeywordHit]) -> "ContentDetail":
        item = ContentListItem.of(c, source_name=source_name, keywords=[h.keyword for h in hits],
                                  excerpt=excerpt_of(c.cleaned_body))
        return cls(
            **item.model_dump(), board_url=c.board_url, first_job_id=c.first_job_id,
            cleaned_body=c.cleaned_body, raw_body=c.raw_body, hits=[ContentHit.of(h) for h in hits],
        )
