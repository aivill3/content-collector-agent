import asyncio
import logging
from typing import Tuple, Optional
import httpx

from app.core.config import MAX_CONCURRENT_SCRAPES
from app.domain.url_collector import FetchTier

logger = logging.getLogger(__name__)

# 동시 실행 브라우저/수집 세마포어
_scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


class HtmlFetcher:
    """3단계 Fallback HTML 수집 엔진"""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch(self, url: str) -> Tuple[str, FetchTier]:
        """
        URL에서 HTML 원본을 3단계 Fallback으로 수집합니다.
        Returns:
            (html_content, FetchTier)
        """
        async with _scrape_semaphore:
            # 1단계: httpx
            html, err = await self._fetch_httpx(url)
            if html and len(html.strip()) > 500:
                logger.info(f"[Fetcher Tier 1: httpx] 성공 - {url}")
                return html, FetchTier.HTTPX

            logger.warning(f"[Fetcher Tier 1: httpx] 실패/불충분({err}) -> Tier 2 시도: {url}")

            # 2단계: Playwright
            html, err = await self._fetch_playwright(url)
            if html and len(html.strip()) > 500:
                logger.info(f"[Fetcher Tier 2: Playwright] 성공 - {url}")
                return html, FetchTier.PLAYWRIGHT

            logger.warning(f"[Fetcher Tier 2: Playwright] 실패({err}) -> Tier 3 시도: {url}")

            # 3단계: Crawl4AI
            html, err = await self._fetch_crawl4ai(url)
            if html and len(html.strip()) > 200:
                logger.info(f"[Fetcher Tier 3: Crawl4AI] 성공 - {url}")
                return html, FetchTier.CRAWL4AI

            logger.error(f"[Fetcher] 모든 3단계 수집 실패: {url}")
            return "", FetchTier.FAILED

    async def _fetch_httpx(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                follow_redirects=True,
                timeout=self.timeout,
                verify=False
            ) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.text, None
                return None, f"HTTP {res.status_code}"
        except Exception as e:
            return None, str(e)

    async def _fetch_playwright(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=DEFAULT_HEADERS["User-Agent"])
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=int(self.timeout * 1000))
                await asyncio.sleep(1.0)
                content = await page.content()
                await browser.close()
                return content, None
        except Exception as e:
            return None, str(e)

    async def _fetch_crawl4ai(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            from crawl4ai import AsyncWebCrawler
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                if result and result.html:
                    return result.html, None
                return None, "empty result"
        except Exception as e:
            return None, str(e)