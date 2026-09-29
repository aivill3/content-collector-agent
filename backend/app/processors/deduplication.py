"""중복 제거 — URL 정규화와 제목 비교.

content-collector models.py 에서 분리했다 (원본: taekwonw-agent core/article_models.py).

DB 를 붙이면 canonical_url() 결과를 Content 테이블의 유니크 키로 저장한다.
그러면 '이미 수집한 글 제외'를 DB 가 맡고, dedupe() 는 한 번의 수집 안에서
겹친 글(여러 키워드에 걸린 같은 기사 등)만 거르면 된다.
"""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.logger import get_logger
from app.domain.content import Article

log = get_logger(__name__)

# 추적용 쿼리 파라미터. 같은 글인데 URL 이 달라 보이게 만든다.
# 주의: 게시판은 글 번호가 쿼리에 있다(wr_id, no, idx, seq ...).
#       여기 넣는 이름이 글 번호로 쓰이지 않는지 확인하고 추가할 것.
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "igshid", "spm", "ref", "referer", "referrer",
    "s_kwcid", "n_media", "n_query", "n_rank",
}


def canonical_url(url: str) -> str:
    """중복 판정용 URL 정규화. 추적 파라미터와 끝 슬래시, fragment 를 뗀다.

    스킴과 www 는 유지한다. 다른 사이트를 같은 것으로 합치는 위험보다
    같은 것을 둘로 세는 편이 덜 나쁘다.
    """
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    if not parts.netloc:
        return url.strip()
    query = urlencode([
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS
    ])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _title_key(title: str) -> str:
    """제목 기반 보조 키. 공백·기호를 지우고 ' - 매체명' 접미사를 뗀다."""
    t = title.rsplit(" - ", 1)[0] if " - " in title else title
    return "".join(ch for ch in t if ch.isalnum())


def dedupe(articles: list[Article], *, by_title: bool = True) -> list[Article]:
    """URL 정규화(+ 제목)로 중복 제거. 먼저 온 것을 남긴다.

    by_title=False 는 게시판용이다. 게시판에는 '공지', '문의드립니다' 처럼
    제목이 같은 다른 글이 흔하다.
    """
    seen_url: set[str] = set()
    seen_title: set[str] = set()
    kept: list[Article] = []
    dropped = 0
    for a in articles:
        key_url = canonical_url(a.url)
        key_title = _title_key(a.title) if by_title else ""
        if key_url in seen_url or (key_title and key_title in seen_title):
            dropped += 1
            continue
        seen_url.add(key_url)
        if key_title:
            seen_title.add(key_title)
        kept.append(a)
    if dropped:
        log.info(f"중복 {dropped}건 제거")
    return kept
