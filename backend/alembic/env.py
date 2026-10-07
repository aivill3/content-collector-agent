"""Alembic 실행 환경.

DB 주소는 DATABASE_URL(app/core/config.py)을 쓴다. 테스트처럼 다른 DB 에 적용할 때는
Config.set_main_option("sqlalchemy.url", ...) 로 넘긴 값이 우선한다.

SQLite 는 ALTER TABLE 이 제한적이라 render_as_batch 로 테이블을 새로 만들어 옮긴다.
"""
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from sqlmodel import SQLModel
from sqlmodel.sql.sqltypes import AutoString

import app.db.models  # noqa: F401  (테이블을 SQLModel.metadata 에 등록)
from app.core.config import DATABASE_URL
from app.db.engine import make_engine
from app.db.types import UTCDateTime

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata


def render_item(type_, obj, autogen_context):
    """마이그레이션 파일이 앱 코드(app.db.types 등)를 import 하지 않도록 범용 타입으로 적는다.

    마이그레이션은 과거 시점의 스키마다. 앱 코드가 바뀌어도 그대로 돌아야 한다.
    """
    if type_ != "type":
        return False
    if isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    if isinstance(obj, sa.Enum) and not obj.native_enum:
        return f"sa.String(length={obj.length})"
    if isinstance(obj, AutoString):
        return f"sa.String(length={obj.length})" if obj.length else "sa.String()"
    return False


def _options() -> dict:
    return dict(target_metadata=target_metadata, render_as_batch=True, render_item=render_item, compare_type=True)


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"}, **_options())
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, **_options())
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
