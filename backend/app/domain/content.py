"""수집 파이프라인이 들고 다니는 데이터.

taekwonw-agent core/article_models.py → content-collector models.py → 여기.
중복 제거 함수(canonical_url, dedupe)는 processors/deduplication.py 로 분리했다.

이 클래스는 DB 테이블(db/models.py)이나 API 응답 형식(schemas/)이 아니다.
수집기 → 추출 → 정제 사이를 오가는 값일 뿐이고, 저장할 때 DB 모델로 옮겨 담는다.
세 가지를 분리해 두어야 DB 컬럼을 바꿀 때 수집 코드가 흔들리지 않는다.

모든 필드에 기본값이 있다. 단계가 건너뛰어져도 AttributeError 로 멈추지 않게.

body 와 body_clean 을 둘 다 남기는 이유:
  정제는 되돌릴 수 없다. 규칙이 본문을 과하게 지웠을 때 원본과 대조해야 원인을
  찾을 수 있다. extractors/cleaner.diagnose() 가 body 를 다시 훑는다.
"""
from dataclasses import asdict, dataclass


@dataclass
class Article:
    # ── 수집 ──
    title: str = ""
    url: str = ""
    source: str = ""          # "naver" | "board" | "website"
    press: str = ""           # 언론사명 / 사이트명
    published: str = ""       # ISO 8601 (KST). 모르면 빈 값
    summary: str = ""         # 검색 API 요약. 본문 추출 실패 시의 보험
    search_keyword: str = ""  # 이 글을 찾은 키워드 (게시판 수집이면 빈 값)
    search_rank: int = 0      # 검색 결과 / 게시판 목록에서의 순서 (1부터)
    board_url: str = ""       # 게시판 수집일 때, 목록 페이지 URL

    # ── 본문 ──
    body: str = ""            # 추출 원본 (정제 전)
    body_clean: str = ""      # 정제 결과

    @property
    def date(self) -> str:
        return self.published[:10] if self.published else ""

    def to_dict(self) -> dict:
        return asdict(self)
