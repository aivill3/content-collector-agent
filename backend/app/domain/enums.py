"""앱 전체가 쓰는 선택지 값.

DB 에는 네이티브 ENUM 이 아니라 문자열 컬럼으로 저장한다 (SQLite·PostgreSQL 공통).
값을 추가할 때는 마이그레이션이 필요 없지만, 이름을 바꾸거나 지울 때는 기존 행을
옮기는 마이그레이션을 함께 만든다.
"""
from enum import StrEnum


class WorkspaceType(StrEnum):
    PERSONAL = "personal"   # 가입 시 자동 생성되는 1인 워크스페이스
    COMPANY = "company"     # 멤버들이 함께 쓰는 워크스페이스


class SourceType(StrEnum):
    NEWS_KEYWORD = "news_keyword"
    BOARD = "board"
    URL = "url"


class ScheduleType(StrEnum):
    MANUAL = "manual"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CRON = "cron"


class JobTrigger(StrEnum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class KeywordOrigin(StrEnum):
    MANUAL = "manual"               # 유저가 직접 입력
    RELATED_WORD = "related_word"   # 연관어 추천에서 추가


class CollectionPath(StrEnum):
    """콘텐츠를 가져온 경로. Article.source 값과 같다."""
    NAVER = "naver"
    BOARD = "board"
    WEBSITE = "website"
