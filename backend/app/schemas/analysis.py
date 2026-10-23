"""키워드 분석 응답. 이름은 frontend/lib/types.ts 의 AnalysisSettings·ContentMetrics 와 맞춘다."""
from app.db.models import ContentAnalysis, ContentKeywordStat
from app.domain.analysis import AnalysisSettings
from app.domain.enums import Relevance
from app.schemas.base import CamelModel, DisplayDateTime
from app.services.analysis_service import TopWord


class MetricFlagsOut(CamelModel):
    tokens: bool
    unique: bool
    nouns: bool
    sentences: bool
    avg_len: bool
    ttr: bool


class AnalysisSettingsOut(CamelModel):
    """적용 중인 분석 설정 (domain/analysis.AnalysisSettings)."""
    version: int
    preset: str
    metrics: MetricFlagsOut
    top_n: int
    ttr_warn: float
    min_body: int | None
    denom: str
    pos_range: str
    density_warn: float
    warn_min_count: int
    warn_min_nouns: int
    min_mentions: int
    dens_title: float
    dens_no_title: float
    dens_min_len: int
    require_title: bool
    passing_mode: str

    @classmethod
    def of(cls, s: AnalysisSettings) -> "AnalysisSettingsOut":
        return cls.model_validate({**s.__dict__, "metrics": MetricFlagsOut(**s.metrics.__dict__)})


class ContentMetricsOut(CamelModel):
    tokens: int
    unique: int
    nouns: int
    sentences: int
    avg_len: float
    ttr: float


class TopWordOut(CamelModel):
    word: str
    pos: str
    count: int
    density: float          # 분모 대비 %


class KeywordStatOut(CamelModel):
    keyword: str
    mentions: int
    density: float          # 1,000자당
    title_has: bool
    relevance: Relevance


class ContentAnalysisOut(CamelModel):
    settings_version: int
    analyzer: str
    analyzed_at: DisplayDateTime
    relevance: Relevance | None
    metrics: ContentMetricsOut
    top_words: list[TopWordOut]          # 지금 설정의 품사 범위·분모·top_n 으로 계산
    keywords: list[KeywordStatOut]       # 이 글을 찾은 키워드 순서

    @classmethod
    def of(cls, a: ContentAnalysis, *, top_words: list[TopWord],
           stats: list[ContentKeywordStat]) -> "ContentAnalysisOut":
        return cls(
            settings_version=a.settings_version, analyzer=a.analyzer, analyzed_at=a.analyzed_at,
            relevance=a.relevance,
            metrics=ContentMetricsOut(tokens=a.tokens, unique=a.unique_tokens, nouns=a.nouns,
                                      sentences=a.sentences, avg_len=a.avg_sentence_len, ttr=a.ttr),
            top_words=[TopWordOut(word=w.term, pos=w.pos, count=w.count, density=w.density) for w in top_words],
            keywords=[KeywordStatOut(keyword=s.keyword, mentions=s.mentions, density=s.density,
                                     title_has=s.title_has, relevance=s.relevance) for s in stats],
        )
