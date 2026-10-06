"""워크스페이스.

Phase 1 에는 유저·인증이 없어 기본 워크스페이스 하나에 모든 데이터를 넣는다.
seed(app/db/seed.py)와 API 의존성(app/api/deps.get_current_workspace)이 같은 id 를 쓴다.
"""
import uuid

from sqlmodel import Session

from app.db.models import Workspace
from app.domain.enums import WorkspaceType

# 고정 값이다. 바꾸면 이미 저장된 데이터가 기본 워크스페이스에서 사라진 것처럼 보인다.
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_WORKSPACE_NAME = "기본 워크스페이스"


def get_workspace(session: Session, workspace_id: uuid.UUID) -> Workspace | None:
    return session.get(Workspace, workspace_id)


def create_workspace(
    session: Session,
    *,
    name: str,
    type: WorkspaceType,
    plan: str = "free",
    id: uuid.UUID | None = None,
) -> Workspace:
    ws = Workspace(name=name, type=type, plan=plan, **({"id": id} if id else {}))
    session.add(ws)
    session.flush()
    return ws


def ensure_default_workspace(session: Session) -> Workspace:
    """기본 워크스페이스가 없으면 만든다. 여러 번 불러도 하나만 생긴다."""
    return get_workspace(session, DEFAULT_WORKSPACE_ID) or create_workspace(
        session, id=DEFAULT_WORKSPACE_ID, name=DEFAULT_WORKSPACE_NAME, type=WorkspaceType.PERSONAL,
    )
