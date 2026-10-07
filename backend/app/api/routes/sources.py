"""수집 소스 조회. 모든 라우트가 get_current_workspace 를 거친다.

지금은 필터 선택지만 있다. 소스 목록·추가·편집(SOURCE-001~005)은 아직 목업이다.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_workspace, get_session
from app.db.models import Workspace
from app.repositories import sources as repo
from app.schemas.sources import SourceOption

router = APIRouter(prefix="/sources", tags=["수집 소스"])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/options", response_model=list[SourceOption])
def source_options(ws: WorkspaceDep, session: SessionDep):
    """워크스페이스의 소스 이름 (id 순). 사용하지 않는 소스도 넣는다 — 그 소스로 모은 콘텐츠가 남아 있다."""
    return [SourceOption.of(s) for s in repo.list_sources(session, ws.id)]
