"""키워드 분석 — 정제 본문의 형태소 지표와 키워드 관련도. 저장하지 않는다.

    text = analyze_text(cleaned_body)                         # 글 단위 지표 + 단어별 횟수
    stat = keyword_stat("태권도", title, cleaned_body)         # 언급 횟수·1,000자당 밀도·제목 포함
    judge(stat, len(cleaned_body), settings)                  # → Relevance
    top_words(text.terms, settings)                           # 상위 키워드 (품사 범위·분모는 설정)

저장(content_analyses·content_terms·content_keyword_stats)은 workers/analysis.py 가
repositories/analyses.py 로 한다.

정의
----
- 토큰: 형태소 하나. 문장부호·기호(S* 중 SL 외국어·SH 한자·SN 숫자 제외)는 세지 않는다.
- 고유 토큰: (형태, 품사)가 다른 토큰 수. 어휘 다양도(TTR) = 고유 토큰 ÷ 토큰.
- 명사: 일반명사(NNG)·고유명사(NNP). 의존명사·수사·대명사는 뺀다.
- 단어(term): 내용어만 센다 — 명사, 동사·형용사(기본형 '열리다'), 외국어(SL).
  상위 키워드·밀도는 이 횟수로 화면이 고른 품사 범위·분모에 맞춰 계산한다 (재분석 불필요).
- 키워드 언급: 정제 본문에서 키워드 문자열이 나온 횟수 (대소문자 무시, 키워드 안의 띄어쓰기는
  있어도 없어도 같다 — '승단 심사' 는 '승단심사' 도 센다). 형태소가 아니라 문자열로 센다 —
  '태권도장' 처럼 붙여 쓴 말도 언급으로 본다.
"""
import re
from collections import Counter
from dataclasses import dataclass, field

from app.analyzers import morph
from app.domain.analysis import AnalysisSettings
from app.domain.enums import Relevance

NOUN_TAGS = frozenset({"NNG", "NNP"})
VERB_ADJ_TAGS = frozenset({"VV", "VA"})
FOREIGN_TAGS = frozenset({"SL"})
TERM_TAGS = NOUN_TAGS | VERB_ADJ_TAGS | FOREIGN_TAGS
_KEPT_SYMBOLS = frozenset({"SL", "SH", "SN"})   # S 로 시작하지만 토큰으로 세는 것

POS_RANGES: dict[str, frozenset[str]] = {
    "noun": NOUN_TAGS,
    "vva": NOUN_TAGS | VERB_ADJ_TAGS,
    "foreign": TERM_TAGS,
}

# 이 횟수 이하로 언급되면 '스쳐 지나감' (화면 범례: 한두 번 언급). 설정 항목이 아니다 [정책 필요]
PASSING_MAX_MENTIONS = 2

_RELEVANCE_ORDER = [Relevance.MAIN, Relevance.PARTIAL, Relevance.PASSING]


@dataclass(frozen=True)
class Term:
    term: str
    pos: str
    count: int


@dataclass
class TextAnalysis:
    tokens: int = 0
    unique_tokens: int = 0
    nouns: int = 0
    sentences: int = 0
    avg_sentence_len: float = 0.0     # 문장당 평균 글자 수
    ttr: float = 0.0
    terms: list[Term] = field(default_factory=list)   # 많이 나온 순


@dataclass(frozen=True)
class KeywordStat:
    keyword: str
    mentions: int
    density: float      # 1,000자당 언급 횟수
    title_has: bool


@dataclass(frozen=True)
class TopWord:
    term: str
    pos: str
    count: int
    density: float      # 분모 대비 % (분모: 설정의 denom)


def analyze_text(body: str) -> TextAnalysis:
    tokens = [m for m in morph.tokenize(body) if not (m.tag.startswith("S") and m.tag not in _KEPT_SYMBOLS)]
    if not tokens:
        return TextAnalysis()
    sentences = morph.split_sentences(body)
    unique = len({(m.form, m.tag) for m in tokens})
    terms = Counter((m.lemma if m.tag in VERB_ADJ_TAGS else m.form, m.tag) for m in tokens if m.tag in TERM_TAGS)
    return TextAnalysis(
        tokens=len(tokens),
        unique_tokens=unique,
        nouns=sum(1 for m in tokens if m.tag in NOUN_TAGS),
        sentences=len(sentences),
        avg_sentence_len=round(sum(len(s) for s in sentences) / len(sentences), 1) if sentences else 0.0,
        ttr=round(unique / len(tokens), 3),
        terms=[Term(t, pos, n) for (t, pos), n in sorted(terms.items(), key=lambda x: (-x[1], x[0]))],
    )


def _keyword_pattern(keyword: str) -> re.Pattern | None:
    words = keyword.split()
    if not words:
        return None
    return re.compile(r"\s*".join(re.escape(w) for w in words), re.IGNORECASE)


def keyword_stat(keyword: str, title: str, body: str) -> KeywordStat:
    pattern = _keyword_pattern(keyword)
    if pattern is None:
        return KeywordStat(keyword, 0, 0.0, False)
    mentions = len(pattern.findall(body))
    density = round(mentions * 1000 / len(body), 2) if body else 0.0
    return KeywordStat(keyword, mentions, density, bool(pattern.search(title)))


def judge(stat: KeywordStat, body_length: int, s: AnalysisSettings) -> Relevance:
    """주제 기사: 최소 언급 이상 + (짧은 글이 아니면) 밀도 기준 이상 + (필수면) 제목 포함.
    스쳐 지나감: PASSING_MAX_MENTIONS 회 이하. 그 사이는 부분 언급.
    """
    if stat.mentions <= PASSING_MAX_MENTIONS:
        return Relevance.PASSING
    threshold = s.dens_title if stat.title_has else s.dens_no_title
    dense = body_length < s.dens_min_len or stat.density >= threshold
    if stat.mentions >= s.min_mentions and dense and (stat.title_has or not s.require_title):
        return Relevance.MAIN
    return Relevance.PARTIAL


def best_relevance(values: list[Relevance]) -> Relevance | None:
    """키워드가 여러 개면 가장 강한 판정을 글의 관련도로 쓴다 (표시 방식 [확인 필요])."""
    return min(values, key=_RELEVANCE_ORDER.index) if values else None


def top_words(terms: list[Term], s: AnalysisSettings, *, stopwords: frozenset[str] = frozenset()) -> list[TopWord]:
    """품사 범위 안의 단어를 많이 나온 순으로 top_n 개. 불용어는 순위와 분모에서 모두 뺀다."""
    allowed = POS_RANGES.get(s.pos_range, POS_RANGES["vva"])
    kept = [t for t in terms if t.pos in allowed and t.term not in stopwords]
    denom_tags = NOUN_TAGS if s.denom == "noun" else allowed
    denom = sum(t.count for t in kept if t.pos in denom_tags)
    ranked = sorted(kept, key=lambda t: (-t.count, t.term))[: s.top_n]
    return [TopWord(t.term, t.pos, t.count, round(t.count * 100 / denom, 1) if denom else 0.0) for t in ranked]
