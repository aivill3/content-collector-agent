"""
URL 기반 스마트 수집 패키지 (url_collector)
- 3단계 Fallback (httpx -> Playwright -> Crawl4AI)
- 게시판 / 단일 글 자동 감지
- 본문 추출 및 정제
"""

from app.url_collector.service import UrlCollectorService

__all__ = ["UrlCollectorService"]