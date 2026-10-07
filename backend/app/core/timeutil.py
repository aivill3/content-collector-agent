"""시간대 변환 — DB(UTC) ↔ 표시 시간대(DISPLAY_TZ). 오프셋을 코드에 적지 않고 여기만 거친다.

    to_display_iso(dt)          UTC → '2026-09-30T14:20:00+09:00' (API 응답)
    display_today()             표시 시간대 기준 오늘 날짜
    recent_days(n)              오늘을 포함한 최근 n일 (첫날, 마지막 날)
    days_to_utc_range(a, b)     표시 시간대 날짜 구간 → UTC [시작, 끝) — WHERE 조건용
    display_date(dt)            UTC 시각 → 표시 시간대 날짜 — 날짜별 묶기용
    schedule_at(day, "HH:MM")   소스 schedule_time → 그날의 실행 시각(UTC)

기간 필터는 날짜 경계를 UTC 로 바꿔 DB 에 넘기고, 날짜별 묶기는 가져온 UTC 시각을 표시 시간대로
바꾼 뒤 파이썬에서 한다. SQLite·PostgreSQL 의 시간대 함수(AT TIME ZONE 등)는 쓰지 않는다.

모든 함수가 tz 인자를 받는다 (기본 DISPLAY_TZ). 테스트와 나중의 워크스페이스별 시간대를 위해서다.
"""
from datetime import date, datetime, time, timedelta, timezone, tzinfo

from app.core.config import DISPLAY_TZ


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("시간대가 없는 datetime 은 변환하지 않습니다")
    return dt


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_display(dt: datetime, tz: tzinfo = DISPLAY_TZ) -> datetime:
    return _aware(dt).astimezone(tz)


def to_display_iso(dt: datetime | None, tz: tzinfo = DISPLAY_TZ) -> str | None:
    """API 응답용. 오프셋이 붙은 ISO 8601, 초 단위까지. None 은 None."""
    return None if dt is None else to_display(dt, tz).replace(microsecond=0).isoformat()


def display_date(dt: datetime, tz: tzinfo = DISPLAY_TZ) -> date:
    """이 시각이 표시 시간대로 며칠인가. UTC 날짜와 다를 수 있다 (KST 00:00~08:59 는 UTC 로 전날)."""
    return to_display(dt, tz).date()


def display_today(now: datetime | None = None, tz: tzinfo = DISPLAY_TZ) -> date:
    return display_date(now or utcnow(), tz)


def recent_days(n: int, now: datetime | None = None, tz: tzinfo = DISPLAY_TZ) -> tuple[date, date]:
    """오늘을 포함한 최근 n일. n=1 이면 오늘 하루, n=7 이면 6일 전 ~ 오늘."""
    if n < 1:
        raise ValueError("n 은 1 이상입니다")
    today = display_today(now, tz)
    return today - timedelta(days=n - 1), today


def day_start_utc(day: date, tz: tzinfo = DISPLAY_TZ) -> datetime:
    """표시 시간대 그날 00:00 을 UTC 로."""
    return datetime.combine(day, time(0), tzinfo=tz).astimezone(timezone.utc)


def days_to_utc_range(first: date, last: date, tz: tzinfo = DISPLAY_TZ) -> tuple[datetime, datetime]:
    """표시 시간대 날짜 first~last(양끝 포함) → UTC [start, end). WHERE col >= start AND col < end."""
    if last < first:
        raise ValueError("마지막 날이 첫날보다 앞섭니다")
    return day_start_utc(first, tz), day_start_utc(last + timedelta(days=1), tz)


def schedule_at(day: date, hhmm: str, tz: tzinfo = DISPLAY_TZ) -> datetime:
    """소스 schedule_time('HH:MM', 표시 시간대 기준) → 그날 실행 시각(UTC)."""
    hour, minute = (int(x) for x in hhmm.split(":"))
    return datetime.combine(day, time(hour, minute), tzinfo=tz).astimezone(timezone.utc)


def next_daily_run(hhmm: str, after: datetime, tz: tzinfo = DISPLAY_TZ) -> datetime:
    """after 이후 처음 오는 'HH:MM'(표시 시간대) 실행 시각(UTC). 매일 실행 소스의 next_run_at 계산용."""
    day = display_date(after, tz)
    run = schedule_at(day, hhmm, tz)
    return run if run > _aware(after) else schedule_at(day + timedelta(days=1), hhmm, tz)
