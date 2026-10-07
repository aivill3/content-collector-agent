"""수집 소스 API 의 응답."""
from app.db.models import Source
from app.domain.enums import SourceType
from app.schemas.base import CamelModel


class SourceOption(CamelModel):
    """필터 선택지용 — 이름만 필요한 화면(콘텐츠 목록 등)이 쓴다."""
    id: int
    name: str
    type: SourceType

    @classmethod
    def of(cls, s: Source) -> "SourceOption":
        return cls(id=s.id, name=s.name, type=s.type)
