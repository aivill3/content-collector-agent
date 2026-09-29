# content-collector-agent

키워드 뉴스 수집, 게시판 수집, 글 URL 수집을 하는 콘텐츠 수집 AI Agent.
수집·본문 추출·정제 로직은 [taekwonw-agent](https://github.com/aivill3/taekwonw-agent)에서 이식했다.

## 구조

```
backend/
  app/
    core/          config.py (환경변수) · logger.py
    collectors/    base.py (공통 인터페이스) · news.py · board.py · website.py
    extractors/    article.py (다운로드·본문 추출) · cleaner.py (정제)
    processors/    deduplication.py · date_filter.py
    domain/        content.py (파이프라인용 Article)
    services/      collection_service.py (collect_keywords · collect_board · collect_urls)
  tests/           오프라인 테스트
  cli.py           API 없이 수집 확인
frontend/          Next.js 16 (App Router) · TypeScript · Tailwind — 화면 12개, 지금은 목업 데이터
  app/             화면 (로그인 · 대시보드 · 콘텐츠 · 수집 소스·작업 · 키워드 분석 · 분석 설정 · 사전 · 관리자)
  lib/api.ts       API 호출의 유일한 진입점 — 백엔드 API 가 생기면 이 파일만 바꾼다
docs/
  design/          Claude Design 화면 시안 (*.dc.html) · 와이어프레임 (uploads/) · 기획서 (spec.txt)
```

흐름: 수집기(`collectors/`)가 메타데이터만 채운 Article 목록을 만들고, 서비스가 본문 추출 → 정제 → 필터를 공통으로 처리한다.

백엔드는 아직 API 가 없고 `cli.py` 로만 동작한다. 프론트엔드는 `frontend/lib/mock/` 의 목업으로 화면을 보여 준다.

예정: `api/` (FastAPI 라우트), `db/` (SQLAlchemy 모델), `schemas/` (Pydantic), `workers/` (수집 작업), `alembic/`, `docker-compose.yml`

## 시작 — 백엔드

```bash
cp .env.example .env          # 네이버 API 키 입력 (저장소 루트)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest              # 네트워크 없이 확인
```

## 사용 (backend/ 에서)

```bash
python cli.py keyword 태권도 국기원 --count 30 --days 3
python cli.py url https://사이트/글/1 https://사이트/글/2
python cli.py detect "https://사이트/bbs/board.php?bo_table=notice"
python cli.py board  "https://사이트/bbs/board.php?bo_table=notice" --page-param page --pages 2
python cli.py board  "https://사이트/bbs/board.php?bo_table=notice" \
    --item "#bo_list tbody tr" --link "td.td_subject a" --body "#bo_v_con" --exclude-notice
```

결과는 `backend/data/output/` 에 JSON·CSV 로 저장된다.

## 시작 — 프론트엔드

```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000 — 아무 이메일·비밀번호로 로그인
```

목업 상태 바꾸기(`?data=empty`, `?role=admin` 등)와 폴더 구성은 [frontend/README.md](frontend/README.md) 참고.

## 게시판 수집의 한계

- 자바스크립트로 목록을 그리는 게시판은 0건이 나온다. `collectors/board.py` 의 `fetch_list_html()` 에 Playwright 를 붙이면 된다.
- 로그인이 필요한 게시판은 대상이 아니다.
- `RESPECT_ROBOTS=true`(기본)이면 robots.txt 가 막은 경로는 받지 않는다.
