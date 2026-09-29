"""발행일 기준 기간 필터.

taekwonw-agent 의 agents/collecting/date_filter.py 를 단순화했다.
원본은 '직전 실행 시각'을 상태 파일에서 읽어 창을 정했는데, 여기서는 호출하는
쪽이 기간(days) 또는 기준 시각(since)을 직접 넘긴다. 유저·작업마다 기준이 다르고,
그 상태는 나중에 DB 가 들고 있게 될 것이기 때문이다.

발행일을 읽지 못한 글은 버리지 않고 통과시킨다 (원본과 같은 정책).
매체·게시판마다 날짜 형식이 제각각이라 실패를 배제로 처리하면 멀쩡한 글이
조용히 사라진다. 중복은 URL 로 따로 거른다.
"""
from datetime import datetime, timedelta

from app.core.logger import get_logger
from app.domain.content import Article
from app.core.config import KST

log = get_logger(__name__)


def parse_dt(value: str) -> datetime | None:
    """ISO 8601 문자열 → datetime. 시간대가 없으면 KST 로 간주. 실패 시 None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt.replace(tzinfo=KST) if dt.tzinfo is None else dt


def filter_recent(
    articles: list[Article],
    *,
    days: int | None = None,
    since: datetime | None = None,
) -> list[Article]:
    """기준 시각 이후 발행분만 남긴다. days·since 둘 다 없으면 그대로 돌려준다.

    둘 다 주면 더 이른 쪽(= 더 넓은 창)을 쓴다. 원본의 '조회 창 확대'와 같은 이유다:
    직전 실행 이후만 보면 첫 시도에서 본문 추출에 실패한 글을 영영 놓친다.
    """
    candidates = []
    if days is not None:
        candidates.append(datetime.now(KST) - timedelta(days=days))
    if since is not None:
        candidates.append(since if since.tzinfo else since.replace(tzinfo=KST))
    if not candidates:
        return articles
    cutoff = min(candidates)

    kept, dropped, unknown = [], 0, 0
    for a in articles:
        dt = parse_dt(a.published)
        if dt is None:
            unknown += 1
            kept.append(a)
        elif dt >= cutoff:
            kept.append(a)
        else:
            dropped += 1
    log.info(
        f"날짜 필터({cutoff:%Y-%m-%d %H:%M} 이후): {len(kept)}건 통과, {dropped}건 제외"
        + (f", {unknown}건 날짜 불명(통과)" if unknown else "")
    )
    return kept


def latest_published(articles: list[Article]) -> str | None:
    """수집분 중 가장 늦은 발행 시각. 다음 실행의 since 로 저장해 두면 된다.

    '지금 시각'을 저장하면 안 된다. 발행과 검색 노출 사이 지연 때문에 그 사이
    나온 글을 영구히 놓친다.
    """
    valid = [t for t in (parse_dt(a.published) for a in articles) if t]
    return max(valid).isoformat() if valid else None
