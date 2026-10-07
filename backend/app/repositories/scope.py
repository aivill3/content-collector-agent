"""워크스페이스 범위 조회 — 모든 repository 함수가 이 두 함수를 거친다.

workspace_id 필터를 호출하는 쪽이 매번 붙이게 두면 언젠가 빠뜨린다. 여기서만 select 를
만들고, WorkspaceScoped 가 아닌 모델은 받지 않는다.

id 로 한 건을 찾을 때 다른 워크스페이스의 행이면 '없음'(None)으로 돌려준다.
라우트는 None 을 404 로 바꾼다 — 403 을 쓰면 그 id 가 존재한다는 사실이 드러난다.
"""
import uuid
from typing import TypeVar

from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.db.models import WorkspaceScoped

M = TypeVar("M", bound=WorkspaceScoped)


def scoped_select(model: type[M], workspace_id: uuid.UUID) -> SelectOfScalar[M]:
    """workspace_id 필터가 걸린 select. 여기에 .where()·.order_by() 를 이어 붙인다."""
    if not (isinstance(model, type) and issubclass(model, WorkspaceScoped) and hasattr(model, "__table__")):
        raise TypeError(f"{model!r} 는 워크스페이스에 속하는 테이블이 아닙니다")
    if not isinstance(workspace_id, uuid.UUID):
        raise TypeError("workspace_id 가 필요합니다")
    return select(model).where(model.workspace_id == workspace_id)


def get_scoped(session: Session, model: type[M], workspace_id: uuid.UUID, id: int) -> M | None:
    """id 로 한 건. 없거나 다른 워크스페이스 것이면 None."""
    return session.exec(scoped_select(model, workspace_id).where(model.id == id)).first()
