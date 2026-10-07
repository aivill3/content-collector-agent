from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List
from app.domain.content import Article


class PageType(str, Enum):
    """페이지 유형 구분을 위한 Enum"""
    ARTICLE = "article"      # 단일 본문 페이지
    BOARD = "board"          # 게시판 목록 페이지
    UNKNOWN = "unknown"      # 판별 불가


class FetchTier(str, Enum):
    """수집에 사용된 3단계 Fallback 엔진 Enum"""
    HTTPX = "httpx"          # 1단계: 정적 HTML
    PLAYWRIGHT = "playwright"# 2단계: JS 렌더링
    CRAWL4AI = "crawl4ai"    # 3단계: 복잡 레이아웃
    FAILED = "failed"        # 수집 실패


@dataclass
class ScrapeResult:
    """단일 URL 수집 결과 도메인 객체"""
    target_url: str
    page_type: PageType
    tier_used: FetchTier
    articles: List[Article] = field(default_factory=list)
    error_message: Optional[str] = None