"""키워드 분석 결과 — content_analyses · content_terms · content_keyword_stats.

분석(services/analysis_service)은 저장하지 않는다. workers/analysis.py 가 분석하고 여기 함수로 저장한다.
모든 함수는 workspace_id 를 받고, 다른 워크스페이스의 콘텐츠는 없는 것으로 다룬다. flush 까지만 한다.
"""
import uuid
from collections.abc import Iterable

from sqlalchemy import delete
from sqlmodel import Session, col

from app.analyzers.morph import ANALYZER
from app.db.models import Content, ContentAnalysis, ContentKeywordHit, ContentKeywordStat, ContentTerm
from app.db.types import utcnow
from app.domain.analysis import DEFAULT_SETTINGS, AnalysisSettings
from app.domain.enums import Relevance
from app.repositories.scope import scoped_select
from app.services.analysis_service import KeywordStat, TextAnalysis, best_relevance

_IN_CHUNK = 500   # IN (...) 한 번에 넣는 값 수 (SQLite 변수 상한 대비)


def _chunks(values: list, size: int = _IN_CHUNK) -> Iterable[list]:
    for i in range(0, len(values), size):
        yield values[i:i + size]


def get_settings(session: Session, workspace_id: uuid.UUID, source_id: int | None = None) -> AnalysisSettings:
    """적용할 분석 설정. 설정 저장(SETTING-001)이 생기기 전이라 모두 기본값이다.

    붙일 때 적용 순서: 시스템 기본값 → 워크스페이스 기본값 → 소스별.
    """
    return DEFAULT_SETTINGS


# ── 대상 찾기 ──────────────────────────────────────────────

def unanalyzed_content_ids(session: Session, workspace_id: uuid.UUID) -> list[int]:
    """분석 결과가 없는 콘텐츠 id (id 순)."""
    done = scoped_select(ContentAnalysis, workspace_id).with_only_columns(col(ContentAnalysis.content_id))
    stmt = (scoped_select(Content, workspace_id).where(col(Content.id).not_in(done))
            .with_only_columns(col(Content.id)).order_by(col(Content.id)))
    return list(session.exec(stmt))


def all_content_ids(session: Session, workspace_id: uuid.UUID) -> list[int]:
    stmt = scoped_select(Content, workspace_id).with_only_columns(col(Content.id)).order_by(col(Content.id))
    return list(session.exec(stmt))


def hits_without_stats(session: Session, workspace_id: uuid.UUID) -> dict[int, list[str]]:
    """키워드 기록은 있는데 언급 수치가 없는 (콘텐츠, 키워드). 이미 분석한 글이 다음 수집에서
    새 키워드로 다시 걸리면 생긴다. 콘텐츠 id → 키워드 목록."""
    have = {(s.content_id, s.keyword) for s in session.exec(scoped_select(ContentKeywordStat, workspace_id))}
    analyzed = scoped_select(ContentAnalysis, workspace_id).with_only_columns(col(ContentAnalysis.content_id))
    stmt = scoped_select(ContentKeywordHit, workspace_id).where(col(ContentKeywordHit.content_id).in_(analyzed))
    missing: dict[int, list[str]] = {}
    for h in session.exec(stmt.order_by(col(ContentKeywordHit.id))):
        if (h.content_id, h.keyword) not in have:
            missing.setdefault(h.content_id, []).append(h.keyword)
    return missing


# ── 저장 ──────────────────────────────────────────────────

def save_text_analysis(
    session: Session,
    workspace_id: uuid.UUID,
    content_id: int,
    result: TextAnalysis,
    *,
    body_length: int,
    settings_version: int,
) -> ContentAnalysis:
    """글 단위 지표와 단어 횟수를 저장한다. 이미 있으면 지우고 새로 쓴다 (단어·키워드 수치 포함)."""
    clear_analysis(session, workspace_id, [content_id])
    row = ContentAnalysis(
        workspace_id=workspace_id, content_id=content_id, settings_version=settings_version, analyzer=ANALYZER,
        body_length=body_length, tokens=result.tokens, unique_tokens=result.unique_tokens, nouns=result.nouns,
        sentences=result.sentences, avg_sentence_len=result.avg_sentence_len, ttr=result.ttr,
        analyzed_at=utcnow(),
    )
    session.add(row)
    session.add_all(
        ContentTerm(workspace_id=workspace_id, content_id=content_id, term=t.term[:100], pos=t.pos, count=t.count)
        for t in result.terms
    )
    session.flush()
    return row


def add_keyword_stats(
    session: Session,
    workspace_id: uuid.UUID,
    content_id: int,
    stats: list[tuple[KeywordStat, Relevance]],
) -> None:
    """키워드별 수치·판정을 더하고 글의 관련도(가장 강한 판정)를 다시 맞춘다. 이미 있는 키워드는 건너뛴다."""
    have = {s.keyword for s in list_keyword_stats(session, workspace_id, content_id)}
    session.add_all(
        ContentKeywordStat(workspace_id=workspace_id, content_id=content_id, keyword=s.keyword,
                           mentions=s.mentions, density=s.density, title_has=s.title_has, relevance=rel)
        for s, rel in stats if s.keyword not in have
    )
    session.flush()
    _refresh_relevance(session, workspace_id, content_id)


def _refresh_relevance(session: Session, workspace_id: uuid.UUID, content_id: int) -> None:
    row = get_analysis(session, workspace_id, content_id)
    if row is None:
        return
    row.relevance = best_relevance([s.relevance for s in list_keyword_stats(session, workspace_id, content_id)])
    session.add(row)
    session.flush()


def clear_analysis(session: Session, workspace_id: uuid.UUID, content_ids: list[int]) -> None:
    """분석 결과를 지운다 (정제 본문이 바뀌어 다시 분석해야 할 때). 콘텐츠는 그대로다."""
    for part in _chunks(content_ids):
        for model in (ContentTerm, ContentKeywordStat, ContentAnalysis):
            session.execute(delete(model).where(model.workspace_id == workspace_id, col(model.content_id).in_(part)))
    session.flush()


# ── 조회 ──────────────────────────────────────────────────

def get_analysis(session: Session, workspace_id: uuid.UUID, content_id: int) -> ContentAnalysis | None:
    stmt = scoped_select(ContentAnalysis, workspace_id).where(ContentAnalysis.content_id == content_id)
    return session.exec(stmt).first()


def list_terms(session: Session, workspace_id: uuid.UUID, content_id: int) -> list[ContentTerm]:
    stmt = scoped_select(ContentTerm, workspace_id).where(ContentTerm.content_id == content_id)
    return list(session.exec(stmt.order_by(col(ContentTerm.count).desc(), col(ContentTerm.term))))


def list_keyword_stats(session: Session, workspace_id: uuid.UUID, content_id: int) -> list[ContentKeywordStat]:
    stmt = scoped_select(ContentKeywordStat, workspace_id).where(ContentKeywordStat.content_id == content_id)
    return list(session.exec(stmt.order_by(col(ContentKeywordStat.id))))


def relevance_for(session: Session, workspace_id: uuid.UUID, content_ids: list[int]) -> dict[int, Relevance | None]:
    """콘텐츠별 관련도 (목록 한 페이지분). 분석 전이거나 키워드 수집분이 아니면 None."""
    found: dict[int, Relevance | None] = {cid: None for cid in content_ids}
    for part in _chunks(content_ids):
        stmt = scoped_select(ContentAnalysis, workspace_id).where(col(ContentAnalysis.content_id).in_(part))
        for a in session.exec(stmt):
            found[a.content_id] = a.relevance
    return found
