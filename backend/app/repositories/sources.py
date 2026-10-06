"""수집 소스와 뉴스 키워드. 모든 함수가 workspace_id 를 받는다 (scope.py).

커밋은 호출하는 쪽(라우트·워커)이 한다. 여기서는 flush 까지만 한다.
"""
import re
import uuid
from collections.abc import Iterable

from sqlmodel import Session, col

from app.db.models import Source, SourceKeyword
from app.db.types import utcnow
from app.domain.enums import KeywordOrigin, ScheduleType, SourceType
from app.repositories.scope import get_scoped, scoped_select
from app.schemas.source_config import DEFAULT_MIN_BODY_LENGTH, SourceConfig, validate_config

_RE_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# update_source 로 바꿀 수 있는 컬럼. type·workspace_id·실행 기록은 바꾸지 않는다.
_EDITABLE = {"name", "is_active", "schedule_type", "schedule_time", "cron_expr",
             "min_body_length", "allow_non_korean", "config"}


def normalize_keyword(keyword: str) -> str:
    """앞뒤 공백 제거·연속 공백을 하나로. ' 태권도   대회 ' → '태권도 대회'"""
    return " ".join((keyword or "").split())


def _check_schedule(schedule_time: str | None) -> None:
    if schedule_time is not None and not _RE_HHMM.match(schedule_time):
        raise ValueError(f"schedule_time 은 HH:MM 형식입니다 (DISPLAY_TZ 기준): {schedule_time}")


def create_source(
    session: Session,
    workspace_id: uuid.UUID,
    *,
    name: str,
    type: SourceType,
    config: dict | SourceConfig,
    keywords: Iterable[str] = (),
    schedule_type: ScheduleType = ScheduleType.MANUAL,
    schedule_time: str | None = None,
    cron_expr: str | None = None,
    min_body_length: int | None = None,
    allow_non_korean: bool = False,
    is_active: bool = True,
) -> Source:
    """소스를 만든다. config 는 유형별 모델로 검증한 뒤 저장한다.

    min_body_length 를 비우면 유형별 기본값(뉴스 100, 게시판·URL 30)을 쓴다.
    """
    type = SourceType(type)
    cfg = validate_config(type, config)
    _check_schedule(schedule_time)
    source = Source(
        workspace_id=workspace_id,
        name=name.strip(),
        type=type,
        config=cfg.model_dump(),
        schedule_type=ScheduleType(schedule_type),
        schedule_time=schedule_time,
        cron_expr=cron_expr or None,
        min_body_length=DEFAULT_MIN_BODY_LENGTH[type] if min_body_length is None else min_body_length,
        allow_non_korean=allow_non_korean,
        is_active=is_active,
    )
    session.add(source)
    session.flush()
    if keywords:
        add_keywords(session, workspace_id, source.id, keywords)
    return source


def get_source(session: Session, workspace_id: uuid.UUID, source_id: int) -> Source | None:
    return get_scoped(session, Source, workspace_id, source_id)


def list_sources(session: Session, workspace_id: uuid.UUID, *, active_only: bool = False) -> list[Source]:
    stmt = scoped_select(Source, workspace_id).order_by(col(Source.id))
    if active_only:
        stmt = stmt.where(col(Source.is_active).is_(True))
    return list(session.exec(stmt))


def update_source(session: Session, workspace_id: uuid.UUID, source_id: int, **changes) -> Source | None:
    """설정 일부를 바꾼다. 다른 워크스페이스 소스면 None. config 는 다시 검증한다."""
    unknown = set(changes) - _EDITABLE
    if unknown:
        raise ValueError(f"바꿀 수 없는 항목: {', '.join(sorted(unknown))}")
    source = get_source(session, workspace_id, source_id)
    if source is None:
        return None
    if "config" in changes:
        changes["config"] = validate_config(source.type, changes["config"]).model_dump()
    if "schedule_time" in changes:
        _check_schedule(changes["schedule_time"])
    for key, value in changes.items():
        setattr(source, key, value)
    source.updated_at = utcnow()
    session.add(source)
    session.flush()
    return source


def source_config(source: Source) -> SourceConfig:
    """저장된 config 를 유형별 모델로 읽는다."""
    return validate_config(source.type, source.config)


# ── 뉴스 키워드 ─────────────────────────────────────────

def list_keywords(session: Session, workspace_id: uuid.UUID, source_id: int) -> list[SourceKeyword]:
    stmt = scoped_select(SourceKeyword, workspace_id).where(SourceKeyword.source_id == source_id)
    return list(session.exec(stmt.order_by(col(SourceKeyword.id))))


def add_keywords(
    session: Session,
    workspace_id: uuid.UUID,
    source_id: int,
    keywords: Iterable[str],
    *,
    origin: KeywordOrigin = KeywordOrigin.MANUAL,
) -> list[SourceKeyword]:
    """검색어를 더한다. 공백을 정리하고, 이미 있는 검색어·빈 값은 건너뛴다. 새로 만든 것만 돌려준다."""
    source = get_source(session, workspace_id, source_id)
    if source is None:
        raise LookupError(f"소스 {source_id} 가 없습니다")
    if source.type != SourceType.NEWS_KEYWORD:
        raise ValueError("검색어는 뉴스 키워드 소스에만 넣을 수 있습니다")
    have = {k.keyword for k in list_keywords(session, workspace_id, source_id)}
    added = []
    for kw in dict.fromkeys(normalize_keyword(k) for k in keywords):
        if kw and kw not in have:
            added.append(SourceKeyword(workspace_id=workspace_id, source_id=source_id, keyword=kw, origin=origin))
    session.add_all(added)
    session.flush()
    return added


def remove_keyword(session: Session, workspace_id: uuid.UUID, source_id: int, keyword: str) -> bool:
    """검색어를 뺀다. 이 검색어로 찾은 기록(content_keyword_hits)은 keyword 문자열로 남는다."""
    stmt = scoped_select(SourceKeyword, workspace_id).where(
        SourceKeyword.source_id == source_id, SourceKeyword.keyword == normalize_keyword(keyword))
    row = session.exec(stmt).first()
    if row is None:
        return False
    session.delete(row)
    session.flush()
    return True
