"""소스 유형별 설정(sources.config) — 저장하기 전에 여기서 검증한다.

DB 에는 snake_case 로 저장한다 (model_dump()). API 로 주고받을 때는 CamelModel 이
camelCase 로 바꾼다.

    news_keyword  NewsKeywordConfig   키워드 자체는 source_keywords 테이블에 둔다
    board         BoardSourceConfig   collectors/board.BoardConfig 필드 + 조회 기간
    url           UrlSourceConfig     글 URL 목록
"""
import re
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from app.collectors.board import BoardConfig
from app.collectors.news import START_MAX
from app.domain.enums import SourceType
from app.extractors.cleaner import MIN_CLEAN_LEN
from app.schemas.base import CamelModel

# 소스 유형별 최소 본문 길이 기본값 — collection_service 의 기본값과 같다.
# 게시판 공지·짧은 글도 수집 대상이라 뉴스보다 낮다.
DEFAULT_MIN_BODY_LENGTH = {
    SourceType.NEWS_KEYWORD: MIN_CLEAN_LEN,
    SourceType.BOARD: 30,
    SourceType.URL: 30,
}


def _http_url(url: str) -> str:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"http(s) 주소가 아닙니다: {url}")
    return url


class _Config(CamelModel):
    # 오타 난 키가 조용히 버려지지 않게 한다
    model_config = ConfigDict(extra="forbid")


class NewsKeywordConfig(_Config):
    count: int = Field(30, ge=1, le=START_MAX)        # 키워드당 검색 건수
    sort: Literal["sim", "date"] = "sim"              # sim=관련도순, date=최신순
    days: int | None = Field(3, ge=1)                 # 최근 N일 발행분. None = 제한 없음


class BoardSourceConfig(_Config):
    """BoardConfig 와 필드 이름·기본값이 같다. 필드를 더하면 양쪽을 함께 고친다."""
    list_url: str
    item_selector: str = ""
    link_selector: str = "a[href]"
    title_selector: str = ""
    date_selector: str = ""
    body_selector: str = ""
    page_param: str = ""
    start_page: int = Field(1, ge=1)
    max_pages: int = Field(1, ge=1)
    max_items: int = Field(50, ge=1)
    include_pattern: str = ""
    exclude_notice: bool = False
    list_pattern: str = ""                            # 자동 탐지에서 채택한 후보 묶음
    days: int | None = Field(None, ge=1)              # collect_board(days=) — BoardConfig 밖의 값

    @field_validator("list_url")
    @classmethod
    def _url(cls, v: str) -> str:
        return _http_url(v)

    @field_validator("include_pattern")
    @classmethod
    def _regex(cls, v: str) -> str:
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"포함 URL 패턴이 정규식이 아닙니다: {e}") from e
        return v

    def to_board_config(self) -> BoardConfig:
        return BoardConfig(**self.model_dump(exclude={"days"}))


class UrlSourceConfig(_Config):
    urls: list[str] = Field(min_length=1)

    @field_validator("urls")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        # 빈 줄은 빼고, 같은 주소는 한 번만 (입력 순서 유지)
        urls = list(dict.fromkeys(_http_url(u) for u in v if u and u.strip()))
        if not urls:
            raise ValueError("URL 이 없습니다")
        return urls


SourceConfig = NewsKeywordConfig | BoardSourceConfig | UrlSourceConfig

CONFIG_MODELS: dict[SourceType, type[SourceConfig]] = {
    SourceType.NEWS_KEYWORD: NewsKeywordConfig,
    SourceType.BOARD: BoardSourceConfig,
    SourceType.URL: UrlSourceConfig,
}


def validate_config(source_type: SourceType, data: dict | SourceConfig) -> SourceConfig:
    """유형에 맞는 설정인지 검증한다. 틀리면 pydantic.ValidationError."""
    model = CONFIG_MODELS[SourceType(source_type)]
    if isinstance(data, model):
        return data
    if not isinstance(data, dict):
        raise TypeError(f"{source_type} 소스에 {type(data).__name__} 설정을 넣을 수 없습니다")
    return model.model_validate(data)
