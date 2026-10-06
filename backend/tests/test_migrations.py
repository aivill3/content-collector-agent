"""alembic 마이그레이션 — 임시 SQLite 에 upgrade/downgrade 를 실제로 돌린다."""
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlmodel import SQLModel

import app.db.models  # noqa: F401
from app.core.config import BASE_DIR
from app.db.engine import make_engine

TABLES = {"workspaces", "sources", "source_keywords", "collection_jobs",
          "job_api_responses", "contents", "content_keyword_hits"}


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'migrate.db').as_posix()}"


def _config(url: str) -> Config:
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False   # pytest 의 로그 설정을 덮어쓰지 않는다
    return cfg


def _tables(url: str) -> set[str]:
    engine = make_engine(url)
    try:
        return set(sa.inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_and_downgrade(db_url):
    cfg = _config(db_url)
    command.upgrade(cfg, "head")
    assert _tables(db_url) == TABLES
    command.downgrade(cfg, "base")
    assert _tables(db_url) == set()
    command.upgrade(cfg, "head")                  # 되돌린 뒤 다시 올려도 된다
    assert _tables(db_url) == TABLES


def test_migrations_match_models(db_url):
    """모델을 바꾸고 마이그레이션을 빠뜨리면 여기서 걸린다."""
    command.upgrade(_config(db_url), "head")
    engine = make_engine(db_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), SQLModel.metadata)
    engine.dispose()
    assert diff == []
