# CLAUDE.md

이 저장소에서 작업할 때 Claude Code 가 따를 규칙과 맥락.

## 프로젝트

키워드 뉴스(네이버 검색 API)·게시판·글 URL 에서 콘텐츠를 수집하는 AI Agent.
모노레포로 `backend/`(Python)와 `frontend/`(Next.js, 예정)를 함께 둔다.

## 디렉터리 규칙

- **프론트엔드 코드는 반드시 `frontend/` 안에만 만든다.** `package.json`, `next.config.*`,
  `tsconfig.json`, `app/`, `components/`, `public/` 등 Next.js 관련 파일을 저장소 루트나
  `backend/` 에 두지 않는다. npm/pnpm 명령도 `frontend/` 에서 실행한다.
- 백엔드 코드는 `backend/` 안에만 둔다.
- `.env` 는 저장소 루트에 둔다 (`backend/.env` 가 있으면 그쪽이 우선). 키 이름은 `.env.example` 참고.
- 문서는 `docs/`.

## 백엔드 (Python)

### 현재 상태

- API 서버(FastAPI, `app/api/`):
  - 소스 점검 3개 (`/api/source-checks/search · board · urls`, 저장 없음)
  - 콘텐츠 조회 (`GET /api/contents`, `GET /api/contents/{id}`) — 프론트 콘텐츠 화면이 live 모드에서 쓴다
  - 소스 선택지 (`GET /api/sources/options`)
  - URL 수집 (`POST /api/v1/scrape`, 저장 없음) — 단일 글·게시판을 자동 감지해 본문을 돌려준다
- 수집 실행은 `app/workers/runner.run_source_once` 이고, DB CLI(`python -m app.cli`)가 부른다.
  `backend/cli.py` 는 DB 없이 파일로 저장하는 디버깅용이다.
- 예정: 스케줄러(next_run_at 계산·Celery), 유저·인증, 키워드 분석, `docker-compose.yml`.
  이 중 무언가를 추가하기 전에는 사용자와 먼저 확인한다.

### 명령 (모두 `backend/` 에서 실행)

```bash
python -m venv .venv && .venv\Scripts\activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head                              # DB 스키마 (DATABASE_URL, 기본 backend/data/app.db)
python -m app.db.seed                             # 기본 워크스페이스 (여러 번 실행해도 안전)
python -m pytest                                  # 오프라인 테스트, 네트워크 불필요
uvicorn app.api.main:app --reload --port 8000     # API 서버 (http://localhost:8000/docs)

python -m app.cli add-news-source --name 태권도뉴스 --keyword 태권도 --keyword 국기원 --count 30 --days 3
python -m app.cli run-source 1                    # 소스 1회 수집 → DB 저장
python -m app.cli list-contents --limit 20
python -m app.cli reclean-contents --dry-run   # 정제 규칙을 고친 뒤 저장된 글에 다시 적용 (--dry-run 빼면 적용)
python -m app.cli delete-content 6               # 콘텐츠 하나 삭제 (키워드 기록도 함께)

# DB 없이 수집만 (결과는 파일)

python cli.py keyword 태권도 국기원 --count 30 --days 3
python cli.py url https://site/a/1 https://site/b/2
python cli.py detect "<게시판 목록 URL>"
python cli.py board  "<게시판 목록 URL>" --page-param page --pages 2
```

`cli.py` 결과는 `backend/data/output/` 에 JSON·CSV 로, `app.cli` 결과는 `backend/data/app.db` 에 저장된다 (둘 다 git 에서 제외됨).

### 구조와 흐름

```
app/core/         config.py (환경변수, DISPLAY_TZ) · timeutil.py (UTC ↔ 표시 시간대) · logger.py
app/domain/       content.py — Article (파이프라인 값 객체)
app/collectors/   base.py (Collector 추상 클래스) · news.py · board.py · website.py
app/extractors/   article.py (다운로드·trafilatura 본문 추출) · cleaner.py (정제) · robots.py
app/processors/   deduplication.py · date_filter.py
app/url_collector/ fetcher.py (httpx → Playwright → Crawl4AI 3단계 fallback) · parser.py (게시판/단일 글 판별·본문 파싱) · cleaner.py
app/services/     collection_service.py — collect_keywords · collect_board · collect_urls
                  url_service.py — UrlCollectorService (fetcher·parser 로 URL 수집, /api/v1/scrape 가 부른다)
                  source_check_service.py — search_preview · detect_board · check_urls (저장 전 점검)
app/schemas/      Pydantic 요청·응답 (JSON 은 camelCase, frontend/lib/types.ts 와 맞춘다)
                  source_config.py — 소스 유형별 설정(sources.config) 검증
app/domain/enums.py  선택지 값 (DB 에는 문자열로 저장)
app/db/           engine.py (DATABASE_URL) · models.py (SQLModel 테이블) · types.py (UTCDateTime) · seed.py
app/repositories/ scope.py (워크스페이스 범위 select) · workspaces · sources · jobs · contents (save_collect_result)
alembic/          마이그레이션. 모델을 바꾸면 revision --autogenerate 후 확인·수정
app/api/          main.py (FastAPI 앱, 유일한 진입점) · deps.py · routes/ (라우터, 모든 경로는 /api 아래)
                  v1/scrape.py — POST /api/v1/scrape (라우터 prefix 는 /v1/scrape, main.py 가 /api 를 붙인다)
app/workers/      runner.py — run_source_once (job → collect_* → save_collect_result, 실패도 job 에 기록)
                  reclean.py — reclean_contents (저장된 원본을 지금 규칙으로 다시 정제, 짧아진 글은 지우지 않고 알림)
app/cli.py        DB CLI (add-news-source · run-source · list-contents · reclean-contents · delete-content)
```

수집기 `collect()` → 중복 제거·기간 필터·기수집 URL 제외 → 본문 추출 → 정제 → `CollectResult`.

### 지켜야 할 설계 원칙

- 수집기는 메타데이터(제목·URL·날짜)만 채운다. 본문 추출·정제는 서비스가 공통 처리한다.
  새 수집원은 `Collector` 를 상속해 `collect()` 만 구현한다 (요청 간격 등이 필요하면 `fetch()` 도).
- CLI·API·워커는 `services/`(수집)·`repositories/`(DB)·`workers/`(수집+저장) 함수만 호출한다. 수집기·추출기를 직접 부르지 않는다.
  수집과 저장을 묶는 곳은 `workers/runner.py` 하나다.
  라우트는 서비스 결과(`Article`·dataclass)를 `schemas/` 로 옮겨 담아 돌려준다.
- 서비스는 저장하지 않는다. 저장(파일·DB)은 호출하는 쪽의 책임이다. DB 저장은 `repositories/` 함수로 한다.
- `Article` 은 DB 모델이나 API 스키마가 아니다. DB/스키마가 생기면 별도 클래스로 옮겨 담는다.
- `body`(원본)와 `body_clean`(정제본)을 둘 다 유지한다.
- 유저별 값(키워드, 건수, 기간, 게시판 설정)은 `config.py` 가 아니라 함수 인자로 받는다.
- 시간대 규칙:
  - DB 에는 UTC 로 저장한다 (`UTCDateTime`).
  - 표시·집계·일정의 기준은 `DISPLAY_TZ`(기본 `Asia/Seoul`)이고, 변환은 `app/core/timeutil.py` 로만 한다.
    코드에 `+9시간` 같은 오프셋을 적지 않는다 (`tests/test_timezone.py` 가 검사한다).
  - API 응답의 시각은 DISPLAY_TZ 로 바꾼 오프셋 포함 ISO 8601 문자열이다.
    DB datetime 은 `schemas/base.DisplayDateTime`, 수집기 날짜 문자열은 `display_iso()` 를 쓴다.
  - 오늘·일별·최근 N일은 DISPLAY_TZ 날짜 기준이다. 기간은 날짜 경계를 UTC 로 바꿔 WHERE 에 쓰고
    (`days_to_utc_range`), 날짜별 묶기는 가져온 시각을 `display_date()` 로 바꿔 파이썬에서 한다.
    DB 의 시간대 함수(AT TIME ZONE, strftime 등)는 쓰지 않는다.
  - 소스의 `schedule_time` 은 DISPLAY_TZ 기준이다 (`schedule_at`, `next_daily_run`).
  - `config.KST` 는 수집 원본을 읽을 때만 쓴다. 시간대 표기가 없는 네이버·국내 게시판 날짜를 해석하는 용도이고, 표시용이 아니다.
- 수집 예절(게시판·URL 모두): `RESPECT_ROBOTS`, `BOARD_REQUEST_DELAY`, `BOARD_MAX_WORKERS` 를 우회하지 않는다.
- 테스트는 네트워크 없이 돌아가야 한다.

### DB 규칙

- **워크스페이스(테넌트) 격리가 최우선이다.** 워크스페이스에 속하는 테이블은 `WorkspaceScoped` 를 상속해
  `workspace_id` 를 직접 가진다 (조인해야 워크스페이스를 알 수 있는 구조 금지).
- 조회·수정은 `repositories/` 함수로만 하고, 모든 함수가 `workspace_id` 를 필수 인자로 받는다.
  select 는 `scope.scoped_select()` / `get_scoped()` 로 만든다. 다른 워크스페이스의 id 는 None(→ 404)으로 답한다.
- DB 를 쓰는 라우트는 `app/api/deps.py` 의 `get_current_workspace` · `get_session` 을 거친다
  (지금은 기본 워크스페이스, 인증을 붙이면 이 함수만 바꾼다).
- repository 는 flush 까지만 한다. 커밋은 라우트·워커가 한다.
- SQLite(개발)·PostgreSQL(운영) 공통 코드: 전용 타입(JSONB·ARRAY·네이티브 ENUM) 금지.
  선택지는 `str_enum()`, 시각은 `UTCDateTime`(UTC aware, naive 는 거부), JSON 은 `sa.JSON`.
- 콘텐츠는 워크스페이스 안에서 `url_hash`(canonical_url 의 sha256)로 한 번만 저장한다.
- 스키마를 바꾸면 마이그레이션을 함께 만든다 (`tests/test_migrations.py` 가 모델과 어긋나면 실패한다).
  마이그레이션 파일은 앱 코드를 import 하지 않고, 첫 줄(docstring)은 ASCII 로 쓴다. `alembic.ini` 도 ASCII 만.
- 코드 주석과 docstring 은 한국어로, 기존 스타일을 따른다.

## 프론트엔드 (Next.js)

- Next.js 16 **App Router** + **TypeScript** + Tailwind CSS 4. 위치는 `frontend/` 고정 (위 디렉터리 규칙 참고).
- Pages Router(`pages/`)는 쓰지 않는다. `.js`/`.jsx` 대신 `.ts`/`.tsx`.
- 화면 시안은 `docs/design/` (Claude Design). 구조·목업 사용법은 `frontend/README.md`.
- **API 호출은 `frontend/lib/api.ts` 한 곳에서만** 한다. 화면은 `lib/mock/` 을 직접 import 하지 않는다.
  백엔드에 있는 기능은 `NEXT_PUBLIC_API_MODE=live` 일 때 `/api/*` 를 부르고(`next.config.ts` 가
  `BACKEND_URL` 로 넘긴다), 없는 기능과 기본(mock) 모드는 목업을 돌려준다. 백엔드에 기능이 생기면
  `api.ts` 함수 본문만 `post()` 호출로 바꾸고 반환 타입은 유지한다.
- 색·폰트는 `app/globals.css` 의 `@theme` 토큰을 쓴다 (임의 hex 값 대신).
- 명령 (`frontend/` 에서): `npm run dev` · `npm run lint` · `npm run build`
