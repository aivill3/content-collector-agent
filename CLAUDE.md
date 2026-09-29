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

- **아직 API 서버가 없다.** FastAPI 라우트·DB·워커는 만들어지지 않았고, 수집은
  `backend/cli.py` 로만 실행한다.
- 예정: `app/api/` (FastAPI), `app/db/` (SQLAlchemy), `app/schemas/` (Pydantic),
  `app/workers/`, `alembic/`, `docker-compose.yml`. 이 중 무언가를 추가하기 전에는
  사용자와 먼저 확인한다.

### 명령 (모두 `backend/` 에서 실행)

```bash
python -m venv .venv && .venv\Scripts\activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest                                  # 오프라인 테스트, 네트워크 불필요

python cli.py keyword 태권도 국기원 --count 30 --days 3
python cli.py url https://site/a/1 https://site/b/2
python cli.py detect "<게시판 목록 URL>"
python cli.py board  "<게시판 목록 URL>" --page-param page --pages 2
```

결과는 `backend/data/output/` 에 JSON·CSV 로 저장된다 (git 에서 제외됨).

### 구조와 흐름

```
app/core/         config.py (환경변수, KST) · logger.py
app/domain/       content.py — Article (파이프라인 값 객체)
app/collectors/   base.py (Collector 추상 클래스) · news.py · board.py · website.py
app/extractors/   article.py (다운로드·trafilatura 본문 추출) · cleaner.py (정제)
app/processors/   deduplication.py · date_filter.py
app/services/     collection_service.py — collect_keywords · collect_board · collect_urls
```

수집기 `collect()` → 중복 제거·기간 필터·기수집 URL 제외 → 본문 추출 → 정제 → `CollectResult`.

### 지켜야 할 설계 원칙

- 수집기는 메타데이터(제목·URL·날짜)만 채운다. 본문 추출·정제는 서비스가 공통 처리한다.
  새 수집원은 `Collector` 를 상속해 `collect()` 만 구현한다 (요청 간격 등이 필요하면 `fetch()` 도).
- CLI·향후 API·워커는 `services/collection_service.py` 의 함수만 호출한다. 수집기·추출기를 직접 부르지 않는다.
- 서비스는 저장하지 않는다. 저장(파일·DB)은 호출하는 쪽의 책임이다.
- `Article` 은 DB 모델이나 API 스키마가 아니다. DB/스키마가 생기면 별도 클래스로 옮겨 담는다.
- `body`(원본)와 `body_clean`(정제본)을 둘 다 유지한다.
- 유저별 값(키워드, 건수, 기간, 게시판 설정)은 `config.py` 가 아니라 함수 인자로 받는다.
- 시간은 KST(`app.core.config.KST`), 날짜 문자열은 ISO 8601.
- 게시판 수집 예절: `RESPECT_ROBOTS`, `BOARD_REQUEST_DELAY`, `BOARD_MAX_WORKERS` 를 우회하지 않는다.
- 테스트는 네트워크 없이 돌아가야 한다.
- 코드 주석과 docstring 은 한국어로, 기존 스타일을 따른다.

## 프론트엔드 (Next.js)

- Next.js 16 **App Router** + **TypeScript** + Tailwind CSS 4. 위치는 `frontend/` 고정 (위 디렉터리 규칙 참고).
- Pages Router(`pages/`)는 쓰지 않는다. `.js`/`.jsx` 대신 `.ts`/`.tsx`.
- 화면 시안은 `docs/design/` (Claude Design). 구조·목업 사용법은 `frontend/README.md`.
- **API 호출은 `frontend/lib/api.ts` 한 곳에서만** 한다. 화면은 `lib/mock/` 을 직접 import 하지 않는다.
  백엔드 API 가 없어 지금은 목업을 돌려주고, API 가 생기면 `api.ts` 함수 본문만 fetch 로 바꾼다.
- 색·폰트는 `app/globals.css` 의 `@theme` 토큰을 쓴다 (임의 hex 값 대신).
- 명령 (`frontend/` 에서): `npm run dev` · `npm run lint` · `npm run build`
