"""DB 테스트 공통 fixture — 테스트마다 임시 SQLite 파일을 새로 만든다."""
import pytest
from sqlmodel import Session, SQLModel

from app.db.engine import make_engine
from app.domain.enums import WorkspaceType
from app.repositories.workspaces import create_workspace


@pytest.fixture
def session(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture
def ws_a(session):
    return create_workspace(session, name="A", type=WorkspaceType.COMPANY).id


@pytest.fixture
def ws_b(session):
    return create_workspace(session, name="B", type=WorkspaceType.PERSONAL).id
