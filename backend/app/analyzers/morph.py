"""형태소 분석 — kiwipiepy(Kiwi) 를 감싼다. 분석기를 바꾸면 이 파일만 고친다.

Kiwi 모델은 처음 쓸 때 한 번 읽는다 (1~2초, 프로세스당 한 번). 네트워크는 쓰지 않는다
(모델은 pip 패키지 kiwipiepy_model 에 들어 있다).

품사 태그는 세종 품사 체계를 따른다 (NNG 일반명사, NNP 고유명사, VV 동사, VA 형용사, SL 외국어 ...).
Kiwi 는 불규칙 활용을 'VA-I' 처럼 붙여 주는데, 여기서 '-' 뒤는 떼어 낸다.
"""
import threading
from dataclasses import dataclass

from kiwipiepy import Kiwi, __version__ as _kiwi_version

ANALYZER = f"kiwi {_kiwi_version}"   # 분석 결과에 남기는 분석기 이름·버전

_kiwi: Kiwi | None = None
_lock = threading.Lock()


def _get() -> Kiwi:
    global _kiwi
    if _kiwi is None:
        with _lock:
            if _kiwi is None:
                _kiwi = Kiwi()
    return _kiwi


@dataclass(frozen=True)
class Morph:
    form: str     # 형태 (본문에 나온 모양)
    tag: str      # 품사 태그 ('-I'·'-R' 은 뗀다)
    lemma: str    # 기본형 — 동사·형용사는 '열리다'처럼 '다'가 붙는다, 나머지는 form 과 같다


def tokenize(text: str) -> list[Morph]:
    if not text.strip():
        return []
    return [Morph(t.form, t.tag.split("-", 1)[0], t.lemma) for t in _get().tokenize(text)]


def split_sentences(text: str) -> list[str]:
    if not text.strip():
        return []
    return [s.text for s in _get().split_into_sents(text) if s.text.strip()]
