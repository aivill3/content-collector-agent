"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Field, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import { downloadBlob } from "@/lib/download";
import { STATUS_BADGE } from "@/lib/labels";
import { useApiData, usePollWhile } from "@/lib/use-api-data";
import type { JobListParams, JobRow, JobStages } from "@/lib/types";

// JOB-001 수집 작업

// [확인 필요] 게시판·URL 작업의 단계명 — 뉴스와 같은 이름으로 표시
const STAGES: [keyof JobStages, string][] = [
  ["search", "검색"],
  ["dedup", "중복 제거 후"],
  ["period", "기간 필터 후"],
  ["fresh", "신규"],
  ["body", "본문 확보"],
  ["clean", "정제 통과"],
];

const GRID = "grid grid-cols-[140px_minmax(0,1fr)_76px_76px_100px_80px] gap-3";

const isActive = (j: JobRow) => j.status === "queued" || j.status === "running";
const isExpandable = (j: JobRow) => j.status === "success" || j.status === "fail";

export function JobScreen() {
  const toast = useToast();
  const [filters, setFilters] = useState<JobListParams>({ sourceId: "all", status: "all", period: "7" });
  // null 이면 와이어프레임처럼 첫 성공·첫 실패 행을 펼쳐 둔다
  const [open, setOpen] = useState<Record<string, boolean> | null>(null);
  const [exporting, setExporting] = useState(false);

  const { data, error, loading, stale, reload } = useApiData(() => api.listJobs(filters), JSON.stringify(filters));
  const { data: sourceOptions } = useApiData(api.listSourceOptions);

  usePollWhile(!!data?.some(isActive), () => reload("quiet"));

  const update = (patch: Partial<JobListParams>) => setFilters((f) => ({ ...f, ...patch }));

  // FUNC: FN-JOB-004
  const exportCsv = async () => {
    setExporting(true);
    try {
      const { blob, count } = await api.exportJobs(filters);
      downloadBlob(blob, "jobs.csv");
      toast(`${count}건을 CSV로 내보냈습니다`);
    } catch {
      toast("CSV를 내보내지 못했습니다 [문구 확인 필요]");
    } finally {
      setExporting(false);
    }
  };

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState onRetry={() => reload("full")} />;

  const openMap = open ?? {
    [data.find((j) => j.status === "success")?.id ?? ""]: true,
    [data.find((j) => j.status === "fail")?.id ?? ""]: true,
  };
  const toggle = (id: string) => setOpen({ ...openMap, [id]: !openMap[id] });

  return (
    <div data-screen-label="JOB-001 수집 작업" data-screen-id="JOB-001" className="flex flex-col gap-6">
      <PageHeader
        title="수집 작업"
        description="실행 이력과 단계별 건수로 수집 결과가 왜 이렇게 나왔는지 확인합니다"
        actions={
          <Button data-ui-id="JOB-001-U01" data-func-id="FN-JOB-004" onClick={exportCsv} disabled={data.length === 0 || exporting}>
            CSV 내보내기
          </Button>
        }
      />

      <section data-func-id="FN-JOB-001" aria-label="필터" className="flex flex-wrap gap-4 rounded-card border border-line bg-surface p-6">
        <Field label="소스" className="w-[220px]">
          <Select data-ui-id="JOB-001-U02" value={filters.sourceId} onChange={(e) => update({ sourceId: e.target.value })}>
            <option value="all">전체 소스</option>
            {sourceOptions?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        {/* 선택지 [추정] */}
        <Field label="상태" className="w-40">
          <Select
            data-ui-id="JOB-001-U03"
            value={filters.status}
            onChange={(e) => update({ status: e.target.value as JobListParams["status"] })}
          >
            <option value="all">전체</option>
            <option value="success">성공</option>
            <option value="fail">실패</option>
            <option value="running">실행 중</option>
            <option value="queued">대기</option>
          </Select>
        </Field>
        {/* [확인 필요] 선택지 · MOCK 데이터는 모두 최근 7일 이내 */}
        <Field label="기간" className="w-40">
          <Select
            data-ui-id="JOB-001-U04"
            value={filters.period}
            onChange={(e) => update({ period: e.target.value as JobListParams["period"] })}
          >
            <option value="7">최근 7일</option>
            <option value="30">최근 30일</option>
          </Select>
        </Field>
      </section>

      <section className="rounded-card border border-line bg-surface px-6 pt-3 pb-6">
        <div aria-busy={stale} className={cx("overflow-x-auto transition-opacity", stale && "opacity-60")}>
          <div data-ui-id="JOB-001-U05" role="table" aria-label="수집 작업 이력" className="min-w-[820px]">
            <div role="row" className={cx(GRID, "border-b border-line-soft pt-3.5 pb-2.5 text-xs text-ink-2")}>
              {["실행 시각", "소스", "방식", "소요", "상태", "수집"].map((h) => (
                <span key={h} role="columnheader">
                  {h}
                </span>
              ))}
            </div>
            {data.map((j) => (
              <JobItem key={j.id} job={j} open={!!openMap[j.id]} onToggle={() => toggle(j.id)} />
            ))}
          </div>
        </div>
        {data.length === 0 && (
          <p className="m-0 py-8 text-center text-[13px] text-muted">조건에 맞는 작업 이력이 없습니다 [문구 확인 필요]</p>
        )}
      </section>
    </div>
  );
}

function JobItem({ job: j, open, onToggle }: { job: JobRow; open: boolean; onToggle: () => void }) {
  const toast = useToast();
  const expandable = isExpandable(j);
  const [label, tone] = STATUS_BADGE[j.status];
  const stages = j.stages;
  // [확인 필요] 원본 응답·제외 목록 표시 방식 (FN-JOB-005)
  const tbd = () => toast("[확인 필요] 표시 방식이 정의되지 않았습니다");

  return (
    <>
      {/* 행 클릭 펼침 [추정] */}
      <div
        role="row"
        tabIndex={expandable ? 0 : undefined}
        aria-expanded={expandable ? open : undefined}
        onClick={expandable ? onToggle : undefined}
        onKeyDown={(e) => {
          if (expandable && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            onToggle();
          }
        }}
        className={cx(GRID, "items-center border-b border-line-soft py-3.5 text-sm", expandable && "cursor-pointer hover:bg-hover")}
      >
        <span role="cell" className="font-mono text-[13px]">
          {j.time}
        </span>
        <span role="cell">{j.sourceName}</span>
        <span role="cell">
          <Badge>{j.mode}</Badge>
        </span>
        <span role="cell" className="font-mono text-[13px]">
          {j.dur == null ? "—" : `${j.dur}초`}
        </span>
        <span role="cell">
          <Badge tone={tone}>{label}</Badge>
        </span>
        <span role="cell" className="font-mono text-[13px]">
          {j.count == null ? "—" : `${j.count}건`}
        </span>
      </div>

      {open && j.status === "success" && stages && (
        <div data-ui-id="JOB-001-U06" data-func-id="FN-JOB-002" className="my-3 flex flex-col gap-3 rounded-[10px] bg-subtle p-4">
          <strong className="text-[13px]">단계별 건수</strong>
          <div className="flex flex-wrap items-center gap-2">
            {STAGES.map(([k, stageLabel], i) => (
              <div key={k} className="contents">
                {i > 0 && (
                  <span aria-hidden="true" className="text-muted">
                    →
                  </span>
                )}
                <div className="flex min-w-[120px] flex-col gap-1 rounded-control border border-line bg-surface px-4 py-3">
                  <span className="text-xs text-ink-2">{stageLabel}</span>
                  <span className="font-mono text-xl font-semibold">{stages[k]}</span>
                </div>
              </div>
            ))}
          </div>
          <span className="text-[13px] text-ink-2">
            <TextButton onClick={tbd}>키워드별 네이버 API 원본 응답 보기</TextButton> ·{" "}
            <TextButton onClick={tbd}>제외된 글 목록 보기</TextButton>
          </span>
        </div>
      )}

      {open && j.status === "fail" && (
        <div data-ui-id="JOB-001-U07" data-func-id="FN-JOB-003" role="alert" className="my-3 flex flex-col gap-2.5 rounded-[10px] bg-alert p-4">
          <strong className="text-[13px] text-warn">실패 사유</strong>
          <span className="text-sm">{j.reason}</span>
          <div className="flex gap-2">
            {/* 이동 vs 제자리 [확인 필요] — 소스 편집의 자동 탐지로 이동 */}
            {j.sourceType === "board" && (
              <ButtonLink href={`/sources/${j.sourceId}/edit?mode=auto`} size="sm">
                탐지 다시 실행
              </ButtonLink>
            )}
            {j.sourceType && (
              <ButtonLink href={`/sources/${j.sourceId}/edit`} size="sm">
                소스 설정 열기
              </ButtonLink>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function TextButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="border-none bg-transparent p-0 text-[13px] text-ink-2 hover:underline">
      {children}
    </button>
  );
}
