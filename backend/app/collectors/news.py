"""네이버 검색 API(뉴스) 수집기.

taekwonw-agent 의 tools/naver_news_client.py 이식. 호출·파싱 로직은 그대로다.

이식하며 바꾼 점:
  - 키워드·건수·정렬을 설정 파일(SEARCH_KEYWORDS 등)이 아니라 인자로 받는다.
    유저가 입력한 키워드를 그대로 넘기기 위해서다.
  - 응답 원본을 data/raw/ 파일로 쓰지 않고 SearchResult.raw 로 돌려준다.
    원본 보존의 이유(검색 결과는 시점마다 달라 나중에 재현이 안 된다)는 그대로
    유효하므로, 호출하는 쪽이 DB 에 함께 저장하는 것을 권한다.
  - start 파라미터를 열었다. 100건을 넘게 받으려면 페이지를 넘겨야 한다.

originallink(언론사 원문)를 link(네이버 뉴스 페이지)보다 우선한다.
본문 추출이 더 잘 되고, 다른 키워드로 들어온 같은 기사와 URL 이 맞아 중복 판정에 걸린다.
"""
import html
import re
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime

import requests

from app.core.logger import get_logger
from app.collectors.base import Collector
from app.domain.content import Article
from app.core.config import (
    KST,
    NAVER_API_MODE,
    NAVER_CLIENT_ID,
    NAVER_CLIENT_SECRET,
    REQUEST_TIMEOUT,
)

log = get_logger(__name__)

HUB_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
LEGACY_URL = "https://openapi.naver.com/v1/search/news.json"

_RE_TAG = re.compile(r"<[^>]+>")   # 네이버가 검색어에 씌우는 <b> 태그
_VALID_SORTS = ("sim", "date")     # sim=관련도순(검색 화면 기본), date=최신순
DISPLAY_MAX = 100                  # API 한 번에 최대 100건
START_MAX = 1000                   # API start 상한


class NaverCollectError(RuntimeError):
    """자격증명이 없거나, 요청한 키워드 전부가 실패했다."""


@dataclass
class SearchResult:
    keyword: str
    articles: list[Article] = field(default_factory=list)
    raw: list[dict] = field(default_factory=list)   # API items 원본
    ok: bool = True                                  # False = 호출 실패 (0건과 구분)


def _clean(text: str) -> str:
    return html.unescape(_RE_TAG.sub("", text or "")).strip()


def _to_kst_iso(pub_date: str) -> str:
    """RFC 2822(Mon, 10 Aug 2026 09:07:13 +0900) → KST ISO 8601. 실패 시 원본."""
    if not pub_date:
        return ""
    try:
        return parsedate_to_datetime(pub_date).astimezone(KST).isoformat()
    except (TypeError, ValueError):
        return pub_date


def _endpoints() -> list[tuple[str, str, dict]]:
    hub = ("API HUB", HUB_URL, {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET,
    })
    legacy = ("개발자센터(구)", LEGACY_URL, {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    })
    if NAVER_API_MODE == "hub":
        return [hub]
    if NAVER_API_MODE == "legacy":
        return [legacy]
    return [hub, legacy]


def _request(query: str, display: int, start: int, sort: str) -> list[dict] | None:
    """한 페이지 호출. 모든 방식이 실패하면 None."""
    params = {"query": query, "display": display, "start": start, "sort": sort}
    for name, url, headers in _endpoints():
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (401, 403):
                log.warning(f"네이버 {name} 인증 실패({resp.status_code})")
                continue
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            log.warning(f"네이버 {name} 호출 실패 ('{query}'): {e}")
    return None


def search(query: str, *, count: int = 30, sort: str = "sim") -> SearchResult:
    """키워드 하나를 검색해 네이버 응답 순서대로 Article 목록을 돌려준다.

    count 가 100 을 넘으면 start 를 넘기며 여러 번 호출한다 (API 상한 1000).
    """
    result = SearchResult(keyword=query)
    if not (NAVER_CLIENT_ID and NAVER_CLIENT_SECRET):
        raise NaverCollectError("NAVER_CLIENT_ID/SECRET 이 없습니다 (.env 확인)")

    sort = sort.strip().lower()
    if sort not in _VALID_SORTS:
        log.warning(f"sort='{sort}' 는 지원하지 않습니다. sim 으로 진행합니다")
        sort = "sim"

    count = max(1, min(count, START_MAX))
    start = 1
    while len(result.raw) < count and start <= START_MAX:
        display = min(DISPLAY_MAX, count - len(result.raw))
        items = _request(query, display, start, sort)
        if items is None:
            if not result.raw:          # 첫 페이지부터 실패 = 호출 실패
                result.ok = False
                log.warning(f"네이버 '{query}' 수집 실패")
                return result
            break                       # 뒤 페이지 실패 = 받은 만큼으로 진행
        result.raw.extend(items)
        if len(items) < display:        # 결과가 더 없다
            break
        start += display

    # 순위는 URL 없는 항목을 건너뛰기 전에 매긴다 (원본 응답 위치와 대조 가능하게).
    for rank, it in enumerate(result.raw, 1):
        url = (it.get("originallink") or it.get("link") or "").strip()
        if not url:
            continue
        result.articles.append(Article(
            title=_clean(it.get("title", "")),
            url=url,
            source="naver",
            published=_to_kst_iso(it.get("pubDate", "")),
            summary=_clean(it.get("description", "")),
            search_keyword=query,
            search_rank=rank,
        ))
    log.info(f"'{query}' {len(result.articles)}건 수집 (정렬={sort})")
    return result


def search_many(keywords: list[str], *, count: int = 30, sort: str = "sim") -> list[SearchResult]:
    """여러 키워드를 차례로 검색한다. 전부 실패하면 NaverCollectError.

    일부만 실패하면 경고를 남기고 나머지로 진행한다. 빈 목록을 조용히 돌려주면
    '새 기사 없음'과 '수집 장애'가 구분되지 않는다.
    """
    keywords = [k.strip() for k in keywords if k and k.strip()]
    if not keywords:
        raise NaverCollectError("검색 키워드가 없습니다")
    results = [search(kw, count=count, sort=sort) for kw in keywords]
    failed = [r.keyword for r in results if not r.ok]
    if len(failed) == len(results):
        raise NaverCollectError(
            "모든 키워드의 네이버 수집이 실패했습니다 — 키와 방식을 확인하세요. "
            "API HUB 키라면 NAVER_API_MODE=hub 로 두면 재시도 없이 바로 붙습니다"
        )
    if failed:
        log.warning(f"일부 키워드 수집 실패, 나머지로 진행합니다: {', '.join(failed)}")
    return results


class NewsCollector(Collector):
    """키워드 목록 → 네이버 뉴스. 호출 후 self.results 에 키워드별 원본이 남는다."""
    source_type = "naver"

    def __init__(self, keywords: list[str], *, count: int = 30, sort: str = "sim"):
        self.keywords = keywords
        self.count = count
        self.sort = sort
        self.results: list[SearchResult] = []

    def collect(self) -> list[Article]:
        self.results = search_many(self.keywords, count=self.count, sort=self.sort)
        return [a for r in self.results for a in r.articles]

    @property
    def raw(self) -> dict[str, list[dict]]:
        return {r.keyword: r.raw for r in self.results}
