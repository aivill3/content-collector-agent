"""소스 점검 API 의 요청·응답 (frontend/lib/types.ts 의 같은 이름 타입과 맞춘다).

날짜는 DISPLAY_TZ 기준 ISO 8601 문자열이고(schemas/base.display_iso), 모르면 빈 값이다. 화면 표기(MM-DD 등)는 프론트가 정한다.
"""
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field

from app.domain.content import Article
from app.schemas.base import CamelModel, display_iso
from app.services.source_check_service import MAX_CHECK_URLS, BoardDetection, UrlCheck


def _outlet(a: Article) -> str:
    """언론사명. 네이버 검색 결과에는 없어 기사 주소의 도메인으로 대신한다."""
    if a.press:
        return a.press
    host = urlsplit(a.url).netloc
    return host.removeprefix("www.")


# ── 뉴스 검색 테스트 (FN-SRC-003) ──

class SearchTestRequest(CamelModel):
    keyword: str = Field(min_length=1, max_length=100)


class SearchPreview(CamelModel):
    title: str
    url: str
    outlet: str
    date: str
    keyword: str

    @classmethod
    def of(cls, a: Article) -> "SearchPreview":
        return cls(title=a.title, url=a.url, outlet=_outlet(a), date=display_iso(a.published), keyword=a.search_keyword)


# ── 게시판 자동 탐지 (FN-SRC-004·005) ──

class BoardDetectRequest(CamelModel):
    url: str = Field(min_length=1, max_length=2000)


class BoardPostPreview(CamelModel):
    title: str
    url: str
    date: str


class BoardCandidate(CamelModel):
    pattern: str
    links: int
    posts: list[BoardPostPreview]


class BoardDetectResult(CamelModel):
    robots: bool
    http_ok: bool
    candidates: list[BoardCandidate]

    @classmethod
    def of(cls, d: BoardDetection) -> "BoardDetectResult":
        return cls(
            robots=d.robots,
            http_ok=d.http_ok,
            candidates=[
                BoardCandidate(
                    pattern=c.pattern,
                    links=c.links,
                    posts=[BoardPostPreview(title=p.title, url=p.url, date=display_iso(p.published)) for p in c.posts],
                )
                for c in d.candidates
            ],
        )


# ── URL 확인 (FN-SRC-007) ──

class UrlCheckRequest(CamelModel):
    urls: list[str] = Field(min_length=1, max_length=MAX_CHECK_URLS)
    min_len: int = Field(default=30, ge=0, le=100_000)
    korean_only: bool = True


class UrlCheckResult(CamelModel):
    url: str
    result: Literal["ok", "short", "foreign", "robots", "fail"]
    length: int           # 정제 후 본문 길이 (자)
    title: str
    outlet: str
    date: str
    excerpt: str          # 정제 본문 앞부분

    @classmethod
    def of(cls, u: UrlCheck) -> "UrlCheckResult":
        a = u.article
        return cls(
            url=u.url, result=u.result, length=u.length, excerpt=u.excerpt,
            title=a.title if a else "", outlet=_outlet(a) if a else "", date=display_iso(a.published) if a else "",
        )
