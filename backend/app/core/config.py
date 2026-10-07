"""전역 설정. 환경변수에서 읽는다. (content-collector settings.py 에서 이동)

taekwonw-agent 의 config/settings.py 에서 수집에 필요한 값만 옮겼다.
노션·Gemini·삽화·보관 정책 관련 값은 모두 뺐다.

유저별로 달라지는 값(키워드, 수집 건수, 조회 기간, 게시판 설정)은 여기 두지 않는다.
함수 인자로 받는다 — 나중에 API 서버·DB 에서 유저 설정을 넘기기 위해서다.
"""
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

# 수집 원본을 읽을 때의 시간대. 네이버 검색 API·국내 게시판은 한국 시각으로 날짜를 적으므로
# 시간대 표기가 없는 날짜('2026.09.25', '14:32')를 이 시간대로 해석한다. 표시 시간대와는 별개다.
KST = ZoneInfo("Asia/Seoul")

# backend/app/core/config.py → BASE_DIR = backend/, ROOT_DIR = 저장소 루트
BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BASE_DIR.parent
# .env 는 저장소 루트에 둔다 (docker-compose 와 같은 위치). backend/.env 가 있으면 그쪽이 우선.
load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")

# ── 시간대 ──────────────────────────────────────────────
# DB 에는 UTC 로 저장한다. 화면·API 응답의 시각, '오늘'·일별·최근 N일 집계, 소스의 schedule_time 은
# 이 시간대 기준이다. 변환은 app/core/timeutil.py 로만 한다 (오프셋을 코드에 적지 않는다).
DISPLAY_TZ_NAME = os.getenv("DISPLAY_TZ") or "Asia/Seoul"
try:
    DISPLAY_TZ = ZoneInfo(DISPLAY_TZ_NAME)
except (ZoneInfoNotFoundError, ValueError) as e:
    raise RuntimeError(f"DISPLAY_TZ='{DISPLAY_TZ_NAME}' 는 IANA 시간대 이름이 아닙니다 (예: Asia/Seoul)") from e

# ── 네이버 검색 API ─────────────────────────────────────
# 네이버 검색 API 는 개발자센터에서 NAVER API HUB 로 이전 중이다.
# (2026-07-31 구 방식 신규 신청 종료, 2027-06-30 구 방식 지원 종료)
# hub | legacy | auto  — auto 는 HUB 를 먼저 시도하고 401/403 이면 구 방식으로 재시도.
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
NAVER_API_MODE = os.getenv("NAVER_API_MODE", "auto").lower()

# ── 네트워크 / 병렬 처리 ─────────────────────────────────
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))  # 초
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))           # 본문 추출 병렬 스레드 수

# ── 게시판 수집 예절 ────────────────────────────────────
# 같은 사이트에 연달아 요청할 때의 간격(초). 목록 페이지 사이, 본문 요청 사이 모두 적용.
BOARD_REQUEST_DELAY = float(os.getenv("BOARD_REQUEST_DELAY", "1.0"))
# 게시판 본문을 받을 때의 동시 요청 수. 뉴스(여러 언론사로 분산)와 달리
# 한 사이트에 몰리므로 낮게 둔다.
BOARD_MAX_WORKERS = int(os.getenv("BOARD_MAX_WORKERS", "2"))
# robots.txt 준수 여부. 외부 판매 서비스라면 끄지 않는 것을 권한다.
RESPECT_ROBOTS = os.getenv("RESPECT_ROBOTS", "true").lower() != "false"

# ── DB ──────────────────────────────────────────────────
# 개발은 SQLite, 운영은 PostgreSQL. 코드는 같고 이 값만 바꾼다.
#   postgresql+psycopg://user:pass@host:5432/dbname
# 상대 경로 SQLite 는 실행 위치에 따라 파일이 달라지므로 backend/data/ 로 고정한다.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{(BASE_DIR / 'data' / 'app.db').as_posix()}"

# ── site-crawler 서버 및 인증 설정 (추가) ───────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
X_INTERNAL_SECRET = os.getenv("X_INTERNAL_SECRET", "my-super-secret-internal-key")
MAX_CONCURRENT_SCRAPES = int(os.getenv("MAX_CONCURRENT_SCRAPES", "5"))