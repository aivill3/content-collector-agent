"""저장된 콘텐츠 다시 정제 — 정제 규칙(extractors/cleaner.py)을 고친 뒤 기존 글에 적용한다.

    python -m app.cli reclean-contents --dry-run    # 바뀌는 글만 확인
    python -m app.cli reclean-contents              # 적용

원본(raw_body)에서 다시 정제해 cleaned_body·body_length 만 바꾼다. 원본은 그대로라 몇 번 실행해도 결과가 같다.
정제 후 소스의 최소 길이(min_body_length)보다 짧아진 글도 지우지 않는다 — 목록(short)으로 알려 주고
지울지는 사람이 정한다. 수집 때라면 저장되지 않았을 글이다.
"""
import uuid
from dataclasses import dataclass, field

from sqlmodel import Session

from app.core.logger import get_logger
from app.repositories import contents, sources
from app.services.collection_service import reclean_body

log = get_logger(__name__)


@dataclass
class RecleanChange:
    content_id: int
    title: str
    before: int          # 바꾸기 전 정제 본문 길이
    after: int
    min_length: int      # 소스의 최소 본문 길이


@dataclass
class RecleanSummary:
    checked: int = 0
    changed: list[RecleanChange] = field(default_factory=list)

    @property
    def short(self) -> list[RecleanChange]:
        """정제 후 소스의 최소 길이보다 짧아진 글."""
        return [c for c in self.changed if c.after < c.min_length]


def reclean_contents(session: Session, workspace_id: uuid.UUID, *, dry_run: bool = False) -> RecleanSummary:
    """워크스페이스의 모든 콘텐츠를 다시 정제한다. dry_run 이면 바꾸지 않고 결과만 돌려준다."""
    summary = RecleanSummary()
    min_length: dict[int, int] = {}
    updates: list[tuple[int, str]] = []
    for c in contents.iter_contents(session, workspace_id):
        summary.checked += 1
        cleaned = reclean_body(c.raw_body, c.title)
        if cleaned == c.cleaned_body:
            continue
        if c.source_id not in min_length:
            src = sources.get_source(session, workspace_id, c.source_id)
            min_length[c.source_id] = src.min_body_length if src else 0
        summary.changed.append(RecleanChange(c.id, c.title, c.body_length, len(cleaned), min_length[c.source_id]))
        updates.append((c.id, cleaned))

    if dry_run:
        return summary
    for content_id, cleaned in updates:
        contents.update_cleaned_body(session, workspace_id, content_id, cleaned)
    session.commit()
    log.info(f"다시 정제: {summary.checked}건 중 {len(updates)}건 변경")
    return summary
