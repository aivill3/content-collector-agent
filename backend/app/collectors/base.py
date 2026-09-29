"""수집기 공통 인터페이스.

수집기는 '어떤 글이 있는가'까지만 책임진다. 제목·URL·날짜 등 메타데이터를
채운 Article 목록을 돌려주고, 본문은 비워 둔다. 본문 추출과 정제는
services/collection_service.py 가 extractors/ 로 공통 처리한다.

수집원을 새로 추가할 때(RSS, 유튜브 등) 이 클래스를 상속해 collect() 만 구현하면
서비스·워커·API 는 고치지 않아도 된다.
"""
from abc import ABC, abstractmethod

from app.domain.content import Article
from app.extractors.article import extract_body


class Collector(ABC):
    #: Article.source 에 들어갈 값. DB 의 Source.type 과 맞춘다.
    source_type: str = ""

    @abstractmethod
    def collect(self) -> list[Article]:
        """메타데이터만 채운 Article 목록. 수집 순서(검색 순위·목록 순서)를 유지한다."""

    def fetch(self, article: Article) -> Article:
        """글 하나의 본문을 채운다. 기본은 공통 추출기(trafilatura).

        게시판처럼 요청 간격·본문 영역 지정이 필요한 수집기는 덮어쓴다.
        """
        return extract_body(article)
