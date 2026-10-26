"""저장된 콘텐츠 키워드 분석 — 분석(services)과 저장(repositories)을 묶는다.

    python -m app.cli analyze-contents          # 분석 안 된 글만 (수집 직후 runner 도 이것을 부른다)
    python -m app.cli analyze-contents --all    # 모두 다시 (분석기·분석 규칙을 바꾼 뒤)

한 글의 분석:
    정제 본문 → analyze_text (지표·단어 횟수) → 저장
    이 글을 찾은 키워드(content_keyword_hits)마다 keyword_stat → judge → 저장, 글의 관련도 = 가장 강한 판정

이미 분석한 글이 다음 수집에서 새 키워드로 걸리면 그 키워드의 수치만 더한다 (본문은 다시 분석하지 않는다).
수집 작업과 달리 분석 실패는 작업 상태를 바꾸지 않는다 — 다음 analyze_pending 이 다시 시도한다.
"""
import uuid
from dataclasses import dataclass

from sqlmodel import Session

from app.core.logger import get_logger
from app.db.models import Content
from app.domain.analysis import AnalysisSettings
from app.repositories import analyses, contents
from app.services import analysis_service

log = get_logger(__name__)

_COMMIT_EVERY = 100   # 많은 글을 분석할 때 이만큼마다 커밋한다 (중간에 멈춰도 한 일은 남는다)


@dataclass
class AnalyzeSummary:
    analyzed: int = 0          # 본문을 분석한 글
    keyword_stats: int = 0     # 키워드 수치만 더한 글 (이미 분석된 글에 새 키워드)


def _keyword_stats(c: Content, keywords: list[str], s: AnalysisSettings):
    out = []
    for kw in keywords:
        stat = analysis_service.keyword_stat(kw, c.title, c.cleaned_body)
        out.append((stat, analysis_service.judge(stat, len(c.cleaned_body), s)))
    return out


def analyze_content(session: Session, workspace_id: uuid.UUID, content_id: int) -> bool:
    """글 하나를 지금 설정으로 (다시) 분석한다. 없거나 다른 워크스페이스 것이면 False. 커밋은 부르는 쪽이."""
    c = contents.get_content(session, workspace_id, content_id)
    if c is None:
        return False
    s = analyses.get_settings(session, workspace_id, c.source_id)
    body = c.cleaned_body
    too_short = s.min_body is not None and len(body) < s.min_body
    result = analysis_service.TextAnalysis() if too_short else analysis_service.analyze_text(body)
    analyses.save_text_analysis(session, workspace_id, c.id, result,
                                body_length=len(body), settings_version=s.version)
    keywords = [h.keyword for h in contents.list_hits(session, workspace_id, c.id)]
    if keywords:
        analyses.add_keyword_stats(session, workspace_id, c.id, _keyword_stats(c, keywords, s))
    return True


def analyze_pending(session: Session, workspace_id: uuid.UUID, *, reanalyze_all: bool = False) -> AnalyzeSummary:
    """분석 안 된 글(reanalyze_all 이면 전부)을 분석하고, 새 키워드의 수치를 더한다. 커밋한다."""
    summary = AnalyzeSummary()
    ids = (analyses.all_content_ids if reanalyze_all else analyses.unanalyzed_content_ids)(session, workspace_id)
    for i, content_id in enumerate(ids, 1):
        analyze_content(session, workspace_id, content_id)
        summary.analyzed += 1
        if i % _COMMIT_EVERY == 0:
            session.commit()

    for content_id, keywords in analyses.hits_without_stats(session, workspace_id).items():
        c = contents.get_content(session, workspace_id, content_id)
        s = analyses.get_settings(session, workspace_id, c.source_id)
        analyses.add_keyword_stats(session, workspace_id, content_id, _keyword_stats(c, keywords, s))
        summary.keyword_stats += 1
    session.commit()
    if summary.analyzed or summary.keyword_stats:
        log.info(f"키워드 분석: 본문 {summary.analyzed}건, 새 키워드 수치 {summary.keyword_stats}건")
    return summary
