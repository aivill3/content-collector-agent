"""콘텐츠 조회 (CONTENT-001·002). 모든 라우트가 get_current_workspace 를 거친다.

라우트는 repositories/ 의 함수만 부르고 결과를 schemas/contents.py 로 옮겨 담는다.
재분석(POST /{id}/reanalyze)은 workers/analysis 를 부르고 커밋한다.
"""
import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.deps import get_current_workspace, get_session, not_found
from app.core.timeutil import recent_days
from app.db.models import Content, Workspace
from app.repositories import analyses
from app.repositories import contents as repo
from app.schemas.analysis import AnalysisSettingsOut, ContentAnalysisOut
from app.schemas.contents import ContentDetail, ContentListItem, ContentListParams, ContentListResult
from app.services import analysis_service
from app.workers import analysis as analysis_worker

router = APIRouter(prefix="/contents", tags=["콘텐츠"])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=ContentListResult)
def list_contents(params: Annotated[ContentListParams, Query()], ws: WorkspaceDep, session: SessionDep):
    first, last = recent_days(params.days) if params.days else (params.from_, params.to)
    settings = analyses.get_settings(session, ws.id)
    query = repo.ContentQuery(
        source_id=params.source_id, collection_path=params.collection_path,
        first=first, last=last, date_field=params.date_field,
        q=params.q, sort=params.sort, descending=params.order == "desc",
        relevance=params.relevance, hide_passing=settings.passing_mode == "hide",
    )
    rows, total = repo.search_contents(session, ws.id, query, page=params.page, size=params.size)
    ids = [c.id for c in rows]
    keywords = repo.keywords_for(session, ws.id, ids)
    excerpts = repo.excerpts_for(session, ws.id, ids)
    relevance = analyses.relevance_for(session, ws.id, ids)
    names = repo.source_names(session, ws.id, (c.source_id for c in rows))
    return ContentListResult(
        items=[ContentListItem.of(c, source_name=names.get(c.source_id, ""), keywords=keywords[c.id],
                                  excerpt=excerpts[c.id], relevance=relevance[c.id]) for c in rows],
        total=total, page=params.page, size=params.size, page_count=math.ceil(total / params.size),
        passing_mode=settings.passing_mode,
    )


@router.get("/{content_id}", response_model=ContentDetail)
def get_content(content_id: int, ws: WorkspaceDep, session: SessionDep):
    c = repo.get_content(session, ws.id, content_id)
    if c is None:                     # 다른 워크스페이스의 id 도 같은 404
        raise not_found("콘텐츠")
    return _detail(session, ws, c)


@router.post("/{content_id}/reanalyze", response_model=ContentDetail)
def reanalyze_content(content_id: int, ws: WorkspaceDep, session: SessionDep):
    """글 하나를 지금 분석 설정으로 다시 분석한다 (FN-CNT-007)."""
    if not analysis_worker.analyze_content(session, ws.id, content_id):
        raise not_found("콘텐츠")
    session.commit()
    return _detail(session, ws, repo.get_content(session, ws.id, content_id))


def _detail(session: Session, ws: Workspace, c: Content) -> ContentDetail:
    names = repo.source_names(session, ws.id, [c.source_id])
    settings = analyses.get_settings(session, ws.id, c.source_id)
    a = analyses.get_analysis(session, ws.id, c.id)
    analysis = None
    if a is not None:
        terms = [analysis_service.Term(t.term, t.pos, t.count) for t in analyses.list_terms(session, ws.id, c.id)]
        analysis = ContentAnalysisOut.of(a, top_words=analysis_service.top_words(terms, settings),
                                         stats=analyses.list_keyword_stats(session, ws.id, c.id))
    return ContentDetail.of_detail(c, source_name=names.get(c.source_id, ""),
                                   hits=repo.list_hits(session, ws.id, c.id),
                                   analysis=analysis, settings=AnalysisSettingsOut.of(settings))
