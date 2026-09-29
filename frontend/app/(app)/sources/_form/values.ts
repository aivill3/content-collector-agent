// 소스 폼 입력값 — 숫자 필드도 입력 중 그대로 두려고 문자열로 들고, 저장할 때 바꾼다.

import { SCHEDULE_LABEL } from "@/lib/labels";
import type { BoardSelectors, Schedule, Source, SourceInput, SourceKeyword, SourceType } from "@/lib/types";

export type BoardMode = "auto" | "manual";

export interface FormValues {
  name: string;
  analysis: "default" | "custom";
  nonKorean: boolean;
  // 수집 일정 (뉴스·게시판)
  schedule: Schedule;
  time: string;
  cron: string;
  // 뉴스
  keywords: SourceKeyword[];
  count: string;
  sort: "sim" | "date";
  period: string;
  // 게시판
  boardUrl: string;
  pageParam: string;
  pages: string;
  maxPosts: string;
  urlPattern: string;
  boardPeriod: string;
  skipNotice: boolean;
  listPattern: string;
  // 게시판 · URL
  minLen: string;
  // URL
  urls: string;
}

export type FormErrors = Partial<Record<"name" | "keywords" | "count" | "boardUrl" | "urls" | "cron", string>>;

const DEFAULTS: FormValues = {
  name: "", analysis: "default", nonKorean: false,
  schedule: "daily", time: "", cron: "",
  keywords: [], count: "30", sort: "sim", period: "3d",
  boardUrl: "", pageParam: "page", pages: "2", maxPosts: "50", urlPattern: "", boardPeriod: "none", skipNotice: true, listPattern: "",
  minLen: "30",
  urls: "",
};

export function initialValues(source?: Source | null): FormValues {
  if (!source) return DEFAULTS;
  const str = (v: number | undefined, fallback: string) => (v == null ? fallback : String(v));
  return {
    ...DEFAULTS,
    name: source.name,
    analysis: source.analysis,
    nonKorean: source.nonKorean,
    schedule: source.schedule,
    time: source.time,
    cron: source.cron,
    keywords: source.keywords ?? [],
    count: str(source.count, DEFAULTS.count),
    sort: source.sort ?? DEFAULTS.sort,
    period: source.period ?? DEFAULTS.period,
    boardUrl: source.boardUrl ?? "",
    pageParam: source.pageParam ?? DEFAULTS.pageParam,
    pages: str(source.pages, DEFAULTS.pages),
    maxPosts: str(source.maxPosts, DEFAULTS.maxPosts),
    urlPattern: source.urlPattern ?? "",
    boardPeriod: source.boardPeriod ?? DEFAULTS.boardPeriod,
    skipNotice: source.skipNotice ?? DEFAULTS.skipNotice,
    listPattern: source.listPattern ?? "",
    minLen: str(source.minLen, DEFAULTS.minLen),
    urls: source.urls ?? "",
  };
}

/** 줄마다 하나, 공백 제거, 중복 제외 */
export function urlList(urls: string): string[] {
  return Array.from(new Set(urls.split("\n").map((x) => x.trim()).filter(Boolean)));
}

// Validation — 문서 확정: 검색 건수 1~1,000. 나머지 필수 조건은 [추정]. 오류 문구 [문구 확인 필요]
export function validate(v: FormValues, type: SourceType): FormErrors {
  const err: FormErrors = {};
  if (!v.name.trim()) err.name = "소스 이름을 입력하세요";
  if (type === "news") {
    if (!v.keywords.length) err.keywords = "키워드를 1개 이상 추가하세요";
    const n = Number(v.count);
    if (!(n >= 1 && n <= 1000)) err.count = "1~1,000 사이로 입력하세요";
  }
  if (type === "board" && !v.boardUrl.trim()) err.boardUrl = "게시판 목록 URL을 입력하세요";
  if (type === "url" && !urlList(v.urls).length) err.urls = "주소를 1개 이상 입력하세요";
  if (type !== "url" && v.cron.trim() && v.cron.trim().split(/\s+/).length !== 5) err.cron = "cron 식 형식을 확인하세요 [추정]";
  return err;
}

/** 유형에 해당하는 필드만 담아 저장 요청으로 */
export function toInput(v: FormValues, type: SourceType, id: string | null, selectors: BoardSelectors | null): SourceInput {
  const num = (s: string) => Number(s) || 0;
  const common = { id: id ?? undefined, type, name: v.name.trim(), analysis: v.analysis, nonKorean: v.nonKorean };
  if (type === "news") {
    return {
      ...common, schedule: v.schedule, time: v.time, cron: v.cron.trim(),
      keywords: v.keywords, count: num(v.count), sort: v.sort, period: v.period,
    };
  }
  if (type === "board") {
    return {
      ...common, schedule: v.schedule, time: v.time, cron: v.cron.trim(),
      boardUrl: v.boardUrl.trim(), pageParam: v.pageParam, pages: num(v.pages), maxPosts: num(v.maxPosts),
      urlPattern: v.urlPattern, boardPeriod: v.boardPeriod, skipNotice: v.skipNotice, minLen: num(v.minLen),
      listPattern: v.listPattern || undefined, selectors: selectors ?? undefined,
    };
  }
  // URL 수집은 한 번만 실행한다
  return { ...common, schedule: "manual", time: "", cron: "", urls: urlList(v.urls).join("\n"), minLen: num(v.minLen) };
}

export function scheduleSummary(v: FormValues): string {
  const sched = v.cron ? `cron ${v.cron}` : `${SCHEDULE_LABEL[v.schedule]} ${v.time || "[HH:MM]"}`;
  return `${sched} · ${v.analysis === "custom" ? "개별 설정" : "내 기본값"}`;
}

export function scopeSummary(v: FormValues): string {
  return `${v.pageParam} 파라미터 · ${v.pages}쪽 · 최대 ${v.maxPosts}개 · ${v.skipNotice ? "공지 제외" : "공지 포함"}`;
}

export function basicSummary(v: FormValues): string {
  return `게시판 · ${v.name || "[소스 이름]"} · ${v.boardUrl || "https://[사이트]/bbs/board.php?bo_table=notice"}`;
}

const pad = (n: number) => String(n).padStart(2, "0");
export const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

/** 섹션 컴포넌트가 받는 폼 상태 */
export interface FormProps {
  v: FormValues;
  set: (patch: Partial<FormValues>) => void;
  err: FormErrors;
  setErr: (patch: FormErrors) => void;
}
