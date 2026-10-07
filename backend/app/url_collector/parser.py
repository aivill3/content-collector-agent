from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import trafilatura

from app.domain.url_collector import PageType
from app.url_collector.cleaner import TextCleaner


class SmartUrlParser:
    """게시판/단일 글 자동 판별 및 본문 파싱 모듈"""

    BOARD_INDICATORS = ["board", "bbs", "list", "notice", "category", "index", "page"]

    @classmethod
    def detect_page_type(cls, html: str, url: str) -> PageType:
        """URL 키워드 및 DOM 내부 구조로 페이지 타입을 자동 판별합니다."""
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        query_lower = parsed.query.lower()

        # URL 경로 검사
        if any(ind in path_lower or ind in query_lower for ind in cls.BOARD_INDICATORS):
            return PageType.BOARD

        # DOM 내부 a 태그 집계 검사
        soup = BeautifulSoup(html, "html.parser")
        table_rows = soup.find_all("tr")
        list_items = soup.find_all(["li", "div"])

        valid_link_count = 0
        for parent in list_items + table_rows:
            a_tag = parent.find("a", href=True)
            if a_tag and len(a_tag.get_text(strip=True)) > 5:
                valid_link_count += 1
                if valid_link_count >= 5:
                    return PageType.BOARD

        return PageType.ARTICLE

    @classmethod
    def extract_sub_links(cls, html: str, base_url: str, limit: int = 10) -> List[str]:
        """게시판 목록 HTML에서 상세 글 링크를 추출합니다."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        seen = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            text = a_tag.get_text(strip=True)

            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue

            if len(text) < 4:
                continue

            full_url = urljoin(base_url, href)

            if full_url == base_url or full_url in seen:
                continue

            seen.add(full_url)
            links.append(full_url)

            if len(links) >= limit:
                break

        return links

    @classmethod
    def parse_article_content(cls, html: str, url: str) -> Dict[str, Any]:
        """단일 페이지 HTML에서 제목, 본문, 정제 본문, 날짜를 추출합니다."""
        extracted = trafilatura.extract(
            html,
            url=url,
            include_links=False,
            include_images=False,
            output_format="python"
        )

        title = ""
        body_raw = ""
        published_at = None

        if extracted and isinstance(extracted, dict):
            title = extracted.get("title", "")
            body_raw = extracted.get("text", "")
            published_at = extracted.get("date", None)

        soup = BeautifulSoup(html, "html.parser")
        if not title and soup.title:
            title = soup.title.get_text(strip=True)

        if not body_raw:
            article_body = (
                soup.find("article") or
                soup.find("div", id=lambda x: x and ("content" in x or "body" in x or "article" in x)) or
                soup.find("main")
            )
            body_raw = article_body.get_text(separator="\n") if article_body else soup.get_text(separator="\n")

        body_clean = TextCleaner.clean_html_to_text(body_raw)

        return {
            "url": url,
            "title": title or "제목 없음",
            "body": body_raw,
            "body_clean": body_clean,
            "published_at": published_at,
        }