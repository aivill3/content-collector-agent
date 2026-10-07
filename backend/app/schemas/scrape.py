from pydantic import BaseModel, Field
from typing import List, Optional
from app.domain.url_collector import PageType, FetchTier


class ScrapeRequest(BaseModel):
    """URL 수집 요청 DTO"""
    urls: List[str] = Field(
        ...,
        min_length=1,
        description="수집 대상 URL 목록",
    )
    max_items_per_board: int = Field(
        default=10,
        ge=1,
        le=50,
        description="게시판 목록 감지 시 수집할 최대 하위 글 개수"
    )


class ArticleResponse(BaseModel):
    """단일 수집 문서 응답 DTO"""
    url: str
    title: str
    body: str
    body_clean: str
    published: Optional[str] = None
    board_url: Optional[str] = None


class ScrapeResultResponse(BaseModel):
    """URL별 상세 수집 결과 응답 DTO"""
    target_url: str
    page_type: PageType
    tier_used: FetchTier
    articles: List[ArticleResponse]
    error_message: Optional[str] = None


class ScrapeResponse(BaseModel):
    """전체 수집 작업 결과 응답 DTO"""
    total_requested: int
    total_articles: int
    results: List[ScrapeResultResponse]