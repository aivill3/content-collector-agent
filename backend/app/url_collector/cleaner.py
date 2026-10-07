import re
from bs4 import BeautifulSoup


class TextCleaner:
    """본문 정제 및 노이즈 제거 모듈"""

    # 불필요 태그 식별자
    REMOVE_TAGS = ["script", "style", "noscript", "iframe", "header", "footer", "nav", "aside", "form"]

    # 기자/저작권/노이즈 정규식
    NOISE_PATTERNS = [
        r"기자\s*=\s*[가-힣]{2,4}",
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        r"저작권자\s*©.*?",
        r"무단전재\s*및\s*재배포\s*금지",
        r"All\s*rights\s*reserved",
        r"▶\s*네이버\s*메인에서.*?",
        r"\[사진\s*=\s*.*?\]",
    ]

    @classmethod
    def clean_html_to_text(cls, html_or_text: str) -> str:
        """HTML 또는 파싱된 텍스트에서 불필요 요소와 정규식 노이즈를 정제합니다."""
        if not html_or_text:
            return ""

        # HTML 구조인 경우 태그 정리
        if "<" in html_or_text and ">" in html_or_text:
            soup = BeautifulSoup(html_or_text, "html.parser")
            for tag in cls.REMOVE_TAGS:
                for el in soup.find_all(tag):
                    el.decompose()
            text = soup.get_text(separator="\n")
        else:
            text = html_or_text

        # 줄 단위 정제
        lines = text.splitlines()
        cleaned_lines = []

        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 3:
                continue

            # 정규식 패턴 제거
            for pattern in cls.NOISE_PATTERNS:
                line_str = re.sub(pattern, "", line_str, flags=re.IGNORECASE).strip()

            if line_str:
                cleaned_lines.append(line_str)

        # 문단 결합 및 공백 정규화
        result = "\n\n".join(cleaned_lines)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()