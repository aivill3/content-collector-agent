import asyncio
import logging
from typing import List, Union, Optional

from app.core.timeutil import to_display_iso
from app.domain.content import Article
from app.domain.url_collector import PageType, FetchTier, ScrapeResult
from app.processors.date_filter import parse_dt
from app.url_collector.fetcher import HtmlFetcher
from app.url_collector.parser import SmartUrlParser

logger = logging.getLogger(__name__)


class UrlCollectorService:
    """URL 전용 단일/게시판 수집 메인 서비스 레이어"""

    def __init__(self, timeout: float = 15.0):
        self.fetcher = HtmlFetcher(timeout=timeout)
        self.parser = SmartUrlParser()

    async def collect_with_details(self, target: Union[str, List[str]], max_items_per_board: int = 10) -> List[ScrapeResult]:
        """
        URL별 수집 결과 상세 정보(ScrapeResult) 객체 리스트를 반환합니다.
        """
        urls = [target] if isinstance(target, str) else target
        results: List[ScrapeResult] = []

        for url in urls:
            logger.info(f"[UrlCollector] 수집 시작: {url}")
            html, engine_used = await self.fetcher.fetch(url)

            if engine_used == FetchTier.FAILED or not html:
                logger.error(f"[UrlCollector] HTML 수집 실패: {url}")
                results.append(ScrapeResult(
                    target_url=url,
                    page_type=PageType.UNKNOWN,
                    tier_used=FetchTier.FAILED,
                    articles=[],
                    error_message="All 3 fetch tiers failed"
                ))
                continue

            # 페이지 타입 감지
            page_type = self.parser.detect_page_type(html, url)

            if page_type == PageType.BOARD:
                logger.info(f"[UrlCollector] 게시판 목록 페이지 감지 -> 하위 링크 수집 진행: {url}")
                sub_links = self.parser.extract_sub_links(html, base_url=url, limit=max_items_per_board)
                logger.info(f"[UrlCollector] 하위 글 {len(sub_links)}개 발견")

                tasks = [self._collect_single_article(sub_url, board_url=url) for sub_url in sub_links]
                sub_articles = [res for res in await asyncio.gather(*tasks) if res]

                results.append(ScrapeResult(
                    target_url=url,
                    page_type=PageType.BOARD,
                    tier_used=engine_used,
                    articles=sub_articles
                ))
            else:
                logger.info(f"[UrlCollector] 단일 글 페이지 감지: {url}")
                parsed_data = self.parser.parse_article_content(html, url)
                article = self._build_article_object(parsed_data, board_url="")

                results.append(ScrapeResult(
                    target_url=url,
                    page_type=PageType.ARTICLE,
                    tier_used=engine_used,
                    articles=[article]
                ))

        return results

    async def collect(self, target: Union[str, List[str]], max_items_per_board: int = 10) -> List[Article]:
        """
        기존 파이프라인 호환성을 위해 Article 객체 리스트만 반환합니다.
        """
        detailed_results = await self.collect_with_details(target, max_items_per_board)
        articles: List[Article] = []
        for res in detailed_results:
            articles.extend(res.articles)
        return articles

    async def _collect_single_article(self, url: str, board_url: str = "") -> Optional[Article]:
        """글 1건 수집 및 파싱. 게시판 하위 글이면 board_url 에 목록 주소를 넘긴다."""
        html, engine_used = await self.fetcher.fetch(url)
        if engine_used == FetchTier.FAILED or not html:
            return None
        parsed_data = self.parser.parse_article_content(html, url)
        return self._build_article_object(parsed_data, board_url=board_url)

    @staticmethod
    def _to_display_published(value: Optional[str]) -> str:
        """발행일 문자열 → DISPLAY_TZ(KST) ISO 8601. 시간대 표기가 없으면 KST 로 읽고, 못 읽으면 빈 값."""
        dt = parse_dt(value or "")
        return (to_display_iso(dt) or "") if dt else ""

    def _build_article_object(self, data: dict, board_url: str = "") -> Article:
        """파싱 결과를 기존 content.py의 Article dataclass 규격에 맞게 변환"""
        return Article(
            url=data.get("url", ""),
            title=data.get("title", ""),
            body=data.get("body", ""),
            body_clean=data.get("body_clean", ""),
            published=self._to_display_published(data.get("published_at")),
            board_url=board_url,
            source="website"
        )