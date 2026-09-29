// API 호출은 모두 이 파일을 거친다. 화면·컴포넌트는 lib/mock 을 직접 부르지 않는다.
//
// 지금은 백엔드 API 가 없어(backend 는 cli.py 로만 동작) 목업(lib/mock/handlers.ts)을 지연과 함께 돌려준다.
// 내부 API Endpoint·Request/Response Schema 는 미확정이다. [API 확인 필요]
// FastAPI 가 생기면 각 함수 본문을 fetch 호출로 바꾸고, 반환 타입(lib/types.ts)은 유지한다.

import * as mock from "@/lib/mock/handlers";
import type {
  AdminDefault,
  AdminPageData,
  AnalysisOverview,
  AnalysisSettings,
  AnalysisParams,
  BoardDetectResult,
  BoardPostPreview,
  CollectResult,
  ContentDetail,
  ContentListParams,
  ContentListResult,
  DailyCount,
  DashboardData,
  DictKind,
  DictListParams,
  DictListResult,
  DictOrigin,
  JobListParams,
  JobRow,
  RelatedWord,
  SearchPreview,
  SettingsBundle,
  Source,
  SourceInput,
  SourceOption,
  SourceType,
  UrlCheckResult,
  User,
} from "@/lib/types";

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export type LoginResult = { ok: true; user: User } | { ok: false };

export const api = {
  // ── 인증 ── FN-AUTH-001. 세션·로그인 유지 정책 [정책 필요]

  async login(input: { email: string; password: string; keep: boolean }): Promise<LoginResult> {
    await wait(700);
    return mock.login(input.email, input.keep);
  },

  /** 현재 로그인한 사용자. 없으면 null */
  async getSession(): Promise<User | null> {
    return mock.getSession();
  },

  async logout(): Promise<void> {
    mock.logout();
  },

  // ── 대시보드 ── FN-DASH-001~005

  async getDashboard(): Promise<DashboardData> {
    await wait(400);
    return mock.getDashboard();
  },

  // ── 콘텐츠 ── FN-CNT-001~007

  /** 콘텐츠 목록 (필터·페이지). 필터는 서버에서 처리하는 것으로 가정 [API 확인 필요] */
  async listContents(params: ContentListParams): Promise<ContentListResult> {
    await wait(300);
    return mock.listContents(params);
  },

  /** 현재 필터 결과 전체 CSV (FN-CNT-002). 서버 생성 여부 [API 확인 필요] */
  async exportContents(params: Omit<ContentListParams, "page">): Promise<{ blob: Blob; count: number }> {
    await wait(300);
    const { csv, count } = mock.exportContentsCsv(params);
    return { blob: new Blob([csv], { type: "text/csv;charset=utf-8" }), count };
  },

  /** 콘텐츠 상세. 없으면 null (삭제된 글 처리 정책 [확인 필요]) */
  async getContent(id: string): Promise<ContentDetail | null> {
    await wait(300);
    return mock.getContent(id);
  },

  /** 글 하나를 현재 분석 설정으로 재분석 (FN-CNT-007) */
  async reanalyzeContent(id: string): Promise<ContentDetail | null> {
    await wait(1200);
    return mock.reanalyzeContent(id);
  },

  // ── 수집 소스 ── FN-SRC-001

  /** 수집 소스 목록. 유형 탭은 같은 표를 거르는 필터 */
  async listSources(type: "all" | SourceType = "all"): Promise<Source[]> {
    await wait(300);
    return mock.listSources(type);
  },

  /** 소스 하나 (편집 화면). 없으면 null */
  async getSource(id: string): Promise<Source | null> {
    await wait(300);
    return mock.getSource(id);
  },

  /** 소스 저장 — id 가 없으면 새로 만든다 (FN-SRC-010) [API 확인 필요] */
  async saveSource(input: SourceInput): Promise<Source> {
    await wait(700);
    return mock.saveSource(input);
  },

  /** 첫 키워드로 네이버 뉴스 검색 5건 미리보기 — 실제 호출은 서버 경유 (FN-SRC-003) [API 확인 필요] */
  async searchTest(keyword: string): Promise<SearchPreview[]> {
    await wait(900);
    return mock.searchTest(keyword);
  },

  /** robots.txt 확인 → 목록 수집 → 후보 묶음 (FN-SRC-004) [API 확인 필요] */
  async detectBoard(url: string): Promise<BoardDetectResult> {
    await wait(1100);
    return mock.detectBoard(url);
  },

  /** 후보 묶음으로 찾은 글 미리보기 (FN-SRC-005) */
  async boardPreview(url: string, candidateIndex: number): Promise<BoardPostPreview[]> {
    await wait(300);
    return mock.boardPreview(candidateIndex);
  },

  /** 주소별로 본문을 가져올 수 있는지 확인 (FN-SRC-007) */
  async checkUrls(urls: string[], minLen: number): Promise<UrlCheckResult[]> {
    await wait(1000);
    return mock.checkUrls(urls, minLen);
  },

  /** 필터 선택지용 소스 이름 목록 */
  async listSourceOptions(): Promise<SourceOption[]> {
    await wait(200);
    return mock.listSourceOptions();
  },

  // ── 키워드 분석 ── FN-ANL-001~007 [API 확인 필요]

  /** 핵심어 순위·급상승·키워드별 적중도 */
  async getAnalysis(params: AnalysisParams): Promise<AnalysisOverview> {
    await wait(400);
    return mock.getAnalysis(params);
  },

  /** 기준 소스·키워드로 모은 글에 함께 자주 나온 단어 (FN-ANL-004) */
  async getRelatedWords(sourceId: string, keyword: string): Promise<RelatedWord[]> {
    await wait(250);
    return mock.getRelatedWords(sourceId, keyword);
  },

  /** 연관어를 뉴스 소스의 검색 키워드로 추가 (FN-ANL-005) */
  async addSourceKeyword(sourceId: string, keyword: string): Promise<void> {
    await wait(400);
    mock.addSourceKeyword(sourceId, keyword);
  },

  /** 불용어 등록 (FN-ANL-005 · FN-DIC-001) */
  async addStopword(word: string): Promise<void> {
    await wait(400);
    mock.addStopword(word);
  },

  /** 일별 수집 건수 — 오래된 날부터 (FN-ANL-006) */
  async getDailyCounts(days: number): Promise<DailyCount[]> {
    await wait(250);
    return mock.getDailyCounts(days);
  },

  // ── 분석 설정 ── FN-SET-001~007 [API 확인 필요]

  /** scope: 'default'(내 기본값) 또는 소스 id */
  async getSettings(scope: string): Promise<SettingsBundle> {
    await wait(350);
    return mock.getSettings(scope);
  },

  /** 저장하면 판정만 새 기준으로 다시 계산한다 (수치는 그대로). 새 버전을 돌려준다 */
  async saveSettings(scope: string, settings: AnalysisSettings): Promise<AnalysisSettings> {
    await wait(700);
    return mock.saveSettings(scope, settings);
  },

  // ── 사전 ── FN-DIC-001~006 [API 확인 필요]

  /** 불용어·사용자 사전 목록 (검색·필터·정렬·50개씩) */
  async listDictionary(kind: DictKind, params: DictListParams): Promise<DictListResult> {
    await wait(250);
    return mock.listDictionary(kind, params);
  },

  /** 한 개·여러 개·CSV 가져오기 모두 이 함수로. 중복은 건너뛴다 */
  async addDictWords(
    kind: DictKind,
    words: { word: string; pos?: string }[],
    opts: { target: string; origin: DictOrigin; pos: string },
  ): Promise<{ added: number; skipped: number }> {
    await wait(300);
    return mock.addDictWords(kind, words, opts);
  },

  /** 적용 켜기·끄기 — 클릭 즉시 저장 [추정] */
  async setDictEnabled(kind: DictKind, ids: string[], on: boolean): Promise<void> {
    await wait(150);
    mock.setDictEnabled(kind, ids, on);
  },

  /** '시스템 공통' 단어는 관리자만 지울 수 있어, 권한이 없으면 skipped 로 돌아온다 */
  async deleteDictEntries(kind: DictKind, ids: string[]): Promise<{ deleted: number; skipped: number }> {
    await wait(300);
    return mock.deleteDictEntries(kind, ids);
  },

  /** 현재 필터 결과 CSV */
  async exportDictionary(kind: DictKind, params: Omit<DictListParams, "page">): Promise<Blob> {
    await wait(300);
    return new Blob([mock.exportDictionaryCsv(kind, params)], { type: "text/csv;charset=utf-8" });
  },

  /** 최근 30일 수집분 재분석 등록 — 30일 범위 선택 가능 여부 [확인 필요] */
  async reanalyzeRecent(): Promise<void> {
    await wait(1200);
    mock.reanalyzeRecent();
  },

  // ── 관리자 ── FN-ADM-001~007. 관리자가 아니면 거부된다 [API 확인 필요]

  /** 전체 사용량·작업 큐·핵심어·키워드 현황·시스템 기본값·공통 불용어 */
  async getAdminPage(): Promise<AdminPageData> {
    await wait(400);
    return mock.getAdminPage();
  },

  async saveAdminDefaults(rows: AdminDefault[]): Promise<AdminDefault[]> {
    await wait(600);
    return mock.saveAdminDefaults(rows);
  },

  /** 이미 있는 단어면 false */
  async addCommonStopword(word: string): Promise<boolean> {
    await wait(300);
    return mock.addCommonStopword(word);
  },

  async removeCommonStopword(id: string): Promise<void> {
    await wait(300);
    mock.removeCommonStopword(id);
  },

  // ── 수집 작업 ── FN-JOB-001~004

  async listJobs(params: JobListParams): Promise<JobRow[]> {
    await wait(300);
    return mock.listJobs(params);
  },

  /** 현재 필터 결과 CSV (FN-JOB-004) [API 확인 필요] */
  async exportJobs(params: JobListParams): Promise<{ blob: Blob; count: number }> {
    await wait(300);
    const { csv, count } = mock.exportJobsCsv(params);
    return { blob: new Blob([csv], { type: "text/csv;charset=utf-8" }), count };
  },

  // ── 수집 ── FN-COL-001

  /** 수집 작업 등록. sourceIds 를 생략하면 전체 소스. ("지금 수집" 대상 [확인 필요]) */
  async runCollect(sourceIds?: string[]): Promise<CollectResult> {
    await wait(300);
    return mock.runCollect(sourceIds);
  },
};
