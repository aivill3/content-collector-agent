"""게시판 수집기 — 사이트 URL 을 받아 게시판 목록의 글 링크를 모은다.

taekwonw-agent 에 없던 새 모듈이다. 여기서는 '어떤 글이 있는가(목록)'만 찾고,
본문은 뉴스와 같은 경로(extractors/article → extractors/cleaner)로 처리한다.

두 가지 방식
-----------
1. 수동 설정 (BoardConfig.item_selector 지정)
   목록의 한 줄을 가리키는 CSS 선택자를 준다. 가장 정확하다.
   예) 그누보드  item_selector="#bo_list tbody tr", link_selector="td.td_subject a"

2. 자동 탐지 (item_selector 비움)
   페이지의 링크를 'URL 모양'으로 묶어, 글 번호만 다른 링크가 가장 많이 반복되는
   묶음을 게시글 목록으로 본다.
     /bbs/board.php?bo_table=free&wr_id=123  →  /bbs/board.php?bo_table=free&wr_id={n}
     /news/articleView.html?idxno=4567       →  /news/articleView.html?idxno={n}
     /notice/view/88                         →  /notice/view/{n}
   게시판 대부분이 이 규칙에 맞지만 확률적이다. 결과가 이상하면 detect 명령으로
   어떤 묶음이 잡혔는지 보고 수동 설정으로 바꾼다.

한계
----
- 자바스크립트로 목록을 그리는 게시판은 requests 로 받은 HTML 에 글이 없다.
  이때는 0건이 나오며 경고를 남긴다. Playwright 렌더링을 붙이는 것이 다음 단계다
  (fetch_list_html 만 바꾸면 되도록 분리해 두었다).
- 로그인이 필요한 게시판은 대상이 아니다.

예절
----
- RESPECT_ROBOTS=true(기본)면 robots.txt 가 막은 경로는 받지 않는다.
- 같은 사이트 요청 사이에 BOARD_REQUEST_DELAY 초를 둔다.
"""
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, Tag

from app.extractors.article import extract_body, fetch_html
from app.core.logger import get_logger
from app.collectors.base import Collector
from app.domain.content import Article
from app.processors.deduplication import canonical_url
from app.core.config import (
    BOARD_REQUEST_DELAY,
    KST,
    REQUEST_TIMEOUT,
    RESPECT_ROBOTS,
)

log = get_logger(__name__)


@dataclass
class BoardConfig:
    """게시판 하나의 수집 설정. 나중에 DB 의 '수집 소스' 한 행이 된다."""
    list_url: str
    # ── 수동 설정 (비우면 자동 탐지) ──
    item_selector: str = ""       # 목록 한 줄 (예: "#bo_list tbody tr")
    link_selector: str = "a[href]"  # 줄 안의 글 링크
    title_selector: str = ""      # 줄 안의 제목 (비우면 링크 텍스트)
    date_selector: str = ""       # 줄 안의 날짜 (비우면 줄 전체 텍스트에서 찾음)
    body_selector: str = ""       # 글 페이지의 본문 영역 (비우면 trafilatura 자동 추출)
    # ── 범위 ──
    page_param: str = ""          # 페이지 번호 쿼리 이름 (예: "page"). 비우면 첫 페이지만
    start_page: int = 1
    max_pages: int = 1
    max_items: int = 50
    include_pattern: str = ""     # 글 URL 이 이 정규식에 맞아야 채택 (선택)
    exclude_notice: bool = False  # '공지' 표시 줄 제외 (상단 고정 공지가 매번 잡히는 것 방지)


# ── robots.txt ─────────────────────────────────────────

_robots_cache: dict[str, RobotFileParser | None] = {}


def allowed(url: str) -> bool:
    """robots.txt 가 이 URL 을 허용하는가. robots.txt 를 못 읽으면 허용으로 본다."""
    if not RESPECT_ROBOTS:
        return True
    parts = urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _robots_cache:
        rp: RobotFileParser | None = RobotFileParser()
        try:
            resp = requests.get(f"{root}/robots.txt", timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp = None   # 없음(404 등) = 제한 없음
        except requests.RequestException:
            rp = None
        _robots_cache[root] = rp
    rp = _robots_cache[root]
    return True if rp is None else rp.can_fetch("*", url)


# ── 날짜 ───────────────────────────────────────────────

_RE_YMD = re.compile(r"(20\d{2})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})")
_RE_YY_MD = re.compile(r"(?<![\d])(\d{2})[-./](\d{1,2})[-./](\d{1,2})(?![\d])")
_RE_MD = re.compile(r"(?<![\d.\-/])(\d{1,2})[-./](\d{1,2})(?![\d.\-/])")
_RE_HM = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")
_RE_AGO = re.compile(r"(\d+)\s*(분|시간|일)\s*전")


def parse_board_date(text: str, now: datetime | None = None) -> str:
    """게시판 목록의 날짜 표기 → ISO 8601(KST). 못 읽으면 빈 문자열.

    게시판은 오늘 글을 '14:32', 올해 글을 '09-25', 그 전을 '2025.12.01' 처럼
    섞어 쓰는 경우가 흔하다. 순서대로 시도한다.
    """
    now = now or datetime.now(KST)
    text = text or ""

    def _mk(y: int, m: int, d: int) -> str:
        try:
            return datetime(y, m, d, tzinfo=KST).isoformat()
        except ValueError:
            return ""

    if m := _RE_YMD.search(text):
        return _mk(int(m[1]), int(m[2]), int(m[3]))
    if m := _RE_YY_MD.search(text):
        return _mk(2000 + int(m[1]), int(m[2]), int(m[3]))
    if m := _RE_AGO.search(text):
        n, unit = int(m[1]), m[2]
        delta = {"분": timedelta(minutes=n), "시간": timedelta(hours=n), "일": timedelta(days=n)}[unit]
        return (now - delta).isoformat()
    if m := _RE_MD.search(text):
        month, day = int(m[1]), int(m[2])
        if 1 <= month <= 12 and 1 <= day <= 31:
            got = _mk(now.year, month, day)
            # 1월에 보는 '12-30' 은 작년 글이다
            if got and datetime.fromisoformat(got) > now + timedelta(days=1):
                got = _mk(now.year - 1, month, day)
            return got
    if m := _RE_HM.search(text):
        return now.replace(hour=int(m[1]), minute=int(m[2]), second=0, microsecond=0).isoformat()
    return ""


# ── 목록 페이지 ────────────────────────────────────────

def fetch_list_html(url: str) -> str | None:
    """목록 페이지 HTML. JS 렌더링(Playwright)을 붙일 때 이 함수만 바꾼다."""
    return fetch_html(url)


def page_url(list_url: str, param: str, page: int) -> str:
    parts = urlsplit(list_url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != param]
    query.append((param, str(page)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


# 페이지 이동 링크의 쿼리 이름. 자동 탐지에서 이것만 다른 묶음은 글 목록이 아니다.
_PAGING_KEYS = {"page", "pg", "p", "pageno", "pageindex", "cpage", "curpage", "pagenum", "offset", "start"}
_RE_DIGITS = re.compile(r"\d+")
_SKIP_SCHEMES = ("javascript:", "mailto:", "tel:", "#")
_ROW_TAGS = ("tr", "li", "article", "dd")
_RE_NOTICE = re.compile(r"공지|notice|NOTICE|📢")


def _shape(url: str) -> tuple[str, bool]:
    """URL 모양. 숫자 덩어리를 {n} 으로 바꾼다. (모양, 페이지 이동 링크 여부)"""
    parts = urlsplit(url)
    path = _RE_DIGITS.sub("{n}", parts.path)
    varying: list[str] = []
    q = []
    for k, v in sorted(parse_qsl(parts.query, keep_blank_values=True)):
        if v.isdigit():
            q.append(f"{k}={{n}}")
            varying.append(k.lower())
        else:
            q.append(f"{k}={v}")
    paging_only = bool(varying) and all(k in _PAGING_KEYS for k in varying) and "{n}" not in path
    return f"{parts.netloc}{path}?{'&'.join(q)}", paging_only


def _content_root(soup: BeautifulSoup) -> Tag:
    """머리말·메뉴·꼬리말을 뗀 본문 영역. 메뉴 링크가 목록으로 오인되는 것을 줄인다."""
    for tag in soup.find_all(["header", "nav", "footer", "aside", "script", "style"]):
        tag.decompose()
    return soup.body or soup


def _row_of(a: Tag) -> Tag:
    """링크를 감싼 '목록 한 줄'. 날짜·공지 표시를 찾는 범위다."""
    for parent in a.parents:
        if parent.name in _ROW_TAGS:
            return parent
    return a.parent or a


def _text(el: Tag | None) -> str:
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def _posts_manual(soup: BeautifulSoup, base: str, cfg: BoardConfig) -> list[Article]:
    out = []
    for row in soup.select(cfg.item_selector):
        link = row.select_one(cfg.link_selector)
        if not link or not link.get("href") or link["href"].startswith(_SKIP_SCHEMES):
            continue
        if cfg.exclude_notice and _RE_NOTICE.search(_text(row)[:20]):
            continue
        title_el = row.select_one(cfg.title_selector) if cfg.title_selector else link
        date_text = _text(row.select_one(cfg.date_selector)) if cfg.date_selector else _text(row)
        out.append(Article(
            title=_text(title_el) or link.get("title", ""),
            url=urljoin(base, link["href"]),
            published=parse_board_date(date_text),
        ))
    return out


def detect_groups(html: str, base: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """자동 탐지 후보 묶음. [(URL 모양, [(url, 링크 텍스트), ...])] — 큰 순서.

    detect 명령이 이 결과를 그대로 보여 준다. 잘못 잡혔을 때 원인을 볼 수 있게.
    """
    soup = BeautifulSoup(html, "lxml")
    root = _content_root(soup)
    host = urlsplit(base).netloc
    groups: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    for a in root.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(_SKIP_SCHEMES):
            continue
        url = urljoin(base, href)
        if urlsplit(url).netloc != host:
            continue
        shape, paging_only = _shape(url)
        if paging_only or "{n}" not in shape:
            continue
        text = _text(a) or a.get("title", "")
        key = canonical_url(url)
        # 같은 글에 링크가 여럿(제목·썸네일·댓글수)이면 가장 긴 텍스트를 제목으로
        existing = groups[shape].get(key)
        if existing is None or len(text) > len(existing[1]):
            groups[shape][key] = (url, text)
    ranked = sorted(
        ((s, list(v.values())) for s, v in groups.items()),
        # 제목다운(4자 이상) 링크 수가 많은 묶음이 게시글 목록일 가능성이 높다
        key=lambda g: sum(len(t) >= 4 for _, t in g[1]),
        reverse=True,
    )
    return ranked


def _posts_auto(html: str, base: str, cfg: BoardConfig) -> list[Article]:
    groups = detect_groups(html, base)
    if not groups or len(groups[0][1]) < 3:
        return []
    shape, links = groups[0]
    log.info(f"자동 탐지: {shape} ({len(links)}건)")
    wanted = {canonical_url(u) for u, _ in links}

    # 날짜·공지 표시를 보려면 링크의 '줄'이 필요하다. 다시 파싱해 해당 링크를 찾는다.
    soup = BeautifulSoup(html, "lxml")
    rows: dict[str, Tag] = {}
    for a in _content_root(soup).find_all("a", href=True):
        key = canonical_url(urljoin(base, a["href"].strip()))
        if key in wanted and key not in rows:
            rows[key] = _row_of(a)

    out = []
    for url, text in links:
        row = rows.get(canonical_url(url))
        row_text = _text(row)
        if cfg.exclude_notice and _RE_NOTICE.search(row_text[:20]):
            continue
        # 줄 텍스트에서 제목을 빼고 날짜를 찾는다 (제목 안의 숫자를 날짜로 오인하지 않게)
        rest = row_text.replace(text, " ") if text else row_text
        out.append(Article(title=text, url=url, published=parse_board_date(rest)))
    return out


def list_posts(cfg: BoardConfig) -> list[Article]:
    """게시판 목록에서 글 링크를 모은다. 본문은 채우지 않는다."""
    include = re.compile(cfg.include_pattern) if cfg.include_pattern else None
    pages = range(cfg.start_page, cfg.start_page + max(1, cfg.max_pages)) if cfg.page_param else [None]
    seen: set[str] = set()
    posts: list[Article] = []

    for i, page in enumerate(pages):
        url = page_url(cfg.list_url, cfg.page_param, page) if page is not None else cfg.list_url
        if not allowed(url):
            log.warning(f"robots.txt 가 막은 경로라 건너뜁니다: {url}")
            break
        if i:
            time.sleep(BOARD_REQUEST_DELAY)
        html = fetch_list_html(url)
        if not html:
            log.warning(f"목록 페이지를 받지 못했습니다: {url}")
            break
        soup = BeautifulSoup(html, "lxml")
        found = _posts_manual(soup, url, cfg) if cfg.item_selector else _posts_auto(html, url, cfg)

        new = 0
        for a in found:
            key = canonical_url(a.url)
            if key in seen or (include and not include.search(a.url)):
                continue
            seen.add(key)
            a.source = "board"
            a.board_url = cfg.list_url
            a.search_rank = len(posts) + 1
            posts.append(a)
            new += 1
        log.info(f"목록 {url} → 새 글 {new}건")
        if new == 0:
            if i == 0:
                log.warning(
                    "첫 페이지에서 글을 찾지 못했습니다. 자바스크립트로 목록을 그리는 "
                    "게시판이거나 선택자가 맞지 않습니다 (detect 명령으로 확인)"
                )
            break               # 더 넘겨도 같은 글이거나 빈 페이지
        if len(posts) >= cfg.max_items:
            break
    return posts[: cfg.max_items]


# ── 글 본문 ────────────────────────────────────────────

def fetch_post(article: Article, cfg: BoardConfig) -> Article:
    """글 하나의 본문. body_selector 가 있으면 그 영역만, 없으면 trafilatura 자동 추출.

    게시판 글은 표 레이아웃·짧은 본문이라 trafilatura 가 본문을 못 찾는 경우가
    뉴스보다 잦다. 그럴 때 body_selector 로 영역을 지정한다.
    """
    if not allowed(article.url):
        log.warning(f"robots.txt 가 막은 글이라 건너뜁니다: {article.url}")
        return article
    time.sleep(BOARD_REQUEST_DELAY)
    html = fetch_html(article.url)
    if not html:
        return article
    if cfg.body_selector:
        el = BeautifulSoup(html, "lxml").select_one(cfg.body_selector)
        if el:
            article.body = el.get_text("\n", strip=True)
            return article
        log.info(f"body_selector 로 본문을 못 찾아 자동 추출합니다: {article.url}")
    return extract_body(article, html=html)


class BoardCollector(Collector):
    """게시판 설정 하나 → 글 목록. 본문은 fetch_post 규칙(간격·본문 영역)으로 받는다."""
    source_type = "board"

    def __init__(self, cfg: BoardConfig):
        self.cfg = cfg

    def collect(self) -> list[Article]:
        return list_posts(self.cfg)

    def fetch(self, article: Article) -> Article:
        return fetch_post(article, self.cfg)
