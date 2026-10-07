// API 호출은 모두 이 파일을 거친다. 화면·컴포넌트는 lib/mock 을 직접 부르지 않는다.
//
// 백엔드(FastAPI, backend/app/api/)가 있는 기능은 NEXT_PUBLIC_API_MODE=live 일 때 /api/* 를 부른다
// (next.config.ts 가 백엔드로 넘긴다). 그 밖의 기능과 mock 모드는 목업(lib/mock/handlers.ts)을 지연과 함께 돌려준다.
// 연결된 기능: 소스 점검 3개 (searchTest · detectBoard · checkUrls) · 콘텐츠 목록·상세·CSV · 소스 선택지
// 나머지 Endpoint·Request/Response Schema 는 미확정이다. [API 확인 필요]
// 백엔드가 생기면 각 함수 본문을 post/get 호출로 바꾸고, 반환 타입(lib/types.ts)은 유지한다.

import * as mock from "@/lib/mock/handlers";
import type {
  AdminDefault,
  AdminPageData,
  AnalysisOverview,
  AnalysisSettings,
  AnalysisParams,
  BoardDetectResult,
  CollectResult,
  Content,
  ContentDetail,
  ContentListParams,
  ContentListResult,
  ContentSummary,
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

/** live: 연결된 기능은 백엔드를 부른다 · mock(기본): 전부 목업 */
const LIVE = process.env.NEXT_PUBLIC_API_MODE === "live";

/** 백엔드가 거절했거나 닿지 않았다. message 는 화면에 그대로 보여 줄 수 있는 문장이다 */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

/** 화면의 오류 문구 — 백엔드가 알려 준 사유가 있으면 그것을, 없으면 fallback */
export const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);

async function send<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError("서버에 연결하지 못했습니다", 0);
  }
  if (!res.ok) throw new ApiError(await failReason(res), res.status);
  return (await res.json()) as T;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return send(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

/** 값이 없는(undefined·빈 문자열) 쿼리는 빼고 보낸다 */
function get<T>(path: string, query: Record<string, string | number | undefined> = {}): Promise<T> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== "") qs.set(k, String(v));
  return send(qs.size ? `${path}?${qs}` : path);
}

/** FastAPI 오류 본문 { detail } → 문장. detail 은 문자열이거나 입력 검증 오류 목록이다 */
async function failReason(res: Response): Promise<string> {
  const body: unknown = await res.json().catch(() => null);
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return `입력값을 확인하세요 (${detail[0].msg})`;
  // JSON 이 아닌 5xx 는 Next 프록시가 백엔드에 닿지 못한 경우다
  return res.status >= 500 ? "백엔드 서버에 연결하지 못했습니다" : `요청이 거절되었습니다 (${res.status})`;
}

// ── 백엔드 응답 → 화면 타입 ──
// 백엔드 형식(backend/app/schemas/)은 여기서만 다룬다. 화면은 lib/types.ts 의 타입만 본다.

/** backend/app/schemas/contents.py ContentListItem */
interface BackendContentItem {
  id: number;
  title: string;
  url: string;
  publisher: string;
  summary: string; // 검색 API 설명 (정제 안 됨)
  excerpt: string; // 정제 본문 앞부분
  collectionPath: "naver" | "board" | "website";
  sourceId: number;
  sourceName: string;
  publishedAt: string | null; // DISPLAY_TZ ISO 8601 (오프셋 포함)
  collectedAt: string;
  keywords: string[];
  bodyLength: number;
}

interface BackendContentList {
  items: BackendContentItem[];
  total: number;
  page: number;
  size: number;
  pageCount: number;
}

interface BackendContentDetail extends BackendContentItem {
  boardUrl: string;
  firstJobId: number;
  cleanedBody: string;
  rawBody: string;
  hits: { keyword: string; rank: number; jobId: number; foundAt: string }[];
}

const PATH_TYPE: Record<BackendContentItem["collectionPath"], SourceType> = { naver: "news", board: "board", website: "url" };

const CONTENT_PAGE_SIZE = 20;
const EXPORT_PAGE_SIZE = 100; // 백엔드 한 페이지 상한 (MAX_PAGE_SIZE)

/** 백엔드 시각은 이미 표시 시간대다 — 브라우저 시간대로 바꾸지 않고 글자만 자른다. '2026-09-30T14:20:00+09:00' → '2026-09-30 14:20' */
const displayTime = (iso: string | null) => (iso ? iso.slice(0, 16).replace("T", " ") : "");

const toParagraphs = (text: string) => text.split(/\n+/).map((p) => p.trim()).filter(Boolean);

function toContentSummary(c: BackendContentItem): ContentSummary {
  return {
    id: String(c.id),
    title: c.title,
    type: PATH_TYPE[c.collectionPath],
    outlet: c.publisher,
    published: displayTime(c.publishedAt),
    isNew: false,
    keyword: c.keywords[0] ?? null,
    relevance: null, // 키워드 관련도 분석은 백엔드에 아직 없다
    // 목록의 요약 줄은 정제 본문 앞부분 — 검색 API 설명은 정제되지 않아 사진 캡션·바이라인이 섞인다
    summary: c.excerpt || c.summary,
    sourceName: c.sourceName,
  };
}

/** 분석 필드는 빈 값으로 채운다 — ContentDetail.analyzed=false 라 화면이 쓰지 않는다 */
function toContent(c: BackendContentDetail): Content {
  return {
    ...toContentSummary(c),
    url: c.url,
    sourceId: String(c.sourceId),
    collected: displayTime(c.collectedAt),
    daysAgo: 0,
    mentions: 0,
    density: 0,
    titleHas: false,
    length: c.bodyLength,
    metrics: { tokens: 0, unique: 0, nouns: 0, sentences: 0, avgLen: 0, ttr: 0 },
    topWords: [],
    analyzedVersion: 0,
    staleDict: false,
    paragraphs: toParagraphs(c.cleanedBody),
    removed: [],
    rawBody: c.rawBody,
    hits: c.hits.map((h) => ({ keyword: h.keyword, rank: h.rank, foundAt: displayTime(h.foundAt) })),
  };
}

/** 화면 필터 → GET /api/contents 쿼리. 관련도 필터는 백엔드에 없어 보내지 않는다 (목록이 analyzed=false 로 감춘다) */
function contentQuery(p: Omit<ContentListParams, "page">) {
  return {
    q: p.q.trim(),
    sourceId: p.sourceId === "all" ? undefined : p.sourceId,
    days: p.period === "all" ? undefined : p.period,
  };
}

const CSV_BOM = "﻿"; // 엑셀이 UTF-8 로 읽게
const csvCell = (v: unknown) => '"' + String(v ?? "").replace(/"/g, '""') + '"';

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
    if (LIVE) {
      const r = await get<BackendContentList>("/contents", { ...contentQuery(params), page: params.page, size: CONTENT_PAGE_SIZE });
      return {
        items: r.items.map(toContentSummary),
        total: r.total,
        page: r.page,
        pageCount: Math.max(1, r.pageCount),
        passingMode: "show",
        analyzed: false,
      };
    }
    await wait(300);
    return mock.listContents(params);
  },

  /** 현재 필터 결과 전체 CSV (FN-CNT-002). 서버 생성 여부 [API 확인 필요] */
  async exportContents(params: Omit<ContentListParams, "page">): Promise<{ blob: Blob; count: number }> {
    if (LIVE) {
      // 백엔드에 CSV 기능이 없어 목록을 끝까지 받아 여기서 만든다. 열은 목업과 같다
      const rows: BackendContentItem[] = [];
      for (let page = 1; ; page++) {
        const r = await get<BackendContentList>("/contents", { ...contentQuery(params), page, size: EXPORT_PAGE_SIZE });
        rows.push(...r.items);
        if (page >= r.pageCount) break;
      }
      const lines = [
        ["제목", "출처", "발행일", "수집 경로", "관련도", "URL"].map(csvCell).join(","),
        ...rows.map((c) => [c.title, c.publisher, displayTime(c.publishedAt), PATH_TYPE[c.collectionPath], "", c.url].map(csvCell).join(",")),
      ];
      return { blob: new Blob([CSV_BOM + lines.join("\n")], { type: "text/csv;charset=utf-8" }), count: rows.length };
    }
    await wait(300);
    const { csv, count } = mock.exportContentsCsv(params);
    return { blob: new Blob([csv], { type: "text/csv;charset=utf-8" }), count };
  },

  /** 콘텐츠 상세. 없으면 null (삭제된 글 처리 정책 [확인 필요]) */
  async getContent(id: string): Promise<ContentDetail | null> {
    if (LIVE) {
      if (!/^\d+$/.test(id)) return null; // 백엔드 id 는 숫자다 (목업 id 로 들어온 주소)
      try {
        return { content: toContent(await get<BackendContentDetail>(`/contents/${id}`)), analyzed: false };
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    }
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

  /** 키워드 하나로 네이버 뉴스 검색 5건 미리보기 — 네이버 키는 서버에만 있다 (FN-SRC-003) */
  async searchTest(keyword: string): Promise<SearchPreview[]> {
    if (LIVE) return post("/source-checks/search", { keyword });
    await wait(900);
    return mock.searchTest(keyword);
  },

  /** robots.txt 확인 → 목록 페이지 → 후보 묶음과 묶음별 글 미리보기 (FN-SRC-004·005) */
  async detectBoard(url: string): Promise<BoardDetectResult> {
    if (LIVE) return post("/source-checks/board", { url });
    await wait(1100);
    return mock.detectBoard(url);
  },

  /** 주소별로 본문을 가져올 수 있는지 확인 (FN-SRC-007). 한 번에 20개까지 */
  async checkUrls(urls: string[], opts: { minLen: number; koreanOnly: boolean }): Promise<UrlCheckResult[]> {
    if (LIVE) return post("/source-checks/urls", { urls, ...opts });
    await wait(1000);
    return mock.checkUrls(urls, opts);
  },

  /** 필터 선택지용 소스 이름 목록 */
  async listSourceOptions(): Promise<SourceOption[]> {
    if (LIVE) {
      const opts = await get<{ id: number; name: string }[]>("/sources/options");
      return opts.map((o) => ({ id: String(o.id), name: o.name }));
    }
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
