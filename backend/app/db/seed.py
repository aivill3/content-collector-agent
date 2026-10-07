"""기본 데이터 넣기. 마이그레이션 뒤에 한 번 실행한다 (여러 번 실행해도 안전하다).

    alembic upgrade head
    python -m app.db.seed
"""
from sqlmodel import Session

from app.core import logger
from app.db.engine import engine
from app.repositories.workspaces import ensure_default_workspace

log = logger.get_logger(__name__)


def seed(session: Session) -> None:
    ws = ensure_default_workspace(session)
    session.commit()
    log.info(f"기본 워크스페이스: {ws.name} ({ws.id})")


if __name__ == "__main__":
    logger.setup()
    with Session(engine) as s:
        seed(s)
