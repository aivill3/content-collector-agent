"""단일 URL 수집기 — 유저가 넣은 글 주소의 본문만 가져온다.

게시판(목록 → 여러 글)과 달리 '이 글 하나'가 대상이다. 목록 탐색은 없고,
제목·날짜는 본문 추출 때 페이지 메타데이터로 채워진다 (extractors/article.py).
원본 taekwonw-agent 의 source="manual" 에 해당한다.
"""
from app.collectors.base import Collector
from app.domain.content import Article
from app.processors.deduplication import canonical_url


class WebsiteCollector(Collector):
    source_type = "website"

    def __init__(self, urls: list[str]):
        self.urls = urls

    def collect(self) -> list[Article]:
        seen: set[str] = set()
        out: list[Article] = []
        for url in (u.strip() for u in self.urls):
            if not url or canonical_url(url) in seen:
                continue
            seen.add(canonical_url(url))
            out.append(Article(url=url, source=self.source_type, search_rank=len(out) + 1))
        return out
