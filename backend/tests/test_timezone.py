"""시간대 규칙 — DB 는 UTC, 표시·집계·일정은 DISPLAY_TZ(기본 Asia/Seoul). 네트워크 없음."""
import subprocess
import sys
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlmodel import select

from app.core.config import BASE_DIR
from app.core.timeutil import (
    days_to_utc_range,
    display_date,
    display_today,
    next_daily_run,
    recent_days,
    schedule_at,
    to_display_iso,
)
from app.db.models import Content
from app.repositories import contents
from app.schemas.base import CamelModel, DisplayDateTime, display_iso
from app.services.collection_service import CollectResult
from tests.test_db import article, news_source, run

UTC = timezone.utc
SEOUL = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 9, 30, 3, 0, tzinfo=UTC)          # KST 2026-09-30 12:00


def utc(y, mo, d, h, mi=0, s=0) -> datetime:
    return datetime(y, mo, d, h, mi, s, tzinfo=UTC)


def seed_contents(session, ws, collected: dict[str, datetime]) -> None:
    """URL 끝자리 → collected_at 을 가진 콘텐츠를 만든다."""
    src = news_source(session, ws)
    urls = {key: f"https://news.example.com/{key}" for key in collected}
    run(session, ws, src.id, CollectResult(articles=[article(url=u) for u in urls.values()]))
    for c in session.exec(select(Content)):
        c.collected_at = collected[c.url.rsplit("/", 1)[1]]
        session.add(c)
    session.commit()


def test_kst_early_morning_is_counted_in_kst_today(session, ws_a):
    # UTC 로는 9월 29일이지만 KST 로는 9월 30일인 시각들
    seed_contents(session, ws_a, {
        "kst_0000": utc(2026, 9, 29, 15, 0),        # KST 09-30 00:00
        "kst_0859": utc(2026, 9, 29, 23, 59, 59),   # KST 09-30 08:59:59
        "kst_2359": utc(2026, 9, 30, 14, 59, 59),   # KST 09-30 23:59:59
        "kst_prev": utc(2026, 9, 29, 14, 59, 59),   # KST 09-29 23:59:59 → 어제
        "kst_next": utc(2026, 9, 30, 15, 0),        # KST 10-01 00:00   → 내일
    })
    today = display_today(NOW)
    assert today == date(2026, 9, 30)

    assert contents.count_contents_on(session, ws_a, today) == 3
    assert contents.count_contents_by_day(session, ws_a, *recent_days(2, NOW)) == {
        date(2026, 9, 29): 1, date(2026, 9, 30): 3}
    got = {c.url.rsplit("/", 1)[1] for c in contents.list_contents(session, ws_a, days=(today, today))}
    assert got == {"kst_0000", "kst_0859", "kst_2359"}
    # 같은 데이터를 UTC 날짜로 셌다면 틀렸을 것이다 (KST 00:00~08:59 가 전날로 빠진다)
    assert contents.count_contents_on(session, ws_a, today, tz=UTC) == 2


def test_published_at_basis_skips_unknown(session, ws_a):
    src = news_source(session, ws_a)
    known = article(url="https://news.example.com/known")
    known.published = "2026-09-30T08:30:00+09:00"            # UTC 로는 09-29 23:30
    unknown = article(url="https://news.example.com/unknown")
    unknown.published = ""
    run(session, ws_a, src.id, CollectResult(articles=[known, unknown]))
    counts = contents.count_contents_by_day(session, ws_a, date(2026, 9, 29), date(2026, 9, 30), by="published_at")
    assert counts == {date(2026, 9, 29): 0, date(2026, 9, 30): 1}


def test_date_range_and_grouping_helpers():
    assert recent_days(7, NOW) == (date(2026, 9, 24), date(2026, 9, 30))
    assert days_to_utc_range(date(2026, 9, 30), date(2026, 9, 30)) == (utc(2026, 9, 29, 15), utc(2026, 9, 30, 15))
    assert display_date(utc(2026, 9, 29, 15)) == date(2026, 9, 30)
    # 시간대를 바꾸면 경계도 바뀐다 — 오프셋이 코드에 박혀 있지 않다
    assert days_to_utc_range(date(2026, 9, 30), date(2026, 9, 30), ZoneInfo("America/New_York"))[0] == utc(2026, 9, 30, 4)


def test_api_datetime_is_display_tz_iso():
    assert to_display_iso(utc(2026, 9, 30, 5, 20)) == "2026-09-30T14:20:00+09:00"
    assert to_display_iso(None) is None

    class Out(CamelModel):
        collected_at: DisplayDateTime
        finished_at: DisplayDateTime | None = None

    body = Out(collected_at=utc(2026, 9, 30, 5, 20)).model_dump(mode="json", by_alias=True)
    assert body == {"collectedAt": "2026-09-30T14:20:00+09:00", "finishedAt": None}
    # 수집기가 채운 날짜 문자열도 같은 형식으로
    assert display_iso("2026-09-25") == "2026-09-25T00:00:00+09:00"
    assert display_iso("Fri, 25 Sep 2026 09:07:13 +0900") == ""   # 못 읽은 원본은 빈 값
    assert display_iso("") == ""


def test_schedule_time_is_display_tz():
    assert schedule_at(date(2026, 9, 30), "09:00") == utc(2026, 9, 30, 0)
    assert schedule_at(date(2026, 9, 30), "06:00") == utc(2026, 9, 29, 21)   # UTC 로는 전날
    # KST 12:00 기준 다음 09:00 은 내일, 다음 18:00 은 오늘
    assert next_daily_run("09:00", NOW) == utc(2026, 10, 1, 0)
    assert next_daily_run("18:00", NOW) == utc(2026, 9, 30, 9)


def _run_with_env(code: str, **env) -> subprocess.CompletedProcess:
    import os
    return subprocess.run([sys.executable, "-c", code], cwd=BASE_DIR, capture_output=True, encoding="utf-8",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8", **env})


def test_display_tz_setting():
    code = ("from datetime import datetime, timezone; from app.core.timeutil import to_display_iso; "
            "print(to_display_iso(datetime(2026, 9, 30, 5, 20, tzinfo=timezone.utc)))")
    assert _run_with_env(code, DISPLAY_TZ="UTC").stdout.strip() == "2026-09-30T05:20:00+00:00"
    bad = _run_with_env("import app.core.config", DISPLAY_TZ="Mars/Base")
    assert bad.returncode != 0 and "RuntimeError" in bad.stderr


def test_no_hardcoded_kst_offset():
    """오프셋 하드코딩 금지 — 시간대는 ZoneInfo 이름으로만."""
    offenders = [str(p.relative_to(BASE_DIR)) for p in (BASE_DIR / "app").rglob("*.py")
                 if "hours=9" in p.read_text(encoding="utf-8")]
    assert offenders == []
