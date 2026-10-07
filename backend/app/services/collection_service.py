"""수집 서비스 — 두 진입점. (content-collector pipeline.py 에서 이동)

API 라우트와 워커는 이 함수들만 부른다. 수집기·추출기를 직접 부르지 않는다.

    collect_keywords(keywords, ...)  키워드 → 네이버 뉴스 → 본문 → 정제
    collect_board(config, ...)       게시판 URL → 글 목록 → 본문 → 정제
    collect_urls(urls, ...)          글 URL 목록 → 본문 → 정제

둘 다 CollectResult 를 돌려준다. 저장(DB·파일)은 여기서 하지 않는다 —
CLI 는 JSON/CSV 로, 나중의 API 서버는 DB 로 저장하게 호출하는 쪽에 맡긴다.

taekwonw-agent 의 collect_workflow.py 와 달리 레인·주제 판정·같은 사건 제거·
초안 작성은 없다. 필요해지면 이 결과 위에 단계를 얹으면 된다.

이미 수집한 글 제외(exclude_urls)
------------------------------
원본은 state.processed_urls 파일로 관리했다. 여기서는 호출하는 쪽이 이미 가진
URL 집합을 넘긴다 (나중에는 DB 에서 조회). canonical_url 기준으로 비교하므로
정규화된 값을 저장해 두면 된다.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime

from app.extractors.cleaner import MIN_CLEAN_LEN, clean_all, clean_content
from app.processors.date_filter import filter_recent, latest_published
from app.extractors.article import extract_all
from app.extractors.robots import allowed
from app.core.logger import get_logger
from app.domain.content import Article
from app.processors.deduplication import canonical_url, dedupe
from app.core.config import BOARD_MAX_WORKERS
from app.collectors.board import BoardCollector, BoardConfig
from app.collectors.news import NewsCollector
from app.collectors.website import WebsiteCollector

log = get_logger(__name__)


@dataclass
class CollectResult:
    articles: list[Article] = field(default_factory=list)
    stats: dict = field(default_factory=dict)          # 단계별 건수
    raw: dict[str, list[dict]] = field(default_factory=dict)  # 키워드별 API 원본
    latest_published: str | None = None                # 다음 실행의 since 값
    failed_keywords: list[str] = field(default_factory=list)  # 호출이 실패한 키워드 (0건과 구분)


def _drop_seen(articles: list[Article], exclude_urls: set[str] | None) -> list[Article]:
    if not exclude_urls:
        return articles
    kept = [a for a in articles if canonical_url(a.url) not in exclude_urls]
    if len(kept) < len(articles):
        log.info(f"이미 수집한 글 {len(articles) - len(kept)}건 제외")
    return kept


def collect_keywords(
    keywords: list[str],
    *,
    count: int = 30,
    sort: str = "sim",
    days: int | None = 3,
    since: datetime | None = None,
    exclude_urls: set[str] | None = None,
    min_len: int = MIN_CLEAN_LEN,
    korean_only: bool = True,
) -> CollectResult:
    """키워드별 네이버 뉴스를 모아 본문까지 채운다.

    같은 기사가 두 키워드에 걸리면 앞 키워드 쪽이 남는다 (search_keyword 기준).
    """
    stats: dict = {}
    collector = NewsCollector(keywords, count=count, sort=sort)
    found = collector.collect()
    stats["검색"] = len(found)

    articles = dedupe(found)
    stats["중복 제거 후"] = len(articles)
    articles = filter_recent(articles, days=days, since=since)
    stats["기간 필터 후"] = len(articles)
    articles = _drop_seen(articles, exclude_urls)
    stats["신규"] = len(articles)

    articles = extract_all(articles)
    stats["본문 확보"] = len(articles)
    articles = clean_all(articles, min_len=min_len, korean_only=korean_only)
    stats["정제 통과"] = len(articles)

    log.info(f"키워드 수집 완료: {stats}")
    return CollectResult(
        articles=articles,
        stats=stats,
        raw=collector.raw,
        latest_published=latest_published(articles),
        failed_keywords=[r.keyword for r in collector.results if not r.ok],
    )


def collect_board(
    cfg: BoardConfig,
    *,
    days: int | None = None,
    since: datetime | None = None,
    exclude_urls: set[str] | None = None,
    min_len: int = 30,
    korean_only: bool = True,
) -> CollectResult:
    """게시판 목록의 글을 모아 본문까지 채운다.

    min_len 기본값이 뉴스(100)보다 낮은 이유: 게시판 공지·짧은 글도 수집 대상이다.
    목록에서 날짜를 못 읽은 글은 기간 필터를 통과하고, 본문 페이지의 메타데이터로
    날짜가 채워지면 한 번 더 거른다.
    """
    stats: dict = {}
    collector = BoardCollector(cfg)
    posts = collector.collect()
    stats["목록"] = len(posts)
    posts = filter_recent(posts, days=days, since=since)
    posts = _drop_seen(posts, exclude_urls)
    stats["신규"] = len(posts)

    # 한 사이트에 요청이 몰리므로 동시 요청 수를 낮게 둔다 (fetch_post 가 간격도 둔다).
    with ThreadPoolExecutor(max_workers=max(1, BOARD_MAX_WORKERS)) as pool:
        posts = list(pool.map(collector.fetch, posts))
    posts = [a for a in posts if a.body.strip()]
    stats["본문 확보"] = len(posts)

    posts = filter_recent(posts, days=days, since=since)
    posts = clean_all(posts, min_len=min_len, korean_only=korean_only)
    stats["정제 통과"] = len(posts)

    log.info(f"게시판 수집 완료: {stats}")
    return CollectResult(articles=posts, stats=stats, latest_published=latest_published(posts))


def collect_urls(
    urls: list[str],
    *,
    exclude_urls: set[str] | None = None,
    min_len: int = 30,
    korean_only: bool = True,
) -> CollectResult:
    """유저가 넣은 글 URL 들의 본문을 가져온다. 기간 필터는 적용하지 않는다."""
    stats: dict = {}
    articles = WebsiteCollector(urls).collect()
    stats["입력"] = len(articles)
    articles = _drop_seen(articles, exclude_urls)
    stats["신규"] = len(articles)
    # 게시판과 같은 예절 — robots.txt 가 막은 글은 받지 않는다.
    blocked = [a.url for a in articles if not allowed(a.url)]
    if blocked:
        log.warning(f"robots.txt 가 막은 글 {len(blocked)}건 제외: {', '.join(blocked)}")
        articles = [a for a in articles if a.url not in blocked]
    articles = extract_all(articles)
    stats["본문 확보"] = len(articles)
    articles = clean_all(articles, min_len=min_len, korean_only=korean_only)
    stats["정제 통과"] = len(articles)
    log.info(f"URL 수집 완료: {stats}")
    return CollectResult(articles=articles, stats=stats, latest_published=latest_published(articles))


def reclean_body(raw_body: str, title: str = "") -> str:
    """저장된 원본 본문을 지금의 정제 규칙으로 다시 정제한다. 정제 규칙을 고친 뒤 기존 글에 적용할 때 쓴다.
    title 을 주면 본문 맨 앞의 제목 줄·부제도 지운다 (수집 때와 같다).

    길이·언어로 걸러 내지는 않는다 — 기준(소스의 min_body_length)은 호출하는 쪽이 판단한다.
    """
    return clean_content(raw_body, title)
