"""API 공통 의존성. DB 를 쓰는 라우트는 모두 이 둘을 거친다.

    @router.get("/sources")
    def list_(ws: Workspace = Depends(get_current_workspace), session: Session = Depends(get_session)):
        return sources.list_sources(session, ws.id)

Phase 1 에는 인증이 없어 get_current_workspace 가 기본 워크스페이스를 돌려준다.
인증을 붙일 때 이 함수만 '토큰의 유저 → 소속 워크스페이스' 로 바꾸면 된다.
repository 가 None(없음 또는 다른 워크스페이스)을 돌려주면 라우트는 not_found() 로 404 를 낸다.
"""
from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.db.engine import get_session
from app.db.models import Workspace
from app.repositories.workspaces import DEFAULT_WORKSPACE_ID, get_workspace

__all__ = ["get_session", "get_current_workspace", "not_found"]


def get_current_workspace(session: Session = Depends(get_session)) -> Workspace:
    ws = get_workspace(session, DEFAULT_WORKSPACE_ID)
    if ws is None:
        # 서버 설정 문제다. backend/ 에서 alembic upgrade head → python -m app.db.seed
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "기본 워크스페이스가 없습니다 (seed 실행 필요)")
    return ws


def not_found(what: str = "대상") -> HTTPException:
    """다른 워크스페이스의 id 도 똑같이 '없음'으로 답한다 (존재 여부를 드러내지 않는다)."""
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what}을(를) 찾을 수 없습니다")
