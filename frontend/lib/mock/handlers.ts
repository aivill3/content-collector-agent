// 목업 API 구현. lib/api.ts 만 이 파일을 부른다 — 화면에서 직접 import 하지 않는다.
// 브라우저 메모리에 저장소를 하나 두고 변경을 반영하므로, 새로고침하면 초기 데이터로 돌아간다.

import {
  createMockStore,
  emptyStore,
  mockDetect,
  mockSearchResults,
  type MockStore,
} from "@/lib/mock/data";
import { getScenario } from "@/lib/mock/scenario";
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
  DictEntry,
  DictKind,
  DictListParams,
  DictListResult,
  DictOrigin,
  Job,
  JobListParams,
  JobRow,
  RelatedWord,
  ScrapeResponse,
  ScrapeResult,
  SearchPreview,
  SettingsBundle,
  Source,
  SourceInput,
  SourceOption,
  SourceType,
  UrlCheckResult,
  User,
} from "@/lib/types";

/** 엑셀이 UTF-8 CSV 를 알아보도록 앞에 붙이는 표시 */
const BOM = String.fromCharCode(0xfeff);

let store: MockStore | null = null;

function db(): MockStore {
  store ??= createMockStore();
  return store;
}

/** 읽기용 — 시나리오의 '빈 상태'·'오류'를 반영한다. */
function view(): MockStore {
  const { data } = getScenario();
  if (data === "error") throw new Error("[MOCK] 데이터 상태: 오류");
  return data === "empty" ? emptyStore(db()) : db();
}

const pad = (n: number) => String(n).padStart(2, "0");
const nowStr = () => {
  const d = new Date();
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

// ── 인증 ── 세션·유지 정책 [정책 필요]

const SESSION_KEY = "cc.session";

export function login(email: string, keep: boolean): { ok: true; user: User } | { ok: false } {
  const sc = getScenario();
  if (sc.login === "fail") return { ok: false };
  const user: User = { name: email.split("@")[0] || "[사용자 이름]", role: sc.role };
  try {
    (keep ? localStorage : sessionStorage).setItem(SESSION_KEY, JSON.stringify(user));
  } catch {}
  return { ok: true, user };
}

export function getSession(): User | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY) ?? localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    // 역할은 시나리오(?role=)를 따른다 — 로그인 후에도 바꿔 볼 수 있게
    return { ...(JSON.parse(raw) as User), role: getScenario().role };
  } catch {
    return null;
  }
}

export function logout() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(SESSION_KEY);
  } catch {}
}

// ── 대시보드 ──

function toSummary(c: Content, sources: Source[]): ContentSummary {
  return {
    id: c.id, title: c.title, type: c.type, outlet: c.outlet, published: c.published,
    isNew: c.isNew, keyword: c.keyword, relevance: c.relevance, summary: c.summary,
    sourceName: sources.find((s) => s.id === c.sourceId)?.name ?? "",
  };
}

export function getDashboard(): DashboardData {
  const s = view();
  const byType = (t: SourceType) => s.sources.filter((x) => x.type === t).length;
  const recentOf = (t: "all" | SourceType) =>
    s.contents
      .filter((c) => t === "all" || c.type === t)
      .slice(0, 5)
      .map((c) => toSummary(c, s.sources));
  const sourceName = (id: string) => s.sources.find((x) => x.id === id)?.name ?? "—";

  return {
    summary: {
      todayCount: s.contents.filter((c) => c.daysAgo === 0).length,
      delta: s.dashboard.delta,
      sourceCounts: { total: s.sources.length, news: byType("news"), board: byType("board"), url: byType("url") },
      successRate: s.dashboard.successRate,
      failCount: s.jobs.filter((j) => j.status === "fail").length,
      nextTime: s.dashboard.nextTime,
      nextSource: s.dashboard.nextSource,
    },
    alerts: s.sources.filter((x) => x.status === "zero3").map((x) => ({ sourceId: x.id, name: x.name })),
    recent: { all: recentOf("all"), news: recentOf("news"), board: recentOf("board"), url: recentOf("url") },
    sources: s.sources.slice(0, 5).map(({ id, name, status, recentNew }) => ({ id, name, status, recentNew })),
    jobs: s.jobs.slice(0, 4).map((j) => ({ ...j, sourceName: sourceName(j.sourceId) })),
  };
}

// ── 콘텐츠 ── FN-CNT-001~007

const CONTENT_PAGE_SIZE = 8; // [확인 필요] 페이지당 건수

export function listSourceOptions(): SourceOption[] {
  return view().sources.map(({ id, name }) => ({ id, name }));
}

function filterContents(s: MockStore, p: Omit<ContentListParams, "page">): Content[] {
  const mode = s.settings.passingMode;
  const q = p.q.trim();
  return s.contents.filter((c) => {
    if (q && !`${c.title} ${c.summary}`.includes(q)) return false;
    if (p.sourceId !== "all" && c.sourceId !== p.sourceId) return false;
    if (p.period !== "all" && c.daysAgo >= Number(p.period)) return false;
    if (p.relevance !== "all" && c.relevance !== p.relevance) return false;
    // '스쳐 지나감' 숨김 설정이어도 그 관련도를 직접 고르면 보여 준다
    if (mode === "hide" && c.relevance === "passing" && p.relevance !== "passing") return false;
    return true;
  });
}

export function listContents(p: ContentListParams): ContentListResult {
  const s = view();
  const list = filterContents(s, p);
  const pageCount = Math.max(1, Math.ceil(list.length / CONTENT_PAGE_SIZE));
  const page = Math.min(Math.max(1, p.page), pageCount);
  return {
    items: list.slice((page - 1) * CONTENT_PAGE_SIZE, page * CONTENT_PAGE_SIZE).map((c) => toSummary(c, s.sources)),
    total: list.length,
    page,
    pageCount,
    passingMode: s.settings.passingMode,
    analyzed: true,
  };
}

/** 현재 필터 결과 전체를 CSV 로. 포함 열 [확인 필요] */
export function exportContentsCsv(p: Omit<ContentListParams, "page">): { csv: string; count: number } {
  const s = view();
  const list = filterContents(s, p);
  const REL = { main: "주제 기사", partial: "부분 언급", passing: "스쳐 지나감" } as const;
  const esc = (v: unknown) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
  const lines = [
    ["제목", "출처", "발행일", "수집 경로", "관련도", "URL"].map(esc).join(","),
    ...list.map((c) => [c.title, c.outlet, c.published, c.type, c.relevance ? REL[c.relevance] : "", c.url].map(esc).join(",")),
  ];
  return { csv: BOM + lines.join("\n"), count: list.length };
}

export function getContent(id: string): ContentDetail | null {
  const s = view();
  const content = s.contents.find((c) => c.id === id);
  if (!content) return null;
  const { version, metrics, topN, ttrWarn, denom, posRange, densTitle, minMentions } = s.settings;
  return { content, analyzed: true, settings: { version, metrics, topN, ttrWarn, denom, posRange, densTitle, minMentions } };
}

/** 글 하나를 현재 분석 설정으로 재분석 (FN-CNT-007) */
export function reanalyzeContent(id: string): ContentDetail | null {
  const s = db();
  s.contents = s.contents.map((c) => (c.id === id ? { ...c, analyzedVersion: s.settings.version, staleDict: false } : c));
  return getContent(id);
}

// ── 수집 소스 ── FN-SRC-001

export function listSources(type: "all" | SourceType): Source[] {
  return view().sources.filter((s) => type === "all" || s.type === type);
}

export function getSource(id: string): Source | null {
  return view().sources.find((s) => s.id === id) ?? null;
}

/** 새 소스면 id 를 만들고, 있으면 덮어쓴다. 대상 요약(target)은 서버가 만든다고 가정 (FN-SRC-010) */
export function saveSource(input: SourceInput): Source {
  const s = db();
  const prev = input.id ? s.sources.find((x) => x.id === input.id) : undefined;
  const urlCount = new Set((input.urls ?? "").split("\n").map((x) => x.trim()).filter(Boolean)).size;
  const target =
    input.type === "news"
      ? (input.keywords ?? []).map((k) => k.kw).join(", ")
      : input.type === "board"
        ? (input.boardUrl ?? "").replace(/^https?:\/\//, "")
        : `URL ${urlCount}개`;
  const saved: Source = {
    status: "idle", last: "", recentNew: null,
    ...prev,
    ...input,
    id: prev?.id ?? "S" + Date.now().toString(36),
    target,
  };
  s.sources = prev ? s.sources.map((x) => (x.id === saved.id ? saved : x)) : [...s.sources, saved];
  return saved;
}

export const searchTest = (keyword: string): SearchPreview[] => mockSearchResults(keyword);
export const detectBoard = (url: string): BoardDetectResult => mockDetect(url);

/** 주소별 확인. robots/blocked 가 들어간 주소나 네 번째 주소는 차단, 세 번째는 본문 짧음,
 *  /en/ 이 들어간 주소는 비한국어, fail 이 들어간 주소는 접속 실패로 재현 */
export function checkUrls(urls: string[], opts: { minLen: number; koreanOnly: boolean }): UrlCheckResult[] {
  return [...new Set(urls)].map((url, i): UrlCheckResult => {
    const none = { url, length: 0, title: "", outlet: "", date: "", excerpt: "" };
    if (/robots|blocked/.test(url) || i === 3) return { ...none, result: "robots" };
    if (/fail/.test(url)) return { ...none, result: "fail" };
    const length = i === 2 ? Math.max(0, opts.minLen - 8) : 1200 + i * 310;
    const page = {
      url,
      length,
      title: `샘플 글 제목 ${i + 1}`,
      outlet: url.replace(/^https?:\/\//, "").split("/")[0],
      date: `2026-09-${27 - i}T10:00:00+09:00`,
      excerpt: "샘플 본문 앞부분입니다. 실제 연결(NEXT_PUBLIC_API_MODE=live)에서는 정제된 본문의 첫 300자가 들어옵니다.",
    };
    if (length < opts.minLen) return { ...page, result: "short" };
    if (opts.koreanOnly && /\/en\//.test(url)) return { ...page, result: "foreign" };
    return { ...page, result: "ok" };
  });
}

/** URL 수집. 주소 모양으로 결과를 재현한다 — fail 이 들어가면 수집 실패, board·list 가 들어가면 게시판
 *  (하위 글 maxItemsPerBoard 건, 최대 12건), 그 밖에는 단일 글 */
export function scrapeUrls(urls: string[], opts: { maxItemsPerBoard?: number }): ScrapeResponse {
  const maxItems = Math.min(opts.maxItemsPerBoard ?? 10, 12);
  const results = urls.map((targetUrl, i): ScrapeResult => {
    const base = { targetUrl, errorMessage: null };
    if (/fail/.test(targetUrl)) {
      return { ...base, pageType: "unknown", tierUsed: "failed", articles: [], errorMessage: "All 3 fetch tiers failed" };
    }
    const article = (url: string, n: number, boardUrl: string | null) => ({
      url,
      title: `샘플 글 제목 ${n}`,
      body: `샘플 원본 본문 ${n}번입니다.\n\n광고·메뉴 같은 군더더기가 섞여 있을 수 있습니다.`,
      bodyClean: `샘플 정제 본문 ${n}번입니다. 실제 연결(NEXT_PUBLIC_API_MODE=live)에서는 정제된 본문 전체가 들어옵니다.`,
      published: `2026-09-${String(27 - (n % 20)).padStart(2, "0")}T10:00:00+09:00`,
      boardUrl,
    });
    if (/board|list/.test(targetUrl)) {
      const articles = Array.from({ length: maxItems }, (_, n) => article(`${targetUrl.replace(/\/$/, "")}/${n + 1}`, n + 1, targetUrl));
      return { ...base, pageType: "board", tierUsed: "httpx", articles };
    }
    return { ...base, pageType: "article", tierUsed: i % 2 ? "playwright" : "httpx", articles: [article(targetUrl, i + 1, null)] };
  });
  return {
    totalRequested: urls.length,
    totalArticles: results.reduce((sum, r) => sum + r.articles.length, 0),
    results,
  };
}

// ── 키워드 분석 ── FN-ANL-001~007

const pad2 = (n: number) => String(n).padStart(2, "0");
const todayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
};

/** MOCK: 소스 필터는 반영하지 않고, 30일은 7일 값에 4를 곱해 흉내 낸다 */
export function getAnalysis(p: AnalysisParams): AnalysisOverview {
  const s = view();
  const stop = new Set(s.stopwords.filter((x) => x.on).map((x) => x.word));
  const mult = p.period === "30" ? 4 : 1;
  const { preset, denom, posRange } = s.settings;
  return {
    basis: { preset, denom, posRange },
    // 불용어는 즉시 제외 (FN-ANL-001)
    core: s.analysis.core.filter((c) => !stop.has(c.w)).slice(0, 8).map((c) => ({ ...c, docs: c.docs * mult })),
    rising: s.analysis.rising.map((r) => ({ ...r, n: r.n * mult })),
    hit: s.analysis.hit.map((h) => ({ ...h, n: h.n * mult, warn: h.passing >= 50 })),
  };
}

export function getRelatedWords(sourceId: string, keyword: string): RelatedWord[] {
  const s = view();
  const src = s.sources.find((x) => x.id === sourceId);
  return (s.analysis.related[keyword] ?? []).map(([w, n]) => ({
    w, n,
    isKeyword: !!src?.keywords?.some((k) => k.kw === w),
    isStopword: s.stopwords.some((x) => x.word === w),
  }));
}

/** 연관어를 뉴스 소스의 검색 키워드로 추가 (FN-ANL-005) */
export function addSourceKeyword(sourceId: string, kw: string): Source | null {
  const s = db();
  const src = s.sources.find((x) => x.id === sourceId);
  if (!src || src.keywords?.some((k) => k.kw === kw)) return src ?? null;
  const keywords = [...(src.keywords ?? []), { kw, origin: "키워드 분석 연관어", added: todayStr(), recent: null }];
  const updated: Source = { ...src, keywords, target: keywords.map((k) => k.kw).join(", ") };
  s.sources = s.sources.map((x) => (x.id === sourceId ? updated : x));
  return updated;
}

/** 불용어 등록 — 대상은 내 기본값 (FN-ANL-005) */
export function addStopword(word: string): DictEntry {
  const s = db();
  const existing = s.stopwords.find((x) => x.word === word);
  if (existing) return existing;
  const entry: DictEntry = { id: "D" + Date.now().toString(36), word, origin: "키워드 분석에서 추가", target: "default", added: todayStr(), on: true };
  s.stopwords = [entry, ...s.stopwords];
  return entry;
}

export function getDailyCounts(days: number): DailyCount[] {
  return view().daily.slice(-days);
}

// ── 분석 설정 ── FN-SET-001~007

// 소스별 설정은 내 기본값과 따로 보관한다. 없으면 내 기본값을 시작값으로 보여 준다
// (제공 문서: 소스별 값은 바꾼 항목만 보관 — 여기서는 단순화해 통째로 보관) [API 확인 필요]
const sourceSettings = new Map<string, AnalysisSettings>();

// MOCK: 최근 7일 수집분의 1,000자당 밀도 분포 (0.25 단위 구간)
const DENSITY_BINS = [9, 7, 5, 4, 3, 5, 6, 7, 5, 4, 3, 2, 2, 1];

export function getSettings(scope: string): SettingsBundle {
  const s = view();
  const settings = (scope !== "default" && sourceSettings.get(scope)) || s.settings;
  return {
    scope,
    settings: structuredClone(settings),
    ranges: s.adminDefaults,
    dictCounts: { stopwords: s.stopwords.length, compounds: s.compounds.length },
    densityHistogram: { binWidth: 0.25, counts: DENSITY_BINS },
  };
}

export function saveSettings(scope: string, next: AnalysisSettings): AnalysisSettings {
  const s = db();
  const prev = (scope !== "default" && sourceSettings.get(scope)) || s.settings;
  const saved = { ...next, version: prev.version + 1 };
  if (scope === "default") {
    s.settings = saved;
    s.savedSettings = structuredClone(saved);
  } else {
    sourceSettings.set(scope, saved);
    s.sources = s.sources.map((x) => (x.id === scope ? { ...x, analysis: "custom" } : x));
  }
  return saved;
}

// ── 사전 ── FN-DIC-001~006

const DICT_PAGE_SIZE = 50;

function filterDict(list: DictEntry[], p: Omit<DictListParams, "page">): DictEntry[] {
  const q = p.q.trim();
  let out = list.filter(
    (x) => (!q || x.word.includes(q)) && (p.origin === "all" || x.origin === p.origin) && (p.target === "all" || x.target === p.target),
  );
  // 목록은 최근 추가순으로 쌓여 있다
  if (p.sort === "old") out = [...out].reverse();
  if (p.sort === "abc") out = [...out].sort((a, b) => a.word.localeCompare(b.word, "ko"));
  return out;
}

export function listDictionary(kind: DictKind, p: DictListParams): DictListResult {
  const s = view();
  const list = filterDict(s[kind], p);
  const pageCount = Math.max(1, Math.ceil(list.length / DICT_PAGE_SIZE));
  const page = Math.min(Math.max(1, p.page), pageCount);
  return {
    items: list.slice((page - 1) * DICT_PAGE_SIZE, page * DICT_PAGE_SIZE),
    total: list.length,
    page,
    pageCount,
    counts: { stopwords: s.stopwords.length, compounds: s.compounds.length },
    pendingCount: s.compounds.filter((x) => x.pending).length,
  };
}

/** 여러 단어 추가 — 이미 있는 단어와 입력 안의 중복은 건너뛴다 [추정] */
export function addDictWords(
  kind: DictKind,
  words: { word: string; pos?: string }[],
  opts: { target: string; origin: DictOrigin; pos: string },
): { added: number; skipped: number } {
  const s = db();
  const existing = new Set(s[kind].map((x) => x.word));
  const stamp = Date.now().toString(36);
  const items: DictEntry[] = [];
  for (const w of words) {
    const word = w.word.trim();
    if (!word || existing.has(word)) continue;
    existing.add(word);
    items.push({
      id: `D${stamp}${items.length}`, word, origin: opts.origin, target: opts.target, added: todayStr(), on: true,
      // 사용자 사전은 재분석 전까지 기존 글에 반영되지 않는다
      ...(kind === "compounds" ? { pos: w.pos || opts.pos, pending: true } : {}),
    });
  }
  s[kind] = [...items, ...s[kind]];
  return { added: items.length, skipped: words.length - items.length };
}

/** 적용 켜기·끄기 (FN-DIC-004) */
export function setDictEnabled(kind: DictKind, ids: string[], on: boolean) {
  const s = db();
  const set = new Set(ids);
  s[kind] = s[kind].map((x) => (set.has(x.id) ? { ...x, on, ...(kind === "compounds" ? { pending: true } : {}) } : x));
}

/** 삭제 (FN-DIC-005). '시스템 공통'은 관리자만 지울 수 있다 (와이어프레임) */
export function deleteDictEntries(kind: DictKind, ids: string[]): { deleted: number; skipped: number } {
  const s = db();
  const admin = getScenario().role === "admin";
  const set = new Set(ids);
  const removable = new Set(s[kind].filter((x) => set.has(x.id) && (admin || x.origin !== "시스템 공통")).map((x) => x.id));
  s[kind] = s[kind].filter((x) => !removable.has(x.id));
  return { deleted: removable.size, skipped: ids.length - removable.size };
}

export function exportDictionaryCsv(kind: DictKind, p: Omit<DictListParams, "page">): string {
  const s = view();
  const name = (id: string) => (id === "default" ? "내 기본값" : (s.sources.find((x) => x.id === id)?.name ?? id));
  const esc = (v: unknown) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
  const comp = kind === "compounds";
  const head = comp ? ["복합어", "품사", "출처", "적용 대상", "추가일", "적용"] : ["단어", "출처", "적용 대상", "추가일", "적용"];
  const rows = filterDict(s[kind], p).map((x) =>
    (comp ? [x.word, x.pos, x.origin, name(x.target), x.added, x.on ? "Y" : "N"] : [x.word, x.origin, name(x.target), x.added, x.on ? "Y" : "N"])
      .map(esc)
      .join(","),
  );
  return BOM + [head.map(esc).join(","), ...rows].join("\n");
}

/** 최근 30일 수집분 재분석 등록 (FN-DIC-006 · FN-CNT-007) */
export function reanalyzeRecent() {
  const s = db();
  s.compounds = s.compounds.map((x) => ({ ...x, pending: false }));
  s.contents = s.contents.map((c) => ({ ...c, staleDict: false }));
}

// ── 관리자 ── FN-ADM-001~007

function requireAdmin() {
  if (getScenario().role !== "admin") throw new Error("[MOCK] 403 관리자만 접근할 수 있습니다");
}

export function getAdminPage(): AdminPageData {
  requireAdmin();
  const s = view();
  return {
    ...s.admin,
    defaults: s.adminDefaults,
    commonStopwords: s.stopwords.filter((x) => x.origin === "시스템 공통"),
  };
}

/** 신규 유저·아직 값을 바꾸지 않은 유저에게 적용되는 범위 [확인 필요] */
export function saveAdminDefaults(rows: AdminDefault[]): AdminDefault[] {
  requireAdmin();
  const s = db();
  s.adminDefaults = rows;
  return rows;
}

/** 공통 불용어 추가 — 이미 있으면 false */
export function addCommonStopword(word: string): boolean {
  requireAdmin();
  return addDictWords("stopwords", [{ word }], { target: "default", origin: "시스템 공통", pos: "" }).added > 0;
}

export function removeCommonStopword(id: string) {
  requireAdmin();
  deleteDictEntries("stopwords", [id]);
}

// ── 수집 작업 ── FN-JOB-001~004

function filterJobs(s: MockStore, p: JobListParams): JobRow[] {
  // 기간(p.period)은 적용하지 않는다 — MOCK 작업 시각에 연도가 없고 모두 최근 7일 이내다
  return s.jobs
    .filter((j) => (p.sourceId === "all" || j.sourceId === p.sourceId) && (p.status === "all" || j.status === p.status))
    .map((j) => {
      const src = s.sources.find((x) => x.id === j.sourceId);
      return { ...j, sourceName: src?.name ?? "—", sourceType: src?.type ?? null };
    });
}

export function listJobs(p: JobListParams): JobRow[] {
  return filterJobs(view(), p);
}

export function exportJobsCsv(p: JobListParams): { csv: string; count: number } {
  const list = filterJobs(view(), p);
  const STATUS = { success: "성공", fail: "실패", running: "실행 중", queued: "대기" } as const;
  const esc = (v: unknown) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
  const lines = [
    ["실행 시각", "소스", "방식", "소요(초)", "상태", "수집"].map(esc).join(","),
    ...list.map((j) => [j.time, j.sourceName, j.mode, j.dur, STATUS[j.status], j.count].map(esc).join(",")),
  ];
  return { csv: BOM + lines.join("\n"), count: list.length };
}

// ── 수집 실행 ── FN-COL-001
// 대기 → (1초) 실행 중 → (2.8초) 성공/실패. 서버 멱등성 [API 확인 필요] — 여기서는 이미 대기·실행 중인 소스만 건너뛴다.

export function runCollect(sourceIds: string[] | undefined, mode: Job["mode"] = "수동"): CollectResult {
  const s = db();
  const ids = sourceIds ?? s.sources.map((x) => x.id);
  const targets = s.sources.filter((x) => ids.includes(x.id) && x.status !== "queued" && x.status !== "running");
  const stamp = Date.now().toString(36);
  const jobIds = targets.map((_, i) => `J${stamp}${i}`);

  const patchSource = (id: string, patch: Partial<Source>) => {
    s.sources = s.sources.map((x) => (x.id === id ? { ...x, ...patch } : x));
  };
  const patchJob = (id: string, patch: Partial<Job>) => {
    s.jobs = s.jobs.map((j) => (j.id === id ? { ...j, ...patch } : j));
  };

  const newJobs: Job[] = targets.map((src, i) => ({
    id: jobIds[i], time: nowStr(), sourceId: src.id, mode, dur: null, status: "queued", count: null,
  }));
  s.jobs = [...newJobs, ...s.jobs];

  targets.forEach((src, i) => {
    const jid = jobIds[i];
    const prevStatus = src.status;
    patchSource(src.id, { status: "queued" });

    setTimeout(() => {
      patchSource(src.id, { status: "running" });
      patchJob(jid, { status: "running" });
    }, 1000);

    setTimeout(() => {
      // MOCK: 기존에 0건/robots 상태였던 소스는 실패로 재현
      const fail = prevStatus === "zero3" || prevStatus === "robots";
      const count = fail ? 0 : 1 + Math.floor(Math.random() * 8);
      if (fail) {
        patchJob(jid, {
          status: "fail", count: 0, dur: 4,
          reason:
            prevStatus === "robots"
              ? "robots.txt가 이 경로의 수집을 허용하지 않습니다."
              : "목록 페이지에서 글을 찾지 못했습니다. 자바스크립트로 목록을 그리는 게시판이거나 선택자가 맞지 않습니다.",
        });
      } else {
        patchJob(jid, {
          status: "success", count, dur: 6 + Math.floor(Math.random() * 12),
          stages: { search: count * 5, dedup: count * 4, period: count * 2, fresh: count + 1, body: count + 1, clean: count },
        });
      }
      patchSource(src.id, { status: fail ? prevStatus : "success", last: nowStr(), recentNew: count });
    }, 2800);
  });

  return { jobIds, queued: targets.length, skipped: ids.length - targets.length };
}
