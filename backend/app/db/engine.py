"""DB 엔진과 세션. DATABASE_URL(core/config.py)만 바꾸면 SQLite ↔ PostgreSQL 이 바뀐다.

테이블은 create_all 이 아니라 alembic 으로 만든다 (backend/ 에서 alembic upgrade head).
"""
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.core.config import DATABASE_URL


def make_engine(url: str = DATABASE_URL) -> Engine:
    if url.startswith("sqlite"):
        if ":memory:" not in url and url.startswith("sqlite:///"):
            # backend/data/ 가 없으면 SQLite 가 파일을 만들지 못한다
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        # FastAPI 는 동기 라우트를 스레드풀에서 돌린다 — 세션은 요청마다 새로 만든다
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            # SQLite 는 기본으로 외래 키를 검사하지 않는다 (ON DELETE 도 동작하지 않는다)
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    return create_engine(url, pool_pre_ping=True)


engine = make_engine()


def get_session() -> Iterator[Session]:
    """요청(작업) 하나에 세션 하나. 커밋은 호출하는 쪽이 한다."""
    with Session(engine) as session:
        yield session
