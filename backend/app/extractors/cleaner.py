"""본문 정제. (taekwonw-agent agents/collecting/body_cleaner.py 이식)

이식하며 바꾼 점: clean_all() 이 min_len·korean_only 를 인자로 받는다.
게시판 글은 뉴스보다 짧은 경우가 많고, 해외 사이트를 수집할 수도 있기 때문이다.

원본 설명:

설계 원칙 ("clean-then-full"):
  - LLM 없이 결정론적(regex/문자열)으로 boilerplate만 제거한다.
  - 팩트(선수명·대회명·점수·날짜 등)가 담긴 본문은 절대 자르지 않는다.
  - 원본은 Article.body에 보존, 정제 결과는 Article.body_clean에 저장.
    → 후속 팩트체크 단계에서 원본과 대조할 소스를 잃지 않기 위함.

정제 대상(제거하는 것):
  1. 이미지 캡션 블록  : '|' 로 감싼 HTML 표 셀 (사진 설명 + 촬영 크레딧)
  2. 통신사 캡션 줄    : '(지역=매체) 이름 기자 = 설명. 연.월.일' 형태 (연합뉴스식)
                         '[지역=매체] 이름 기자 = 설명. 연.월.일. 이메일' 형태 (뉴시스식)
                         '[지역=매체] 설명 (사진=… 제공) *재판매 및 DB 금지' 형태 (뉴시스식)
                         ※ 같은 프리픽스라도 날짜로 끝나지 않으면 기사 리드로 보고
                            프리픽스만 벗긴 뒤 본문은 보존한다
  1-1. 요약 박스       : 기사 앞의 자동 요약 + '전체 내용을 이해하기 위해서는…' 안내 (연합뉴스식)
  3. 기자 바이라인     : '지역=이름 기자 [이메일]' 형태의 서명 줄
                         + '[매체명 이름 기자]' 형태의 본문 내 대괄호 바이라인
                         + 줄 맨 앞 '(매체명 이름 기자)' 소괄호 바이라인
  5-3. 사진 캡션·출처  : 'ⓒ 매체 이름 기자' 표기(앞의 날짜 포함)와 그 앞의 캡션 (뉴스1식).
                         붙은 머리글 절단 뒤에 돌린다. 포토 기사는 캡션이 빠져 최소 길이에서 제외된다
  4. 저작권/재배포 문구: 무단전재, 재배포, 저작권자, ⓒ, ©, Copyright 포함 줄
                         + 매체 고정 꼬리말 줄 ('◎공감언론 뉴시스 …')
  5. 기사 종결 마커    : '(끝)' 으로 시작하는 줄부터 끝까지 절단 (연합뉴스식)
  5-1. 관련기사 섹션   : '관련기사' '많이 본 뉴스' 등 머리글부터 끝까지 절단.
                         기호 없이 제목만 나열되는 매체(무예신문 등) 대응
  6. 관련기사/부제 목록: 본문 '끝'과 '앞머리'에 연속으로 붙은 목록 줄
                         ('- ', '* ☞', '▶' 등) 블록. 앞머리 블록은 기사 부제로,
                         본문 내용과 중복이라 제거해도 팩트 손실이 없다
                         ※ 본문 중간의 목록(일정·명단 등)은 팩트일 수 있어 보존
  7. 꺾쇠 바이라인     : '<최지훈 기자>' 형태 (줄바꿈으로 쪼개진 경우 포함)
  8. 무표식 캡션(휴리스틱): 짧은 줄(100자 이하)이 '모습.'/'장면.'으로 명사형 종결
                         → 사진 캡션으로 판정해 삭제. 본문 문장은 '~했다/~이다'로
                         끝나므로 충돌이 드물지만, 유일한 확률적 규칙임에 유의
  9. 이메일 주소       : 본문 어디에 있든 제거 (사이트가 가린 '[email protected]' 포함)
 10. 공백 노이즈       : 탭, 중복 공백, 중복 개행 정규화
 11. 제목 줄·부제      : 제목을 받으면(clean_content(text, title)) 맨 앞의 제목 줄과
                         바로 뒤 부제(짧고 문장으로 끝나지 않는 줄)를 제거

기사 단위 제외(정제 후 판정):
  - 정제 후 본문이 MIN_CLEAN_LEN(100자) 미만
  - 비한국어 기사: 한글/라틴 문자 중 한글 비율이 KOREAN_MIN_RATIO(50%) 미만
    (NFL, NBA 같은 영문 용어가 섞인 한국어 기사는 한글이 압도적이라 통과)
"""
import re

from app.core.logger import get_logger
from app.domain.content import Article

log = get_logger(__name__)

MIN_CLEAN_LEN = 100      # 정제 후 이 길이 미만이면 블로그 소재로 부적합 판정
KOREAN_MIN_RATIO = 0.5   # (한글 / (한글+라틴)) 이 값 미만이면 비한국어로 판정

# ── 정규식 패턴 (모듈 로드 시 1회 컴파일) ──────────────

# 이메일 주소
RE_EMAIL = re.compile(r"[\w.\-]+@[\w.\-]+\.\w+")

# 언어 판정에서 뺄 URL. 도메인·경로는 전부 라틴 문자라, 링크가 몇 개만 남아도
# 한글 비율이 기준 아래로 떨어진다.
RE_URL = re.compile(r"https?://\S+|www\.\S+")

# 언어 판정용: 한글 음절 / 라틴 알파벳
RE_HANGUL = re.compile(r"[가-힣]")

# 언어 오판 진단용. 라틴 문자가 길게 이어지는 구간을 찾는다.
RE_LATIN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9\s.,'\-]{20,}")
RE_LATIN = re.compile(r"[A-Za-z]")

# 기자 바이라인: (선택)지역= + 이름(한글 2~4자) + '기자' + (선택)이메일
# 예) "부산=홍길동 기자", "인천=김철수 기자 reporter@example.com", "이영희 기자"
RE_BYLINE = re.compile(
    r"^\s*(?:[가-힣A-Za-z]+\s*=\s*)?[가-힣]{2,4}\s*기자(?:\s*[\w.\-]+@[\w.\-]+)?\s*$"
)

# 본문 내 대괄호 바이라인: [아이뉴스24 박민수 기자], [서울=연합뉴스 OO 특파원] 등
# 줄 전체가 아니라 문단 속에 박혀 있어도 해당 대괄호 블록만 제거
RE_BRACKET_BYLINE = re.compile(r"\[[^\[\]]{0,30}(?:기자|특파원)[^\[\]]{0,30}\]")

# 줄 맨 앞의 소괄호 바이라인: '(톱스타뉴스 김수아 기자) 독일 쾰른에서 …'
# 본문의 '(25·용인특례시청)' 같은 괄호와 섞이지 않게 줄 맨 앞, '기자)' 로 닫히는 것만.
# 통신사 프리픽스 '(서울=연합뉴스) 배진남 기자 =' 는 '기자' 가 괄호 밖이라 걸리지 않는다.
RE_PAREN_BYLINE = re.compile(r"^(\s*)\([^()=]{0,20}[가-힣]{2,4}\s*(?:기자|특파원)\)\s*", re.MULTILINE)

# 사진 출처 표기: '… 세리머니를 하고 있다. 2026.10.1 ⓒ 뉴스1 안은나 기자대한민국 윤규성이 …'
# 표기 바로 앞이 사진 캡션이다. 뉴스1 은 부제·캡션·다음 캡션을 공백 없이 한 줄로 붙여 내보내
# 줄 단위로는 못 지운다 — 표기를 기준으로 앞 구간을 도려낸다 (strip_photo_captions).
RE_PHOTO_CREDIT = re.compile(
    r"\s*(?:\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\.?\s*)?[ⓒ©]\s*[가-힣A-Za-z0-9]{1,10}\s+[가-힣]{2,4}\s*기자"
)
# 표기 앞 구간이 이 길이 이하면 통째로 캡션(+ 붙은 부제)으로 보고 지운다.
# 더 길면 본문 문단에 캡션이 붙은 것으로 보고 마지막 문장(캡션)만 지운다.
PHOTO_CAPTION_MAX = 200
RE_SENTENCE_END = re.compile(r"[.!?][\"'”’]?\s+")

# 연합뉴스 요약 박스: 기사 위에 자동 요약 몇 줄 + 이 안내 문구가 붙는다.
# 요약은 본문에 있는 내용이라, 안내 문구가 앞쪽(SUMMARY_NOTE_MAX_LINE 줄 안)에 있으면 그 위까지 지운다.
# (실측 2026-09-30 연합뉴스)
RE_SUMMARY_NOTE = re.compile(r"^\s*전체\s*내용을\s*이해하기\s*위해서는\s*기사\s*본문과\s*함께\s*읽어야\s*합니다\.?\s*$")
SUMMARY_NOTE_MAX_LINE = 6

# 통신사 프리픽스: 캡션 줄과 기사 리드 줄이 모두 이 프리픽스로 시작한다 (분기는 날짜 꼬리로)
#   연합뉴스식 '(다마스쿠스=연합뉴스) 김동호 특파원 = '
#   뉴시스식   '[도요하시(일본)=뉴시스] 이영환 기자 = ' — 대괄호 안 지역명에 괄호가 들어간다
_AGENCY_TAG = r"^\s*(?:\([^()]{1,30}=[^()]{1,30}\)|\[[^\[\]]{1,30}=[^\[\]]{1,30}\])"
RE_AGENCY_PREFIX = re.compile(_AGENCY_TAG + r"\s*[가-힣]{2,4}\s*(?:기자|특파원)\s*=\s*")

# 통신사 태그만 있는 줄의 시작: '[서울=뉴시스] ' (기자 이름 없음)
RE_AGENCY_TAG = re.compile(_AGENCY_TAG)

# 뉴시스 사진 캡션의 꼬리: '… (사진=세계태권도연맹 제공) *재판매 및 DB 금지'
# 태그로 시작하는 줄이면 캡션이라 줄째 지우고, 아니면 이 꼬리만 떼어 낸다.
RE_RESALE_TAIL = re.compile(r"\*?\s*재판매\s*및\s*DB\s*금지\s*\.?\s*$", re.IGNORECASE)

# 사이트가 이메일을 가린 자리 (Cloudflare 이메일 보호). '@' 가 없어 RE_EMAIL 로는 안 잡힌다
RE_EMAIL_PROTECTED = re.compile(r"\[\s*email\s*protected\s*\]", re.IGNORECASE)

# 통신사 캡션의 날짜 꼬리: '2026.7.29' / '2026. 7. 29.' 등으로 줄이 끝남.
# 뒤에 사진기자 이메일이 붙어도 꼬리로 본다 (뉴시스식 '… 2026.10.01. photo@newsis.com')
RE_DATE_TAIL = re.compile(
    r"\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\s*\.?\s*"
    r"(?:[\w.\-]+@[\w.\-]+\.\w+|\[\s*email\s*protected\s*\])?\s*$",
    re.IGNORECASE,
)

# 기사 종결 마커: '(끝)' 으로 시작하는 줄 (연합뉴스식, 이후는 전부 비본문)
RE_TERMINATOR = re.compile(r"^\s*\(끝\)")

# 관련기사/추천기사 섹션 머리글. 이 줄부터 문서 끝까지는 본문이 아니다.
#
# remove_edge_list_blocks 로는 못 잡는 형태가 있어서 추가했다. 그 함수는
# '-', '▶' 같은 목록 기호가 붙은 줄만 지우는데, 매체에 따라 관련기사가
# 기호 없이 '기사 제목'만 줄줄이 나열된다. 그러면 본문으로 통과해 LLM이
# 다른 사건을 이 기사의 내용인 줄 알고 써버린다.
# (실측: 무예신문 포토 기사 1건이 관련기사 5건을 본문으로 흡수해,
#  초안 한 챕터가 통째로 무관한 대회 소식으로 채워짐)
#
# 오삭제를 막기 위해 '짧은 단독 줄'일 때만 머리글로 인정한다.
# '관련 기관과 협의했다' 같은 본문 문장에서 잘리면 팩트를 잃는다.
SECTION_HEADERS = (
    "관련기사", "관련 기사", "연관기사", "추천기사", "추천 기사",
    "많이 본 뉴스", "많이본 뉴스", "많이 본 기사", "인기기사", "인기 기사",
    "주요뉴스", "주요 뉴스", "핫이슈", "실시간 뉴스", "최신기사", "최신 기사",
    "이시각 주요뉴스", "포토뉴스", "많이 읽은 기사", "베스트 클릭",
    "이 기사 어때요", "함께 보면 좋은 기사", "오늘의 주요뉴스",
    "관련 키워드", "관련키워드", "제보하기",
)

# 줄바꿈 없이 한 덩어리로 들어온 본문에서 쓰는 머리글. SECTION_HEADERS 보다
# 좁게 잡는다 — 줄 경계라는 안전장치 없이 문장 중간에서 찾기 때문이다.
# 앞 글자에 '붙어' 나올 때만 머리글로 본다. 본문 문장의 '관련 기사를 참고해'는
# 앞에 공백이 있고, 사이트가 줄바꿈을 잃고 이어 붙인 머리글은 공백이 없다.
# (실측 2026-09-23: 뉴스1 포토 기사가 '…/뉴스1관련 키워드춘천태권도…관련 기사…'
#  로 한 줄이 돼, 설악산 등산객·시내버스 노선 같은 다른 기사 제목 6건이
#  본문으로 남았다. 같은 대회의 KBS 단신과 같은 사건으로 묶이지 못한 원인)
INLINE_SECTION_HEADERS = ("관련 키워드", "관련키워드", "관련 기사", "관련기사")
RE_INLINE_SECTION = re.compile(
    r"(?<=[^\s])(?:" + "|".join(map(re.escape, INLINE_SECTION_HEADERS)) + r")"
)

# 뉴스 사이트의 화면 안내 문구 줄. 기사 내용이 아니다.
# (실측 2026-09-23 KBS: '기사 본문 영역', '읽어주기 기능은 크롬기반의 /
#  브라우저에서만 사용하실 수 있습니다.')
# (실측 2026-09-30 톱스타뉴스: Google 선호 출처 안내 'Google 선호 출처로 추가하면 더 자주 보여요.',
#  'Google에서 톱스타뉴스 자주 보기', 'Google에서 톱스타뉴스를 선택해 주세요.')
# 'Google에서 …' 로 시작하는 본문 문장이 있을 수 있어 끝말까지 맞춘다.
RE_UI_LINE = re.compile(
    r"^\s*(?:기사\s*본문\s*영역|읽어주기\s*기능|브라우저에서만\s*사용"
    r"|Google\s*선호\s*출처"
    r"|Google에서\s.{1,20}?(?:자주\s*보기|선택해\s*주세요)\.?\s*$)"
)
UI_LINE_MAX = 40
SECTION_HEADER_MAX_LEN = 20  # 이보다 긴 줄은 머리글이 아니라 본문 문장으로 본다

# 머리글을 '절단점'으로 인정하려면 그 앞에 이만큼의 본문이 있어야 한다.
#
# 이게 없으면 기사 전체가 사라진다. 일부 매체는 trafilatura 추출 결과의
# 첫 줄에 카테고리 라벨('포토뉴스', '주요 뉴스')이 딸려 오는데, 그 줄을
# 절단점으로 잡으면 lines[:0] = 빈 문자열이 된다.
# (실측 2026-08-14: 13건 중 12건이 '정제 후 0자'로 제외돼 그날 파이프라인이
#  통째로 빈손이 됨)
# 앞에 본문이 없으면 머리글이 아니라 라벨로 보고, 그 줄만 지우고 계속 훑는다.
MIN_BODY_BEFORE_HEADER = 100

# 꺾쇠 바이라인: <최지훈 기자> — trafilatura가 줄바꿈으로 쪼개는 경우가 있어
# ([^<>]가 개행도 매칭하므로) 텍스트 전체 대상으로 줄 경계를 넘어 제거한다
RE_ANGLE_BYLINE = re.compile(r"<[^<>]{0,30}(?:기자|특파원)[^<>]{0,10}>")

# 무표식 캡션 종결: '…하는 모습.' / '…하는 장면.' (명사형 종결은 캡션의 특징)
RE_CAPTION_TAIL = re.compile(r"(?:모습|장면)\s*\.?\s*$")
CAPTION_MAX_LEN = 100  # 캡션 판정 상한 (본문 장문 오삭제 방지)

# 관련기사 목록 줄 판별:
#   - '-', '*', '•' 는 뒤에 공백이 있어야 목록으로 인정 ('-5도' 같은 본문 보호)
#   - '▶▷►☞※' 기호는 공백 없이 붙어도 인정 ('▶제보는...' 대응)
RE_LIST_MARKER = re.compile(r"^\s*(?:[-*•]\s|[▶▷►☞※])")

# 저작권 / 무단전재 / 재배포 안내 (짧은 줄이면 해당 줄 제거)
RE_COPYRIGHT = re.compile(
    r"(무단\s*전재|재배포|저작권자|ⓒ|©|copyright)",
    re.IGNORECASE,
)

# 긴 줄에서는 줄을 지우지 않고 안내 문구만 도려낸다.
# 추출기가 본문을 줄바꿈 없이 한 덩어리로 뱉는 사이트가 있다. 거기에 저작권
# 문구가 섞여 있으면 줄 단위 삭제가 본문 전체를 날린다.
# (2026-09-21: 충북보건과학대 기사 953자, 난민팀 기사 439자가 0자가 됐다)
RE_COPYRIGHT_NOTICE = re.compile(
    r"[<\[(]?\s*(?:ⓒ|©|copyright)?[^.\n]{0,40}?"
    r"(?:무단\s*전재|재배포|저작권자)[^.\n]{0,40}?(?:금지|엄금)\s*[>\])]?\.?",
    re.IGNORECASE,
)

# 이 길이를 넘는 줄은 통째로 지우지 않는다. 본문 한 문단이 통째로 들어 있을
# 수 있어서다. 진짜 저작권 줄은 대개 한 문장이라 이보다 짧다.
COPYRIGHT_LINE_MAX = 80

# 매체 고정 꼬리말 줄. 저작권 문구는 아니지만 기사마다 똑같이 붙는다.
# (실측 2026-10-01 뉴시스: '◎공감언론 뉴시스 [email protected]',
#  '◎공감언론 뉴시스가 독자 여러분의 소중한 제보를 기다립니다.')
# 저작권 문구처럼 짧은 줄(COPYRIGHT_LINE_MAX 이하)일 때만 지운다.
RE_OUTLET_FOOTER = re.compile(r"^\s*◎?\s*공감언론\s*뉴시스")

# 외국어 줄 판정. 한국어 기사에 영문 요약·원문이 통째로 붙는 매체가 있다.
# 줄 단위로 걷어내야 뒤의 언어 판정이 본문만 보고 판단할 수 있다.
FOREIGN_LINE_MIN_LETTERS = 40   # 이 글자 수 미만인 줄은 판정하지 않는다
FOREIGN_LINE_RATIO = 0.7        # 라틴 비율이 이 이상이면 외국어 줄

# 여러 개의 공백/탭 → 공백 1개
RE_MULTISPACE = re.compile(r"[ \t\u00a0]+")

# 3개 이상 연속 개행 → 개행 2개 (문단 구분만 유지)
RE_MULTINEWLINE = re.compile(r"\n{3,}")


# ── 개별 정제 단계 (독립적으로 테스트 가능하도록 분리) ──

def _is_caption_line(line: str) -> bool:
    """'|' 로 시작/끝나는 이미지 캡션(HTML 표 셀) 줄인지 판별."""
    s = line.strip()
    if not s:
        return False
    return s.startswith("|") or s.endswith("|")


CAPTION_KEEP_RATIO = 0.3  # 파이프 줄을 지운 뒤 이 비율 미만이 남으면 표 레이아웃으로 판정


def remove_caption_lines(text: str) -> str:
    """'|' 로 감싼 이미지 캡션(HTML 표 셀) 줄을 제거한다.

    단, 지우고 나서 본문이 거의 남지 않으면 아무것도 지우지 않는다.
    구형 CMS를 쓰는 매체는 기사 본문 자체를 <table> 안에 넣어두고, 그러면
    trafilatura가 모든 줄을 파이프로 감싼 표로 뽑는다. 그 줄들을 캡션으로
    보고 지우면 기사가 통째로 사라진다.
    (실측 2026-08-14: 894·1198·1658·1829·752자 기사 5건이 전부 0자로 붕괴)

    남기기로 한 경우에도 파이프 기호 자체는 normalize_whitespace 가 공백으로
    바꾸므로, 본문만 살아남는다.
    """
    lines = text.split("\n")
    kept = [ln for ln in lines if not _is_caption_line(ln)]

    original_len = len("".join(ln.strip() for ln in lines))
    kept_len = len("".join(ln.strip() for ln in kept))
    if original_len and kept_len < original_len * CAPTION_KEEP_RATIO:
        return text  # 표 레이아웃 — 캡션 제거를 포기하고 원문을 보존한다

    return "\n".join(kept)


def handle_agency_prefix_lines(text: str) -> str:
    """통신사 프리픽스 줄 처리 (연합뉴스·뉴시스식). 결정론적 분기:
      - 프리픽스 있음 + 날짜로 끝남 → 사진 캡션 → 줄 전체 삭제
      - 프리픽스 있음 + 그 외      → 기사 리드 → 프리픽스만 벗기고 본문 보존
    예) '(다마스쿠스=연합뉴스) 김동호 특파원 = ...청년들. 2026.7.29'  → 삭제
        '(다마스쿠스=연합뉴스) 김동호 특파원 = "차렷, 경례!"'          → '"차렷, 경례!"'
    뉴시스 사진 캡션('[서울=뉴시스] … *재판매 및 DB 금지')은 기자 이름이 없어 꼬리로 판정한다."""
    kept = []
    for ln in text.split("\n"):
        if RE_RESALE_TAIL.search(ln):
            if RE_AGENCY_TAG.match(ln):
                continue  # 사진 캡션 줄 삭제
            ln = RE_RESALE_TAIL.sub("", ln)  # 본문 끝에 붙은 꼬리만 제거
        if RE_AGENCY_PREFIX.match(ln):
            if RE_DATE_TAIL.search(ln):
                continue  # 캡션 줄 삭제
            ln = RE_AGENCY_PREFIX.sub("", ln)  # 리드: 프리픽스만 제거
        kept.append(ln)
    return "\n".join(kept)


def remove_boilerplate_lines(text: str) -> str:
    """저작권/재배포 문구 줄과 기자 바이라인 줄을 제거한다.

    긴 줄은 지우지 않고 안내 문구만 도려낸다. 본문이 줄바꿈 없이 한 덩어리로
    들어오는 사이트에서 줄 단위 삭제가 본문 전체를 날리기 때문이다.
    """
    kept = []
    for ln in text.split("\n"):
        if RE_COPYRIGHT.search(ln):
            if len(ln) <= COPYRIGHT_LINE_MAX:
                continue
            ln = RE_COPYRIGHT_NOTICE.sub(" ", ln)
        if RE_BYLINE.match(ln):
            continue
        if len(ln) <= COPYRIGHT_LINE_MAX and RE_OUTLET_FOOTER.match(ln):
            continue
        if len(ln.strip()) <= UI_LINE_MAX and RE_UI_LINE.match(ln):
            continue
        kept.append(ln)
    return "\n".join(kept)


def remove_foreign_lines(text: str) -> str:
    """라틴 문자가 압도적인 줄을 제거한다 (영문 요약·원문 병기 대응).

    짧은 줄은 건드리지 않는다. 'WT', 'KTA' 같은 약어나 선수 영문명이 섞인
    한국어 문장까지 지우면 본문이 상한다.
    """
    kept = []
    for ln in text.split("\n"):
        hangul = len(RE_HANGUL.findall(ln))
        latin = len(RE_LATIN.findall(ln))
        total = hangul + latin
        if total >= FOREIGN_LINE_MIN_LETTERS and latin / total >= FOREIGN_LINE_RATIO:
            continue
        kept.append(ln)
    return "\n".join(kept)


def strip_bracket_bylines(text: str) -> str:
    """문단 속에 박힌 '[매체명 이름 기자]' 대괄호 바이라인,
    '<최지훈 기자>' 꺾쇠 바이라인(줄바꿈으로 쪼개진 경우 포함),
    줄 맨 앞의 '(매체명 이름 기자)' 소괄호 바이라인, 'ⓒ 매체 이름 기자' 사진 출처 표기를 제거한다."""
    text = RE_BRACKET_BYLINE.sub("", text)
    text = RE_ANGLE_BYLINE.sub("", text)
    text = RE_PAREN_BYLINE.sub(r"\1", text)
    return text


def _drop_caption(segment: str) -> str:
    """출처 표기 앞 구간에서 캡션을 뺀 나머지."""
    if len(segment.strip()) <= PHOTO_CAPTION_MAX:
        return ""
    body = segment.rstrip()
    cut = max((m.end() for m in RE_SENTENCE_END.finditer(body[:-1])), default=0)
    return body[:cut]


def strip_photo_captions(text: str) -> str:
    """사진 출처 표기('2026.10.1 ⓒ 뉴스1 안은나 기자')와 그 앞의 캡션을 지운다.

    사진만 있는 기사(포토 기사)는 캡션이 빠지면 본문이 거의 남지 않아 clean_all 의
    최소 길이 판정에서 제외된다 — 사진 기사를 따로 판정하지 않고 이 경로로 거른다.
    (실측 2026-10-01 뉴스1 포토 기사 2건이 캡션만으로 116·214자가 돼 저장됐다)

    '붙은 머리글 절단' 뒤에 돌린다 — 표기 바로 뒤에 공백 없이 붙은 '관련 키워드' 가
    절단점이라, 먼저 표기를 지우면 절단점을 놓친다."""
    out = []
    for ln in text.split("\n"):
        parts, start = [], 0
        for m in RE_PHOTO_CREDIT.finditer(ln):
            parts.append(_drop_caption(ln[start:m.start()]))
            start = m.end()
        parts.append(ln[start:])
        out.append(" ".join(p for p in parts if p.strip()) if len(parts) > 1 else ln)
    return "\n".join(out)


def remove_summary_box(text: str) -> str:
    """기사 앞에 붙은 자동 요약 박스(연합뉴스식)를 안내 문구까지 지운다.
    안내 문구가 앞쪽에 없으면 아무것도 지우지 않는다 — 본문 중간의 같은 문장은 건드리지 않는다."""
    lines = text.split("\n")
    for i, ln in enumerate(lines[:SUMMARY_NOTE_MAX_LINE]):
        if RE_SUMMARY_NOTE.match(ln):
            return "\n".join(lines[i + 1:])
    return text


def remove_unmarked_caption_lines(text: str) -> str:
    """무표식 사진 캡션 제거 (휴리스틱).
    짧은 줄(CAPTION_MAX_LEN 이하)이 '모습/장면'으로 명사형 종결하면 캡션으로 판정.
    예) '최승민 관장이 ... 신호를 기다리고 있는 모습.' → 삭제
    본문 문장은 '~했다/~이다' 등 용언으로 끝나므로 충돌이 드물다."""
    kept = []
    for ln in text.split("\n"):
        s = ln.strip()
        if s and len(s) <= CAPTION_MAX_LEN and RE_CAPTION_TAIL.search(s):
            continue
        kept.append(ln)
    return "\n".join(kept)


def truncate_at_terminator(text: str) -> str:
    """'(끝)' 으로 시작하는 줄을 만나면 그 줄부터 끝까지 절단한다.
    연합뉴스는 본문 종료를 (끝)으로 표시하며, 이후는 관련기사·홍보 등 비본문."""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if RE_TERMINATOR.match(ln):
            return "\n".join(lines[:i])
    return text


def truncate_at_section_header(text: str) -> str:
    """관련기사/많이 본 뉴스 등 섹션 머리글부터 끝까지 절단한다.

    (끝) 절단과 같은 원리이되 연합뉴스 외 매체를 대상으로 한다.
    머리글 아래에 오는 것은 전부 다른 사건의 기사 제목이라, 남겨두면
    LLM이 이 기사의 내용으로 오인해 초안에 섞어 쓴다.

    보수적으로 판정한다:
      - 줄 전체가 SECTION_HEADER_MAX_LEN 이하로 짧아야 한다
      - 머리글로 시작해야 한다 (문장 중간 등장은 무시)
      - 앞에 MIN_BODY_BEFORE_HEADER 이상의 본문이 쌓여 있어야 한다
    '관련 기사를 참고해 협약을 맺었다' 같은 본문 문장에서 잘리지 않게 하기 위함이다.

    마지막 조건이 핵심이다. 앞에 본문이 없는데 자르면 기사가 통째로 사라진다.
    그 위치의 머리글은 관련기사 섹션이 아니라 매체의 카테고리 라벨이므로,
    절단하지 않고 그 줄만 버린 뒤 계속 훑는다.
    """
    lines = text.split("\n")
    kept: list[str] = []
    body_len = 0
    for ln in lines:
        # 머리글을 감싸는 장식 기호를 벗겨낸다 ('[관련기사]', '◆ 주요뉴스' 등)
        s = ln.strip().strip("[]<>()【】〔〕·■□◆◇●○▶▷►▸☞※★☆|-*• \t")
        is_header = bool(s) and len(s) <= SECTION_HEADER_MAX_LEN and any(
            s.startswith(h) for h in SECTION_HEADERS
        )
        if is_header:
            if body_len >= MIN_BODY_BEFORE_HEADER:
                break          # 본문 뒤 → 여기서부터 관련기사 섹션, 절단
            continue           # 본문 앞 → 카테고리 라벨, 그 줄만 버림
        kept.append(ln)
        body_len += len(ln.strip())
    return "\n".join(kept)


def truncate_at_inline_header(text: str) -> str:
    """앞 글자에 붙어 나온 관련기사 머리글부터 끝까지 절단한다.

    truncate_at_section_header 는 줄 단위라, 본문이 줄바꿈 없이 한 덩어리로
    오면 머리글을 못 찾는다. 여기서는 문장 중간을 보되 두 조건을 둔다.
      - 머리글이 앞 글자에 공백 없이 붙어 있어야 한다 (RE_INLINE_SECTION)
      - 그 앞에 MIN_BODY_BEFORE_HEADER 이상의 본문이 있어야 한다
    """
    for m in RE_INLINE_SECTION.finditer(text):
        if len(text[: m.start()].strip()) >= MIN_BODY_BEFORE_HEADER:
            return text[: m.start()].rstrip()
    return text


def remove_edge_list_blocks(text: str) -> str:
    """본문 '앞머리'와 '끝'에 연속으로 붙은 목록 줄 블록을 제거한다.
      - 끝 블록   : 관련기사 / 많이 본 뉴스 / 제보·앱 홍보
      - 앞머리 블록: '▶ ...' 형태의 기사 부제 (본문 내용과 중복)
    양끝에서 안쪽으로 훑으며 목록 줄과 빈 줄만 걷어내고, 일반 문단을 만나면
    멈춘다 → 본문 중간의 목록(일정·명단 등 팩트)은 건드리지 않는다."""
    lines = text.split("\n")

    start = 0
    while start < len(lines):
        s = lines[start].strip()
        if not s or RE_LIST_MARKER.match(s):
            start += 1
            continue
        break

    end = len(lines)
    while end > start:
        s = lines[end - 1].strip()
        if not s or RE_LIST_MARKER.match(s):
            end -= 1
            continue
        break

    return "\n".join(lines[start:end])


def strip_emails(text: str) -> str:
    return RE_EMAIL_PROTECTED.sub("", RE_EMAIL.sub("", text))


def normalize_whitespace(text: str) -> str:
    """탭/중복 공백/중복 개행/남은 파이프 조각을 정리한다."""
    lines = []
    for ln in text.split("\n"):
        ln = ln.replace("|", " ")        # 캡션 제거 후 남은 파이프 조각 제거
        ln = RE_MULTISPACE.sub(" ", ln)  # 다중 공백/탭 → 공백 1개
        lines.append(ln.strip())
    text = "\n".join(lines)
    text = RE_MULTINEWLINE.sub("\n\n", text)  # 과도한 빈 줄 축소
    return text.strip()


def korean_ratio(text: str) -> float:
    """한글 비율. 판정할 문자가 없으면 0.0.

    한글과 라틴 알파벳만 세고, 숫자·문장부호·공백은 언어 판정에 중립이므로
    분모에서 뺀다. URL 과 이메일도 뺀다 — 주소는 전부 라틴 문자라 본문이
    한국어여도 링크 몇 개에 비율이 무너진다.
    (2026-09-21: '춘천시, 2029년까지 국제태권도 3종 개최' 등 2건이
     비한국어로 오판돼 제외됐다. 4개 매체가 보도한 사건이었다)
    """
    sample = RE_URL.sub(" ", text)
    sample = RE_EMAIL.sub(" ", sample)
    hangul = len(RE_HANGUL.findall(sample))
    latin = len(RE_LATIN.findall(sample))
    total = hangul + latin
    return hangul / total if total else 0.0


def is_korean(text: str) -> bool:
    """한글 비율 기반 한국어 판정."""
    return korean_ratio(text) >= KOREAN_MIN_RATIO


# ── 오케스트레이터 ─────────────────────────────────────

CLEAN_STEPS = (
    ("캡션 줄", remove_caption_lines),
    ("요약 박스", remove_summary_box),
    ("통신사 프리픽스", handle_agency_prefix_lines),
    ("저작권·바이라인", remove_boilerplate_lines),
    ("대괄호·꺾쇠 바이라인", strip_bracket_bylines),
    ("무표식 캡션", remove_unmarked_caption_lines),
    ("(끝) 절단", truncate_at_terminator),
    ("섹션 머리글 절단", truncate_at_section_header),
    ("붙은 머리글 절단", truncate_at_inline_header),
    ("사진 캡션·출처", strip_photo_captions),
    ("양끝 목록 블록", remove_edge_list_blocks),
    ("이메일", strip_emails),
    ("외국어 줄", remove_foreign_lines),
    ("공백 정규화", normalize_whitespace),
)


# 본문 맨 앞의 제목 줄 + 부제. 추출기가 기사 머리(제목·부제 영역)를 본문으로 가져오는 매체가 있다.
# (실측 2026-10-01 뉴시스: 제목 + 부제 3줄, Mookas: 제목 전문 + 부제 1줄)
# 제목은 본문만 봐서는 알 수 없어 CLEAN_STEPS 밖에서 제목을 받아 처리한다.
TITLE_PREFIX_MIN = 10   # '...' 로 잘린 제목은 남은 앞부분이 이만큼은 돼야 비교한다
SUBTITLE_MAX_LEN = 60   # 제목 줄 뒤의 이 길이 이하 줄을 부제로 본다
SUBTITLE_MAX_LINES = 4
RE_TITLE_ELLIPSIS = re.compile(r"\s*(?:\.{2,}|…)\s*$")
RE_SENTENCE_TAIL = re.compile(r"[.!?][\"'”’)]?\s*$")   # 문장으로 끝나면 부제가 아니라 본문


def _squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _is_title_line(line: str, title: str) -> bool:
    line, title = _squash(line), _squash(title)
    if not line or not title:
        return False
    if line == title:
        return True
    # 검색 API 제목은 '…' 로 잘려 온다 — 잘리기 전 앞부분으로 시작하는지 본다
    prefix = _squash(RE_TITLE_ELLIPSIS.sub("", title))
    return prefix != title and len(prefix) >= TITLE_PREFIX_MIN and line.startswith(prefix)


def remove_title_block(text: str, title: str) -> str:
    """첫 줄이 제목이면 지우고, 바로 뒤에 이어지는 부제(짧고 문장으로 끝나지 않는 줄)도 지운다.
    제목 줄이 없으면 아무것도 지우지 않는다 — 부제만 따로 판정하지 않는다."""
    lines = text.split("\n")
    if not lines or not _is_title_line(lines[0], title):
        return text
    i = 1
    while (i <= SUBTITLE_MAX_LINES and i < len(lines) and lines[i].strip()
           and len(lines[i].strip()) <= SUBTITLE_MAX_LEN and not RE_SENTENCE_TAIL.search(lines[i])):
        i += 1
    return "\n".join(lines[i:]).strip()


def clean_content(text: str, title: str = "") -> str:
    """본문 1건 정제. 단계와 순서는 CLEAN_STEPS 에 정의돼 있다.
    title 을 주면 마지막에 본문 맨 앞의 제목 줄·부제를 지운다 (remove_title_block)."""
    if not isinstance(text, str) or not text.strip():
        return ""
    for _, step in CLEAN_STEPS:
        text = step(text)
    return remove_title_block(text, title) if title else text


def diagnose(text: str, title: str = "") -> str:
    """단계별 길이 감소를 한 줄로 요약한다 (제외된 기사 원인 추적용).

    본문이 말랐을 때 어느 규칙이 범인인지 로그만 보고 알 수 있어야 한다.
    2026-08-14 에 12건이 0자로 제외됐을 때, 로그에는 결과만 있고 과정이 없어
    원인을 좁히는 데 원본 HTML을 다시 받아야 했다.
    """
    if not isinstance(text, str) or not text.strip():
        return "원본 없음"
    parts = [f"원본 {len(text)}자"]
    prev = len(text)
    for name, step in CLEAN_STEPS:
        text = step(text)
        if len(text) < prev:
            parts.append(f"{name} -{prev - len(text)}")
        prev = len(text)
    if title:
        text = remove_title_block(text, title)
        if len(text) < prev:
            parts.append(f"제목·부제 -{prev - len(text)}")
        prev = len(text)
    return " · ".join(parts) + f" = {prev}자"


def clean_all(
    articles: list[Article],
    *,
    min_len: int = MIN_CLEAN_LEN,
    korean_only: bool = True,
) -> list[Article]:
    """본문을 정제하고, 너무 짧거나(비한국어 판정 시) 쓸 수 없는 글을 뺀다.

    min_len      정제 후 이 길이 미만이면 제외 (게시판 공지 등은 낮춰 쓴다)
    korean_only  False 면 비한국어 판정을 건너뛴다 (해외 사이트 수집용)
    """
    for a in articles:
        a.body_clean = clean_content(a.body, a.title)
    result = []
    for a in articles:
        if len(a.body_clean) < min_len:
            log.warning(f"정제 후 본문 부족({len(a.body_clean)}자), 제외: {a.title[:40]}")
            # 어느 규칙이 지웠는지 남긴다. 결과만 찍으면 원인을 좁힐 수 없다.
            log.warning(f"    단계별: {diagnose(a.body, a.title)}")
            continue
        ratio = korean_ratio(a.body_clean)
        if korean_only and ratio < KOREAN_MIN_RATIO:
            # 비율과 본문 앞머리를 함께 남긴다. 제목만 찍으면 진짜 외국어
            # 기사인지 추출이 잘못된 것인지 로그만으로 가릴 수 없다.
            log.warning(
                f"비한국어 기사 제외(한글 {ratio:.0%} / 기준 {KOREAN_MIN_RATIO:.0%}): "
                f"{a.title[:40]}"
            )
            log.warning(f"    본문 앞머리: {a.body_clean[:80]}")
            # 앞머리가 멀쩡한 한국어인데 비율이 낮으면, 뒤쪽에 라틴 덩어리가
            # 있다는 뜻이다. 그 덩어리를 같이 찍어야 정체를 알 수 있다.
            runs = RE_LATIN_RUN.findall(a.body_clean)
            if runs:
                longest = max(runs, key=len)
                log.warning(
                    f"    라틴 덩어리 {len(runs)}개 · 최장 {len(longest)}자: "
                    f"{longest[:80]}"
                )
            continue
        result.append(a)
    log.info(f"정제 완료, 유효 기사 {len(result)}/{len(articles)}건")
    return result