"""콘텐츠 조회 (CONTENT-001·002). 모든 라우트가 get_current_workspace 를 거친다.

라우트는 repositories/ 의 함수만 부르고 결과를 schemas/contents.py 로 옮겨 담는다.
"""
import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.deps import get_current_workspace, get_session, not_found
from app.core.timeutil import recent_days
from app.db.models import Workspace
from app.repositories import contents as repo
from app.schemas.contents import ContentDetail, ContentListItem, ContentListParams, ContentListResult

router = APIRouter(prefix="/contents", tags=["콘텐츠"])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=ContentListResult)
def list_contents(params: Annotated[ContentListParams, Query()], ws: WorkspaceDep, session: SessionDep):
    first, last = recent_days(params.days) if params.days else (params.from_, params.to)
    query = repo.ContentQuery(
        source_id=params.source_id, collection_path=params.collection_path,
        first=first, last=last, date_field=params.date_field,
        q=params.q, sort=params.sort, descending=params.order == "desc",
    )
    rows, total = repo.search_contents(session, ws.id, query, page=params.page, size=params.size)
    ids = [c.id for c in rows]
    keywords = repo.keywords_for(session, ws.id, ids)
    excerpts = repo.excerpts_for(session, ws.id, ids)
    names = repo.source_names(session, ws.id, (c.source_id for c in rows))
    return ContentListResult(
        items=[ContentListItem.of(c, source_name=names.get(c.source_id, ""), keywords=keywords[c.id],
                                  excerpt=excerpts[c.id]) for c in rows],
        total=total, page=params.page, size=params.size, page_count=math.ceil(total / params.size),
    )


@router.get("/{content_id}", response_model=ContentDetail)
def get_content(content_id: int, ws: WorkspaceDep, session: SessionDep):
    c = repo.get_content(session, ws.id, content_id)
    if c is None:                     # 다른 워크스페이스의 id 도 같은 404
        raise not_found("콘텐츠")
    names = repo.source_names(session, ws.id, [c.source_id])
    return ContentDetail.of_detail(c, source_name=names.get(c.source_id, ""),
                                   hits=repo.list_hits(session, ws.id, c.id))
