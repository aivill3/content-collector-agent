"""전역 설정. 환경변수에서 읽는다. (content-collector settings.py 에서 이동)

taekwonw-agent 의 config/settings.py 에서 수집에 필요한 값만 옮겼다.
노션·Gemini·삽화·보관 정책 관련 값은 모두 뺐다.

유저별로 달라지는 값(키워드, 수집 건수, 조회 기간, 게시판 설정)은 여기 두지 않는다.
함수 인자로 받는다 — 나중에 API 서버·DB 에서 유저 설정을 넘기기 위해서다.
"""
import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

KST = timezone(timedelta(hours=9), name="KST")

# backend/app/core/config.py → BASE_DIR = backend/, ROOT_DIR = 저장소 루트
BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BASE_DIR.parent
# .env 는 저장소 루트에 둔다 (docker-compose 와 같은 위치). backend/.env 가 있으면 그쪽이 우선.
load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")

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