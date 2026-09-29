# frontend

콘텐츠 수집 Agent 화면. Next.js 16 (App Router) · TypeScript · Tailwind CSS 4.
시안은 `../docs/design/` (Claude Design 프로젝트).

```bash
npm install
npm run dev      # http://localhost:3000
npm run lint
npm run build
```

## 구조

```
app/
  layout.tsx            폰트(IBM Plex Sans KR / Mono) · Toast · 확인 모달
  globals.css           디자인 토큰 (@theme) — 색·차트 색·모서리
  not-found.tsx         없는 주소
  login/                MEMBER-001 로그인
  (app)/                로그인 후 화면 — layout 이 COMMON-001 사이드바·로그인 확인
    page.tsx            MAIN-001 대시보드
    contents/           CONTENT-001 목록 · [id] CONTENT-002/003 상세 (?tab=raw)
    sources/            SOURCE-001 목록 · new · [id]/edit — SOURCE-002~005 폼 (_form/)
    jobs/               JOB-001 수집 작업
    analysis/           ANALYSIS-001 키워드 분석 (+P01 연관어 메뉴)
    settings/           SETTING-001 분석 설정
    dictionary/         SETTING-002 불용어 · SETTING-003 사용자 사전 (?tab=user)
    admin/              ADMIN-001 관리자 (멤버는 권한 없음 안내)
components/
  layout/               AppShell · 세션 컨텍스트
  ui/                   Button · Badge · Card · Table · Field · Pagination · Switch · StatCard ·
                        SegmentedTabs · UnderlineTabs · 상태(로딩·오류·빈·권한 없음) · Toast · Confirm
lib/
  api.ts                API 호출의 유일한 진입점 (지금은 목업)
  types.ts              응답 타입
  labels.ts             상태값 → 문구·배지 색
  use-api-data.ts       로딩·오류·새로고침·폴링 훅
  mock/                 목업 데이터·구현 — api.ts 만 import 한다
```

화면 파일마다 시안의 `data-screen-id` · `data-ui-id` · `data-func-id` 와 `[확인 필요]` · `[정책 필요]` 표시를 그대로 옮겨 두었다.
기획서(`../docs/design/spec.txt`)와 대조할 때 쓴다.

## 목업

백엔드 API 가 아직 없어 `lib/api.ts` 가 `lib/mock/` 의 데이터를 돌려준다. 새로고침하면 초기화된다.
아무 이메일·비밀번호로 로그인된다. 시안의 Tweaks 대신 URL 파라미터로 상태를 바꿔 본다 (탭을 닫을 때까지 유지).

| 파라미터 | 값 |
|---|---|
| `?data=` | `normal` · `empty` (빈 상태) · `error` (오류) |
| `?role=` | `member` · `admin` |
| `?login=` | `success` · `fail` (인증 실패) |
