"""키워드 분석 설정 — 형태소 지표·단어별 밀도·키워드 관련도 판정 기준.

화면의 분석 설정(SETTING-001, frontend/lib/types.ts AnalysisSettings)과 같은 항목이다.
지금은 모든 워크스페이스가 DEFAULT_SETTINGS 하나를 쓴다. 설정 저장(내 기본값·소스별)을 붙이면
repositories/analyses.get_settings 가 DB 값을 읽어 이 클래스로 돌려준다.

규칙: 수치(언급 횟수·밀도·단어 횟수)를 저장해 두고, 판정(관련도)은 그 수치와 설정으로 계산해 함께 저장한다
(목록의 관련도 필터가 DB 에서 걸러야 해서). 판정 기준(min_mentions·dens_*·require_title)이 바뀌면
저장된 수치로 판정만 다시 계산한다 — 본문 재분석은 필요 없다 (설정 저장을 붙일 때 만든다).
version 은 분석 결과(content_analyses.settings_version)에 남겨 어떤 설정으로 분석했는지 보여 준다.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricFlags:
    """콘텐츠 상세에 보여 줄 글 단위 지표. 계산은 항상 전부 하고 표시만 고른다."""
    tokens: bool = True
    unique: bool = False
    nouns: bool = True
    sentences: bool = True
    avg_len: bool = False
    ttr: bool = True


@dataclass(frozen=True)
class AnalysisSettings:
    version: int = 1
    preset: str = "normal"            # strict | normal | loose | custom — 엄격·느슨 값은 [정책 필요]

    # ── 글 단위 지표 ──
    metrics: MetricFlags = field(default_factory=MetricFlags)
    top_n: int = 15                   # 상위 키워드 개수
    ttr_warn: float = 0.35            # 어휘 다양도 경고 기준
    min_body: int | None = None       # 분석 최소 본문 길이 — 기본값 미정 [확인 필요], None 이면 모두 분석

    # ── 단어별 밀도 ──
    denom: str = "content"            # noun(명사) | content(내용어 전체)
    pos_range: str = "vva"            # noun(명사만) | vva(+동사·형용사) | foreign(+외국어)
    density_warn: float = 8           # 밀도 경고 기준 (%)
    warn_min_count: int = 3           # 경고 최소 조건: 이 횟수 이상 나온 단어만
    warn_min_nouns: int = 50          # 경고 최소 조건: 명사가 이만큼 이상인 글만

    # ── 키워드 관련도 ──
    min_mentions: int = 4             # 주제 기사가 되려면 이만큼 이상 언급
    dens_title: float = 1.5           # 1,000자당 밀도 기준 — 제목에 키워드가 있을 때
    dens_no_title: float = 3.0        # 1,000자당 밀도 기준 — 제목에 없을 때
    dens_min_len: int = 600           # 이보다 짧은 글은 밀도 검사를 건너뛴다
    require_title: bool = False       # 주제 기사는 제목에 키워드가 있어야 한다
    passing_mode: str = "dim"         # 목록에서 '스쳐 지나감' 처리: hide | dim | show


DEFAULT_SETTINGS = AnalysisSettings()
