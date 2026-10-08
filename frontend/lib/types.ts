// 화면에서 쓰는 데이터 타입.
// 백엔드 API·DB 스키마가 아직 없어 docs/design/mock/data.js 구조를 그대로 옮겼다. [API 확인 필요]
// API 가 생기면 응답 스키마에 맞춰 이 파일을 고친다.

export type SourceType = "news" | "board" | "url";
export type SourceStatus = "success" | "zero3" | "robots" | "idle" | "queued" | "running";
export type Schedule = "manual" | "hourly" | "daily" | "weekly" | "cron";
export type Relevance = "main" | "partial" | "passing";
export type JobStatus = "queued" | "running" | "success" | "fail";
export type JobMode = "정기" | "수동";
export type Role = "member" | "admin";

export interface User {
  name: string;
  role: Role;
}

export interface SourceKeyword {
  kw: string;
  origin: string;
  added: string; // YYYY-MM-DD
  recent: number | null; // 최근 수집 건수, 새로 추가해 아직 수집 전이면 null
}

/** 수집 소스. 유형별 필드는 선택 값으로 둔다 (폼에서 유형을 바꿔도 값이 유지되도록). */
export interface Source {
  id: string;
  name: string;
  type: SourceType;
  target: string; // 목록에 보이는 대상 요약
  schedule: Schedule;
  time: string; // HH:mm
  cron: string;
  last: string; // MM-DD HH:mm, 수집 전이면 빈 값
  status: SourceStatus;
  analysis: "default" | "custom";
  recentNew: number | null; // 마지막 수집의 신규 글 수, 수집 전이면 null
  nonKorean: boolean;
  // 뉴스
  keywords?: SourceKeyword[];
  count?: number;
  sort?: "sim" | "date";
  period?: string;
  // 게시판
  boardUrl?: string;
  pageParam?: string;
  pages?: number;
  maxPosts?: number;
  urlPattern?: string;
  boardPeriod?: string;
  skipNotice?: boolean;
  /** 자동 탐지에서 채택한 링크 묶음 패턴 */
  listPattern?: string;
  /** 수동 설정에서 페이지를 보며 고른 선택자 [API 확인 필요] */
  selectors?: BoardSelectors;
  // 게시판 · URL
  minLen?: number;
  // URL (줄바꿈으로 구분)
  urls?: string;
}

export interface BoardSelectors {
  row: string; // 목록 한 줄
  link: string; // 글 링크
}

/** 소스 저장 요청 — 상태·대상 요약은 서버가 채운다 */
export type SourceInput = Omit<Source, "id" | "status" | "last" | "recentNew" | "target"> & { id?: string };

/** 뉴스 검색 테스트 결과 한 줄 (FN-SRC-003) */
export interface SearchPreview {
  title: string;
  url: string;
  /** 언론사 — 네이버 검색 결과에 없어 기사 주소의 도메인으로 대신한다 */
  outlet: string;
  date: string; // ISO 8601, 모르면 빈 값
  keyword: string;
}

/** 게시판 자동 탐지 결과 (FN-SRC-004). 목록 페이지를 한 번만 받아 후보마다 미리보기까지 담는다 */
export interface BoardDetectResult {
  robots: boolean; // robots.txt 허용
  httpOk: boolean; // 목록 페이지 응답 정상 (robots 차단이면 요청하지 않아 false)
  /** 글 번호만 다른 링크가 많이 반복된 순서 */
  candidates: BoardCandidate[];
}

export interface BoardCandidate {
  pattern: string; // URL 모양 — 채택하면 Source.listPattern 으로 저장
  links: number;
  posts: BoardPostPreview[]; // 앞쪽 몇 건 (FN-SRC-005)
}

export interface BoardPostPreview {
  title: string;
  date: string; // ISO 8601, 목록에서 못 읽으면 빈 값
  url: string;
}

/** URL 확인 결과 (FN-SRC-007) — 실제 수집과 같은 규칙(robots → 본문 추출 → 정제 → 길이·언어)으로 판정 */
export interface UrlCheckResult {
  url: string;
  result: "ok" | "short" | "foreign" | "robots" | "fail";
  length: number; // 정제 후 본문 길이 (자)
  title: string;
  outlet: string;
  date: string; // ISO 8601, 모르면 빈 값
  excerpt: string; // 정제 본문 앞부분
}

// ── URL 수집 (POST /api/v1/scrape) — backend/app/schemas/scrape.py 와 맞춘다. 저장하지 않는다 ──

/** 주소가 가리키는 페이지 유형 — 서버가 자동 감지한다 */
export type ScrapePageType = "article" | "board" | "unknown";

/** 본문을 받는 데 쓴 엔진 (httpx → playwright → crawl4ai 순서로 시도). 모두 실패하면 failed */
export type ScrapeTier = "httpx" | "playwright" | "crawl4ai" | "failed";

export interface ScrapedArticle {
  url: string;
  title: string;
  body: string; // 원본
  bodyClean: string; // 정제본
  published: string | null; // ISO 8601, 모르면 빈 값
  boardUrl: string | null; // 게시판 하위 글이면 목록 주소
}

/** 주소 하나의 수집 결과. 실패해도 HTTP 오류가 아니라 tierUsed === "failed" 로 온다 */
export interface ScrapeResult {
  targetUrl: string;
  pageType: ScrapePageType;
  tierUsed: ScrapeTier;
  articles: ScrapedArticle[]; // 단일 글은 1건, 게시판은 하위 글 (최대 maxItemsPerBoard)
  errorMessage: string | null; // 서버 원문(영문) — 화면에는 tierUsed 로 문구를 만들어 쓴다
}

export interface ScrapeResponse {
  totalRequested: number;
  totalArticles: number;
  results: ScrapeResult[];
}

export interface TopWord {
  w: string;
  pos: string;
  n: number;
  d: number;
}

export interface RemovedBlock {
  after: number; // 몇 번째 문단 뒤에서 제거됐는지
  reason: string;
  text: string;
}

export interface ContentMetrics {
  tokens: number;
  unique: number;
  nouns: number;
  sentences: number;
  avgLen: number;
  ttr: number;
}

export interface Content {
  id: string;
  title: string;
  url: string;
  sourceId: string;
  type: SourceType;
  outlet: string; // 언론사 / 사이트명
  published: string; // YYYY-MM-DD HH:mm
  collected: string;
  daysAgo: number;
  isNew: boolean;
  keyword: string | null;
  relevance: Relevance | null; // 뉴스 키워드 수집분에만 있음
  summary: string;
  mentions: number;
  density: number;
  titleHas: boolean;
  length: number;
  metrics: ContentMetrics;
  topWords: TopWord[];
  analyzedVersion: number;
  staleDict: boolean;
  paragraphs: string[];
  removed: RemovedBlock[];
  /** 정제 전 본문. 있으면 원본 탭이 이것을 보여 준다 (백엔드 연결 시). 없으면 paragraphs + removed */
  rawBody?: string;
  /** 이 글을 찾은 검색 키워드와 순위 (백엔드 연결 시) */
  hits?: ContentHit[];
}

export interface ContentHit {
  keyword: string;
  rank: number;
  foundAt: string; // YYYY-MM-DD HH:mm
}

/** 목록·대시보드에서 쓰는 콘텐츠 요약 */
export type ContentSummary = Pick<
  Content,
  "id" | "title" | "type" | "outlet" | "published" | "isNew" | "keyword" | "relevance" | "summary"
> & { sourceName: string };

export interface JobStages {
  search: number;
  dedup: number;
  period: number;
  fresh: number;
  body: number;
  clean: number;
}

export interface Job {
  id: string;
  time: string; // MM-DD HH:mm
  sourceId: string;
  mode: JobMode;
  dur: number | null; // 초
  status: JobStatus;
  count: number | null;
  stages?: JobStages;
  reason?: string;
}

export interface DictEntry {
  id: string;
  word: string;
  origin: string;
  target: string; // 'default' 또는 소스 id
  added: string;
  on: boolean;
  pos?: string; // 사용자 사전만
  pending?: boolean; // 사용자 사전만 — 재분석 전
}

export interface AnalysisSettings {
  version: number;
  preset: "strict" | "normal" | "loose" | "custom";
  metrics: Record<keyof ContentMetrics, boolean>;
  topN: number;
  ttrWarn: number;
  minBody: number | null; // [확인 필요] 기본값 미정
  denom: string;
  posRange: string;
  densityWarn: number;
  warnMinCount: number;
  warnMinNouns: number;
  minMentions: number;
  densTitle: number;
  densNoTitle: number;
  densMinLen: number;
  requireTitle: boolean;
  passingMode: "hide" | "dim" | "show";
}

export interface AdminDefault {
  key: string;
  label: string;
  def: number;
  min: number;
  max: number;
  unit: string;
  dec?: number;
}

export interface DailyCount {
  news: number;
  board: number;
  url: number;
}

export interface Analysis {
  core: { w: string; docs: number; d: number; kind: "center" | "background" }[];
  rising: { w: string; n: number; x: number }[];
  hit: { kw: string; n: number; main: number; partial: number; passing: number }[];
  related: Record<string, [string, number][]>;
}

export interface AdminOverview {
  users: number;
  newThisMonth: number;
  active7: number;
  apiToday: number;
  apiLimit: number;
  queueWait: number;
  avgWait: number;
  usage: { user: string; plan: string; src: number; kw: number; n30: number; last: string }[];
  queue: { waiting: number; running: number; avgWait: number; workers: number; fail1h: number };
  core: { w: string; docs: number; d: number }[];
  keywords: { kw: string; n: number }[];
}

// ── 화면별 응답 ──

export interface DashboardData {
  summary: {
    todayCount: number;
    delta: number; // 어제 대비
    sourceCounts: Record<SourceType, number> & { total: number };
    successRate: number; // 최근 7일, %
    failCount: number;
    nextTime: string;
    nextSource: string;
  };
  /** 최근 3회 연속 0건인 소스 */
  alerts: { sourceId: string; name: string }[];
  recent: Record<"all" | SourceType, ContentSummary[]>;
  sources: Pick<Source, "id" | "name" | "status" | "recentNew">[];
  jobs: (Job & { sourceName: string })[];
}

export interface ContentListParams {
  q: string; // 제목·요약 검색 ([확인 필요] 검색 대상)
  sourceId: string; // 'all' 또는 소스 id
  period: "7" | "30" | "all"; // 최근 N일 ([확인 필요] 선택지)
  relevance: "all" | Relevance;
  page: number; // 1부터
}

export interface ContentListResult {
  items: ContentSummary[];
  total: number;
  page: number;
  pageCount: number;
  /** 분석 설정의 '스쳐 지나감' 처리 — hide 는 서버에서 이미 제외, dim 은 화면에서 흐리게, show 는 그대로 */
  passingMode: AnalysisSettings["passingMode"];
  /** 키워드 관련도 분석 결과가 있는가. false 면 관련도 필터·열을 감춘다 (백엔드에 분석 기능이 생기기 전) */
  analyzed: boolean;
}

/**
 * analyzed=false 면 관련도·지표·상위 키워드 카드를 감춘다 (content 의 분석 필드는 빈 값).
 * 백엔드에 키워드 분석 기능이 생기기 전의 live 모드가 이렇다.
 */
export type ContentDetail =
  | {
      content: Content;
      analyzed: true;
      /** 판정 기준·표시 항목에 쓰는 현재 분석 설정 */
      settings: Pick<
        AnalysisSettings,
        "version" | "metrics" | "topN" | "ttrWarn" | "denom" | "posRange" | "densTitle" | "minMentions"
      >;
    }
  | { content: Content; analyzed: false };

export type AnalyzedContentDetail = Extract<ContentDetail, { analyzed: true }>;

export interface JobListParams {
  sourceId: string; // 'all' 또는 소스 id
  status: "all" | JobStatus;
  period: "7" | "30"; // [확인 필요] 선택지
}

/** 수집 작업 목록 행 — 실패 조치 버튼(소스 설정 열기·탐지 다시 실행)에 소스 유형이 필요하다 */
export type JobRow = Job & { sourceName: string; sourceType: SourceType | null };

export interface AnalysisParams {
  period: "7" | "30";
  sourceId: string; // 'all' 또는 소스 id
}

/** 키워드 분석 (ANALYSIS-001) — 핵심어·급상승·적중도 */
export interface AnalysisOverview {
  /** 적용 중인 분석 설정 요약 */
  basis: Pick<AnalysisSettings, "preset" | "denom" | "posRange">;
  /** 켜진 불용어를 뺀 상위 핵심어 */
  core: Analysis["core"];
  rising: Analysis["rising"];
  /** warn: 키워드 수정 권장 — 기준 [정책 필요], MOCK 은 스쳐 지나감 50% 이상 */
  hit: (Analysis["hit"][number] & { warn: boolean })[];
}

/** 연관어 한 개와, 연관어 메뉴에서 이미 처리됐는지 여부 */
export interface RelatedWord {
  w: string;
  n: number; // 함께 나온 글 수
  isKeyword: boolean; // 이미 기준 소스의 검색 키워드
  isStopword: boolean; // 이미 불용어
}

/** 분석 설정 화면 (SETTING-001) */
export interface SettingsBundle {
  /** 'default' = 내 기본값, 그 밖에는 소스 id */
  scope: string;
  settings: AnalysisSettings;
  /** 관리자가 정한 시스템 기본값·허용 범위 (ADMIN-001-U06) — 입력 검증과 '보통' 프리셋에 쓴다 */
  ranges: AdminDefault[];
  dictCounts: { stopwords: number; compounds: number };
  /** 최근 7일 수집분의 1,000자당 밀도 분포 — 변경 미리보기용 (MOCK) */
  densityHistogram: { binWidth: number; counts: number[] };
}

export type DictKind = "stopwords" | "compounds";
export type DictOrigin = "직접 추가" | "키워드 분석에서 추가" | "CSV 가져오기" | "시스템 공통";

export interface DictListParams {
  q: string;
  origin: "all" | DictOrigin;
  target: string; // 'all' · 'default' · 소스 id
  sort: "recent" | "old" | "abc"; // [확인 필요] 정렬 선택지
  page: number;
}

export interface DictListResult {
  items: DictEntry[];
  total: number;
  page: number;
  pageCount: number;
  counts: Record<DictKind, number>;
  /** 재분석 전이라 기존 글에 반영되지 않은 사용자 사전 변경 수 (FN-DIC-006) */
  pendingCount: number;
}

/** 관리자 화면 (ADMIN-001) */
export interface AdminPageData extends AdminOverview {
  /** 시스템 기본값·허용 범위 (FN-ADM-006) */
  defaults: AdminDefault[];
  /** 공통 불용어 — 사전의 '시스템 공통' 출처와 같은 목록 (FN-ADM-007) */
  commonStopwords: DictEntry[];
}

export interface SourceOption {
  id: string;
  name: string;
}

export interface CollectResult {
  jobIds: string[];
  queued: number;
  skipped: number; // 이미 대기·실행 중이라 건너뛴 소스 수
}
