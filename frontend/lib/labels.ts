// 상태값 → 화면 문구·배지 색. 시안 DashboardScreen 등의 STATUS / REL / TYPE 표를 옮겼다.

import type { BadgeTone } from "@/components/ui/badge";
import type { AnalysisSettings, JobStatus, Relevance, Schedule, Source, SourceStatus, SourceType } from "@/lib/types";

export const SOURCE_TYPE_LABEL: Record<SourceType, string> = { news: "뉴스", board: "게시판", url: "URL" };

export const STATUS_BADGE: Record<SourceStatus | JobStatus, [string, BadgeTone]> = {
  success: ["성공", "green"],
  zero3: ["0건 3회", "orange"],
  robots: ["robots 차단", "orange"],
  idle: ["대기", "gray"],
  queued: ["대기", "gray"],
  running: ["실행 중", "blue"],
  fail: ["실패", "orange"],
};

export const RELEVANCE_BADGE: Record<Relevance, [string, BadgeTone]> = {
  main: ["주제 기사", "green"],
  partial: ["부분 언급", "blue"],
  passing: ["스쳐 지나감", "gray"],
};

/** 수집 소스 목록의 유형 배지 — 뉴스만 파란색 */
export const SOURCE_TYPE_BADGE: Record<SourceType, [string, BadgeTone]> = {
  news: ["뉴스 키워드", "blue"],
  board: ["게시판", "gray"],
  url: ["URL", "gray"],
};

export const SCHEDULE_LABEL: Record<Schedule, string> = {
  manual: "수동",
  hourly: "매시간",
  daily: "매일",
  weekly: "매주",
  cron: "고급(cron)",
};

/** '매일 08:00' · '매시간' · 'cron 0 9 * * 1' */
export function scheduleText(s: Pick<Source, "schedule" | "time" | "cron">): string {
  if (s.cron) return `cron ${s.cron}`;
  const withTime = s.time && s.schedule !== "manual" && s.schedule !== "hourly";
  return SCHEDULE_LABEL[s.schedule] + (withTime ? ` ${s.time}` : "");
}

export const PRESET_LABEL: Record<AnalysisSettings["preset"], string> = {
  strict: "엄격 프리셋",
  normal: "보통 프리셋",
  loose: "느슨 프리셋",
  custom: "사용자 지정",
};

export const POS_RANGE_LABEL: Record<string, string> = {
  noun: "명사만",
  vva: "명사+동사·형용사",
  foreign: "명사+동사·형용사+외국어",
};

export const denomLabel = (denom: string) => (denom === "content" ? "내용어 전체" : "명사");
