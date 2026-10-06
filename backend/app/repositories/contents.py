"""수집된 콘텐츠와 키워드 기록. 수집 결과(CollectResult)를 DB 에 옮겨 담는 곳이다.

services/collection_service 는 저장하지 않는다. 호출하는 쪽(워커)이

    exclude = seen_urls(session, ws_id)
    result = collect_keywords(keywords, ..., exclude_urls=exclude)
    save_collect_result(session, ws_id, job_id, result)
    session.commit()

순서로 부른다.

저장 규칙
--------
- 같은 워크스페이스에서는 url_hash(정규화 URL 의 sha256)로 한 번만 저장한다.
  다른 워크스페이스는 같은 URL 이라도 따로 저장한다 (격리 우선).
- 키워드 기록(content_keyword_hits)은 articles 가 아니라 API 원본(result.raw)에서 만든다.
  수집 파이프라인이 저장 전에 글을 빼기 때문이다:
    · dedupe()      한 번의 수집에서 두 번째 키워드로 걸린 같은 기사를 버린다
    · exclude_urls  이미 저장된 글은 본문 추출 전에 버린다
  원본 응답의 URL 이 워크스페이스에 저장된 콘텐츠와 맞으면 기록을 더한다.
  (콘텐츠, 키워드)마다 처음 찾은 순위만 남는다.
- 일부 키워드가 실패하면 나머지는 저장하고, 실패 내용은 job.error_message 에 남긴다.

동시 실행: 같은 워크스페이스의 두 작업이 같은 URL 을 동시에 저장하면 UNIQUE 위반이 난다.
워커를 붙일 때 소스·워크스페이스 단위로 직렬화하거나 재시도한다.
"""
import hashlib
import uuid
from collections.abc import Iterable
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo

from sqlalchemy import func
from sqlalchemy.orm import defer
from sqlmodel import Session, col

from app.core.config import DISPLAY_TZ
from app.core.timeutil import day_start_utc, days_to_utc_range, display_date
from app.db.models import CollectionJob, Content, ContentKeywordHit, JobApiResponse, Source
from app.db.types import utcnow
from app.domain.content import Article
from app.domain.enums import CollectionPath, JobStatus
from app.processors.date_filter import parse_dt
from app.processors.deduplication import canonical_url
from app.repositories import jobs
from app.repositories.scope import get_scoped, scoped_select
from app.repositories.sources import get_source, list_keywords, normalize_keyword
from app.services.collection_service import CollectResult

_IN_CHUNK = 500   # IN (...) 한 번에 넣는 값 수 (SQLite 변수 상한 대비)


def url_hash(normalized_url: str) -> str:
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()


def _chunks(values: list, size: int = _IN_CHUNK) -> Iterable[list]:
    for i in range(0, len(values), size):
        yield values[i:i + size]


def _contents_by_hash(session: Session, workspace_id: uuid.UUID, hashes: Iterable[str]) -> dict[str, Content]:
    hashes = list(set(hashes))
    found: dict[str, Content] = {}
    for part in _chunks(hashes):
        stmt = scoped_select(Content, workspace_id).where(col(Content.url_hash).in_(part))
        found.update({c.url_hash: c for c in session.exec(stmt)})
    return found


def _to_content(a: Article, *, workspace_id: uuid.UUID, job: CollectionJob,
                normalized: str, hashed: str, now: datetime) -> Content:
    return Content(
        workspace_id=workspace_id,
        source_id=job.source_id,
        first_job_id=job.id,
        collection_path=CollectionPath(a.source),
        url=a.url,
        normalized_url=normalized,
        url_hash=hashed,
        title=a.title,
        publisher=a.press[:200],
        published_at=parse_dt(a.published),     # 못 읽으면 None
        summary=a.summary,
        board_url=a.board_url,
        raw_body=a.body,
        cleaned_body=a.body_clean,
        body_length=len(a.body_clean),
        collected_at=now,
    )


def _raw_hits(raw: dict[str, list[dict]]) -> list[tuple[str, str, int]]:
    """API 원본 → (키워드, URL, 순위). 순위·URL 규칙은 collectors/news.search 와 같다."""
    hits = []
    for keyword, items in raw.items():
        for rank, it in enumerate(items, 1):
            url = (it.get("originallink") or it.get("link") or "").strip()
            if url:
                hits.append((keyword, url, rank))
    return hits


@dataclass
class SaveSummary:
    new_contents: int = 0     # 새로 저장한 콘텐츠
    known_contents: int = 0   # 이번 결과 중 이미 저장돼 있던 콘텐츠
    new_hits: int = 0         # 새로 더한 키워드 기록


def save_collect_result(
    session: Session,
    workspace_id: uuid.UUID,
    job_id: int,
    result: CollectResult,
) -> SaveSummary:
    """수집 결과를 저장하고 작업을 마무리한다 (status=success, 단계별 건수, 소스 최근 실행).

    수집 자체가 예외로 끝났으면 이 함수 대신 jobs.fail_job 을 부른다.
    """
    job = jobs.get_job(session, workspace_id, job_id)
    if job is None:
        raise LookupError(f"작업 {job_id} 가 없습니다")
    source = get_source(session, workspace_id, job.source_id)
    now = utcnow()
    summary = SaveSummary()

    # ── 1. API 원본 ──
    session.add_all(
        JobApiResponse(workspace_id=workspace_id, job_id=job.id, keyword=kw, response=items)
        for kw, items in result.raw.items()
    )

    # ── 2. 콘텐츠 — 워크스페이스 안에서 url_hash 로 한 번만 ──
    incoming: dict[str, tuple[str, Article]] = {}
    for a in result.articles:
        normalized = canonical_url(a.url)
        incoming.setdefault(url_hash(normalized), (normalized, a))
    known = _contents_by_hash(session, workspace_id, incoming)
    summary.known_contents = len(known)
    new = [
        _to_content(a, workspace_id=workspace_id, job=job, normalized=normalized, hashed=h, now=now)
        for h, (normalized, a) in incoming.items() if h not in known
    ]
    session.add_all(new)
    session.flush()
    summary.new_contents = len(new)

    # ── 3. 키워드 기록 — 저장된 글(이번 것 + 전에 것)에 맞는 검색 결과만 ──
    candidates = [(a.search_keyword, a.url, a.search_rank) for a in result.articles if a.search_keyword]
    candidates += _raw_hits(result.raw)
    if candidates:
        by_url = {url: url_hash(canonical_url(url)) for _, url, _ in candidates}
        contents = _contents_by_hash(session, workspace_id, by_url.values())
        keyword_ids = {k.keyword: k.id for k in list_keywords(session, workspace_id, source.id)}
        have = _existing_hits(session, workspace_id, [c.id for c in contents.values()])
        hits = []
        for keyword, url, rank in candidates:
            content = contents.get(by_url[url])
            keyword = normalize_keyword(keyword)
            if content is None or not keyword or (content.id, keyword) in have:
                continue
            have.add((content.id, keyword))
            hits.append(ContentKeywordHit(
                workspace_id=workspace_id, content_id=content.id, keyword=keyword, rank=rank,
                source_keyword_id=keyword_ids.get(keyword), job_id=job.id, found_at=now,
            ))
        session.add_all(hits)
        summary.new_hits = len(hits)

    # ── 4. 작업 마무리 · 다음 실행의 since ──
    failed = result.failed_keywords
    jobs.finish_job(
        session, workspace_id, job.id,
        status=JobStatus.SUCCESS,
        collected_count=summary.new_contents,
        stage_counts=result.stats,
        error_message=f"일부 키워드 수집 실패: {', '.join(failed)}" if failed else None,
    )
    latest = parse_dt(result.latest_published or "")
    if latest and (source.last_published_at is None or latest > source.last_published_at):
        source.last_published_at = latest
        session.add(source)
    session.flush()
    return summary


def _existing_hits(session: Session, workspace_id: uuid.UUID, content_ids: list[int]) -> set[tuple[int, str]]:
    have: set[tuple[int, str]] = set()
    for part in _chunks(content_ids):
        stmt = scoped_select(ContentKeywordHit, workspace_id).where(col(ContentKeywordHit.content_id).in_(part))
        have.update((h.content_id, h.keyword) for h in session.exec(stmt))
    return have


# ── 조회 ────────────────────────────────────────────────

def seen_urls(session: Session, workspace_id: uuid.UUID) -> set[str]:
    """이 워크스페이스에 이미 저장된 정규화 URL — collect_*(exclude_urls=) 로 넘긴다."""
    stmt = scoped_select(Content, workspace_id).with_only_columns(Content.normalized_url)
    return set(session.exec(stmt))


def iter_contents(session: Session, workspace_id: uuid.UUID, *, batch: int = 200) -> Iterable[Content]:
    """워크스페이스의 콘텐츠 전체를 id 순으로 (본문 포함). 한 번에 batch 건씩 읽는다."""
    last_id = 0
    while True:
        stmt = (scoped_select(Content, workspace_id).where(col(Content.id) > last_id)
                .order_by(col(Content.id)).limit(batch))
        rows = list(session.exec(stmt))
        if not rows:
            return
        yield from rows
        last_id = rows[-1].id


def delete_content(session: Session, workspace_id: uuid.UUID, content_id: int) -> bool:
    """콘텐츠 하나를 지운다. 키워드 기록(content_keyword_hits)은 ON DELETE CASCADE 로 함께 지워진다.

    다른 워크스페이스 것이거나 없으면 False. 같은 URL 은 다음 수집 때 다시 저장될 수 있다.
    """
    c = get_content(session, workspace_id, content_id)
    if c is None:
        return False
    session.delete(c)
    session.flush()
    return True


def update_cleaned_body(session: Session, workspace_id: uuid.UUID, content_id: int, cleaned_body: str) -> Content | None:
    """정제 본문과 길이를 바꾼다. 원본(raw_body)은 건드리지 않는다. 다른 워크스페이스 것이면 None."""
    c = get_content(session, workspace_id, content_id)
    if c is None:
        return None
    c.cleaned_body = cleaned_body
    c.body_length = len(cleaned_body)
    session.add(c)
    session.flush()
    return c


def get_content(session: Session, workspace_id: uuid.UUID, content_id: int) -> Content | None:
    return get_scoped(session, Content, workspace_id, content_id)


def list_contents(
    session: Session,
    workspace_id: uuid.UUID,
    *,
    source_id: int | None = None,
    days: tuple[date, date] | None = None,
    by: str = "collected_at",
    tz: tzinfo = DISPLAY_TZ,
    limit: int = 50,
    offset: int = 0,
) -> list[Content]:
    """최근 수집 순. days=(첫날, 마지막 날)이면 표시 시간대 날짜로 거른다 (timeutil.recent_days 등)."""
    stmt = scoped_select(Content, workspace_id)
    if source_id is not None:
        stmt = stmt.where(Content.source_id == source_id)
    if days is not None:
        stmt = _in_days(stmt, by, *days, tz)
    stmt = stmt.order_by(col(Content.collected_at).desc(), col(Content.id).desc()).offset(offset).limit(limit)
    return list(session.exec(stmt))


@dataclass
class ContentQuery:
    """콘텐츠 목록 조건. 기간(first·last)은 표시 시간대 날짜이고 양끝을 포함한다. 한쪽만 줘도 된다."""
    source_id: int | None = None
    collection_path: CollectionPath | None = None
    first: date | None = None
    last: date | None = None
    date_field: str = "collected_at"      # 기간 기준: collected_at | published_at
    q: str = ""                           # 제목 부분 일치 (대소문자 무시)
    sort: str = "collected_at"            # collected_at | published_at
    descending: bool = True


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_contents(
    session: Session,
    workspace_id: uuid.UUID,
    query: ContentQuery,
    *,
    page: int = 1,
    size: int = 20,
    tz: tzinfo = DISPLAY_TZ,
) -> tuple[list[Content], int]:
    """목록 한 페이지와 조건에 맞는 전체 건수. 본문 컬럼은 읽지 않는다 (목록에 필요 없다).

    정렬 값이 없는 행(발행일 모름)은 방향과 상관없이 맨 뒤, 같은 값끼리는 id 순.
    """
    if page < 1 or size < 1:
        raise ValueError("page·size 는 1 이상입니다")
    conds = []
    if query.source_id is not None:
        conds.append(Content.source_id == query.source_id)
    if query.collection_path is not None:
        conds.append(Content.collection_path == CollectionPath(query.collection_path))
    if query.first or query.last:
        column = _date_column(query.date_field)
        if query.first and query.last and query.last < query.first:
            raise ValueError("기간의 끝이 시작보다 앞섭니다")
        if query.first:
            conds.append(column >= day_start_utc(query.first, tz))
        if query.last:
            conds.append(column < day_start_utc(query.last + timedelta(days=1), tz))
    if query.q.strip():
        conds.append(col(Content.title).ilike(f"%{_escape_like(query.q.strip())}%", escape="\\"))

    base = scoped_select(Content, workspace_id).where(*conds)
    total = session.exec(base.with_only_columns(func.count(col(Content.id)))).one()

    sort_col = _date_column(query.sort)
    order = sort_col.desc() if query.descending else sort_col.asc()
    tie = col(Content.id).desc() if query.descending else col(Content.id).asc()
    stmt = (base.options(defer(Content.raw_body), defer(Content.cleaned_body))
            .order_by(order.nulls_last(), tie).offset((page - 1) * size).limit(size))
    return list(session.exec(stmt)), total


def keywords_for(session: Session, workspace_id: uuid.UUID, content_ids: list[int]) -> dict[int, list[str]]:
    """콘텐츠별 찾은 키워드 (찾은 순서). 목록 한 페이지분을 한 번에 읽는다."""
    found: dict[int, list[str]] = {cid: [] for cid in content_ids}
    for part in _chunks(content_ids):
        stmt = scoped_select(ContentKeywordHit, workspace_id).where(
            col(ContentKeywordHit.content_id).in_(part)).order_by(col(ContentKeywordHit.id))
        for h in session.exec(stmt):
            found[h.content_id].append(h.keyword)
    return found


def source_names(session: Session, workspace_id: uuid.UUID, source_ids: Iterable[int]) -> dict[int, str]:
    ids = list(set(source_ids))
    names: dict[int, str] = {}
    for part in _chunks(ids):
        stmt = scoped_select(Source, workspace_id).where(col(Source.id).in_(part))
        names.update({s.id: s.name for s in session.exec(stmt)})
    return names


def list_hits(session: Session, workspace_id: uuid.UUID, content_id: int) -> list[ContentKeywordHit]:
    stmt = scoped_select(ContentKeywordHit, workspace_id).where(ContentKeywordHit.content_id == content_id)
    return list(session.exec(stmt.order_by(col(ContentKeywordHit.id))))


# ── 날짜 단위 집계 (표시 시간대 기준) ─────────────────────────
# 기간은 표시 시간대 날짜 경계를 UTC 로 바꿔 WHERE 에 쓰고, 날짜별 묶기는 가져온 UTC 시각을
# 표시 시간대로 바꿔 파이썬에서 한다. DB 의 시간대 함수에 기대지 않아 SQLite·PostgreSQL 이 같다.

_DATE_COLUMNS = {"collected_at": Content.collected_at, "published_at": Content.published_at}


def _date_column(by: str):
    if by not in _DATE_COLUMNS:
        raise ValueError(f"날짜 기준은 {', '.join(_DATE_COLUMNS)} 중 하나입니다: {by}")
    return _DATE_COLUMNS[by]


def _in_days(stmt, by: str, first: date, last: date, tz: tzinfo):
    column = _date_column(by)
    start, end = days_to_utc_range(first, last, tz)
    return stmt.where(column >= start, column < end)


def count_contents_by_day(
    session: Session,
    workspace_id: uuid.UUID,
    first: date,
    last: date,
    *,
    by: str = "collected_at",
    source_id: int | None = None,
    tz: tzinfo = DISPLAY_TZ,
) -> dict[date, int]:
    """표시 시간대 날짜별 건수. 구간의 모든 날짜가 들어간다 (없는 날은 0).

    by="published_at" 이면 발행일 기준이고, 발행일을 모르는 콘텐츠는 세지 않는다.
    """
    column = _date_column(by)
    stmt = _in_days(scoped_select(Content, workspace_id), by, first, last, tz)
    if source_id is not None:
        stmt = stmt.where(Content.source_id == source_id)
    counts = Counter(display_date(dt, tz) for dt in session.exec(stmt.with_only_columns(column)))
    return {first + timedelta(days=i): counts.get(first + timedelta(days=i), 0)
            for i in range((last - first).days + 1)}


def count_contents_on(session: Session, workspace_id: uuid.UUID, day: date, **kwargs) -> int:
    """표시 시간대 그날 하루의 건수 (예: 오늘 = timeutil.display_today())."""
    return count_contents_by_day(session, workspace_id, day, day, **kwargs)[day]
