"""수집 소스 점검 서비스 — 소스를 저장하기 전에 설정이 맞는지 미리 확인한다.

소스 추가·편집 화면(SOURCE-002~005)의 확인 버튼이 부른다. 아무것도 저장하지 않고,
수집(collection_service)과 같은 수집기·추출기·정제 규칙을 그대로 쓴다.
미리 본 결과와 실제 수집 결과가 어긋나지 않게 하기 위해서다.

    search_preview(keyword)          네이버 뉴스 검색 몇 건 (FN-SRC-003)
    detect_board(url)                robots.txt → 목록 페이지 → 후보 묶음과 글 미리보기 (FN-SRC-004·005)
    check_urls(urls, min_len=...)    주소별로 본문을 가져올 수 있는지 (FN-SRC-007)
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.collectors.board import detect_groups, fetch_list_html, group_posts
from app.collectors.news import NaverCollectError, search
from app.core.config import MAX_WORKERS
from app.core.logger import get_logger
from app.domain.content import Article
from app.extractors.article import extract_body
from app.extractors.cleaner import clean_content, is_korean
from app.extractors.robots import allowed

log = get_logger(__name__)

MAX_CANDIDATES = 5      # 화면에 보여 줄 후보 묶음 수
PREVIEW_POSTS = 5       # 묶음마다 미리 보여 줄 글 수
MAX_CHECK_URLS = 20     # 한 번에 확인할 주소 수 상한 (사이트마다 요청이 나간다)
EXCERPT_LEN = 300       # URL 확인에서 돌려줄 정제 본문 앞부분


def search_preview(keyword: str, *, count: int = 5, sort: str = "sim") -> list[Article]:
    """키워드 하나로 검색해 본 결과. 본문은 받지 않는다.

    호출 실패를 0건으로 돌려주지 않는다 — '검색 결과 없음'과 '키 오류'를 화면에서 구분해야 한다.
    """
    keyword = keyword.strip()
    if not keyword:
        raise ValueError("검색 키워드가 없습니다")
    result = search(keyword, count=count, sort=sort)
    if not result.ok:
        raise NaverCollectError("네이버 검색 호출에 실패했습니다 — 키와 NAVER_API_MODE 를 확인하세요")
    return result.articles


@dataclass
class BoardCandidate:
    pattern: str                                       # URL 모양 (BoardConfig.list_pattern 에 저장)
    links: int                                         # 묶음의 링크 수
    posts: list[Article] = field(default_factory=list)  # 앞쪽 몇 건 (제목·URL·날짜)


@dataclass
class BoardDetection:
    robots: bool          # robots.txt 가 목록 페이지를 허용
    http_ok: bool         # 목록 페이지를 받았음 (robots 차단이면 요청하지 않아 False)
    candidates: list[BoardCandidate] = field(default_factory=list)


def detect_board(url: str) -> BoardDetection:
    """목록 페이지를 한 번만 받아 후보 묶음마다 미리보기 글까지 채운다.

    후보를 바꿔 볼 때마다 사이트에 다시 요청하지 않도록 한 번에 돌려준다.
    """
    url = url.strip()
    if not allowed(url):
        log.warning(f"robots.txt 가 막은 목록 페이지: {url}")
        return BoardDetection(robots=False, http_ok=False)
    html = fetch_list_html(url)
    if not html:
        return BoardDetection(robots=True, http_ok=False)
    candidates = [
        BoardCandidate(pattern=shape, links=len(links), posts=group_posts(html, url, links)[:PREVIEW_POSTS])
        for shape, links in detect_groups(html, url)[:MAX_CANDIDATES]
    ]
    log.info(f"게시판 탐지: {url} → 후보 {len(candidates)}개")
    return BoardDetection(robots=True, http_ok=True, candidates=candidates)


@dataclass
class UrlCheck:
    url: str
    result: str           # "ok" | "short" | "foreign" | "robots" | "fail"
    length: int = 0       # 정제 후 본문 길이 (자)
    article: Article | None = None   # 제목·사이트명·발행일 (페이지 메타데이터)
    excerpt: str = ""     # 정제 본문 앞부분


def _check_one(url: str, min_len: int, korean_only: bool) -> UrlCheck:
    if not allowed(url):
        return UrlCheck(url, "robots")
    article = extract_body(Article(url=url))
    if not article.body.strip():
        return UrlCheck(url, "fail", article=article)
    body = clean_content(article.body)
    if len(body) < min_len:
        result = "short"
    elif korean_only and not is_korean(body):
        result = "foreign"
    else:
        result = "ok"
    return UrlCheck(url, result, len(body), article, body[:EXCERPT_LEN])


def check_urls(urls: list[str], *, min_len: int = 30, korean_only: bool = True) -> list[UrlCheck]:
    """주소마다 실제 수집과 같은 규칙(robots → 본문 추출 → 정제 → 길이·언어)으로 확인한다.

    빈 줄·중복은 빼고 입력 순서대로 돌려준다.
    """
    unique = list(dict.fromkeys(u.strip() for u in urls if u and u.strip()))
    if not unique:
        raise ValueError("확인할 주소가 없습니다")
    if len(unique) > MAX_CHECK_URLS:
        raise ValueError(f"한 번에 {MAX_CHECK_URLS}개까지 확인할 수 있습니다")
    with ThreadPoolExecutor(max_workers=max(1, min(MAX_WORKERS, len(unique)))) as pool:
        return list(pool.map(lambda u: _check_one(u, min_len, korean_only), unique))
