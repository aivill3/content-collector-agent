"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { StatCard, StatGrid } from "@/components/ui/stat-card";
import { SegmentedTabs } from "@/components/ui/segmented-tabs";
import { EmptyState, ErrorState, PageSkeleton } from "@/components/ui/states";
import { Table, Td, Th } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { RELEVANCE_BADGE, SOURCE_TYPE_LABEL, STATUS_BADGE } from "@/lib/labels";
import { useApiData, usePollWhile } from "@/lib/use-api-data";
import type { ContentSummary, DashboardData, SourceType } from "@/lib/types";

// MAIN-001 대시보드

const SEGMENTS = [
  ["all", "전체"],
  ["news", "뉴스"],
  ["board", "게시판"],
  ["url", "URL"],
] as const;

export function DashboardScreen() {
  const { data, error, loading, refreshing, reload } = useApiData(api.getDashboard);
  const toast = useToast();
  const [collecting, setCollecting] = useState(false);

  // 대기·실행 중인 소스가 있으면 상태가 바뀔 때까지 1초마다 조용히 갱신한다
  const hasActive = !!data?.sources.some((s) => s.status === "queued" || s.status === "running");
  usePollWhile(hasActive, () => reload("quiet"));

  // FUNC: FN-COL-001 — [확인 필요] "지금 수집" 대상은 전체 소스로 가정
  const collectAll = async () => {
    setCollecting(true);
    try {
      const res = await api.runCollect();
      toast(res.queued > 0 ? `수집 작업 ${res.queued}건을 등록했습니다` : "이미 실행 중인 소스입니다");
      reload("quiet");
    } finally {
      setCollecting(false);
    }
  };

  const header = (
    <PageHeader
      title="대시보드"
      description="새로 들어온 글, 수집 상태, 손볼 곳을 한 화면에서 확인합니다"
      actions={
        <>
          {/* FUNC: FN-DASH-005 */}
          <Button
            data-ui-id="MAIN-001-U01"
            data-func-id="FN-DASH-005"
            onClick={() => reload("refresh")}
            disabled={loading || refreshing}
          >
            {refreshing ? "새로고침 중…" : "새로고침"}
          </Button>
          <ButtonLink href="/sources/new" variant="primary" data-ui-id="MAIN-001-U02">
            + 소스 추가
          </ButtonLink>
        </>
      }
    />
  );

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState onRetry={() => reload("full")} />;

  return (
    <div data-screen-label="MAIN-001 대시보드" data-screen-id="MAIN-001" className="flex flex-col gap-6">
      {header}
      {data.summary.sourceCounts.total === 0 ? (
        // Empty 상태 [추정] / [문구 확인 필요]
        <EmptyState
          title="등록된 수집 소스가 없습니다"
          description="[문구 확인 필요] 소스를 추가하면 수집 현황이 여기에 표시됩니다"
          action={
            <ButtonLink href="/sources/new" variant="primary" className="h-10">
              + 소스 추가
            </ButtonLink>
          }
        />
      ) : (
        <>
          <SummaryCards summary={data.summary} />
          {data.alerts.map((a) => (
            <div
              key={a.sourceId}
              data-ui-id="MAIN-001-U04"
              data-func-id="FN-DASH-002"
              role="status"
              className="flex flex-wrap items-center gap-5 rounded-card border border-alert-line bg-alert px-6 py-4"
            >
              <span className="text-[13px] font-semibold text-warn">점검 필요</span>
              <span className="min-w-60 flex-1 text-sm">
                <strong>{a.name}</strong> 최근 3회 연속 0건 — 사이트 구조 변경이 의심됩니다
              </span>
              <Link href="/sources" className="font-bold text-warn underline hover:text-warn">
                설정 확인
              </Link>
            </div>
          ))}
          <div className="flex flex-wrap items-start gap-6">
            <RecentContents recent={data.recent} />
            <SourceStatusCard sources={data.sources} onCollect={collectAll} collecting={collecting} />
          </div>
          <JobHistory jobs={data.jobs} />
        </>
      )}
    </div>
  );
}

function SummaryCards({ summary: s }: { summary: DashboardData["summary"] }) {
  return (
    <StatGrid label="요약" data-ui-id="MAIN-001-U03" data-func-id="FN-DASH-001">
      <StatCard label="오늘 수집된 콘텐츠" value={`${s.todayCount}건`} sub={`어제 대비 ${s.delta >= 0 ? "+" : ""}${s.delta}건`} />
      <StatCard
        label="활성 수집 소스"
        value={`${s.sourceCounts.total}개`}
        sub={`뉴스 ${s.sourceCounts.news} · 게시판 ${s.sourceCounts.board} · URL ${s.sourceCounts.url}`}
      />
      <StatCard label="최근 7일 수집 성공률" value={`${s.successRate}%`} sub={`실패 ${s.failCount}건`} />
      <StatCard label="다음 예정 수집" value={s.nextTime} sub={s.nextSource} />
    </StatGrid>
  );
}

function RecentContents({ recent }: { recent: DashboardData["recent"] }) {
  const [seg, setSeg] = useState<"all" | SourceType>("all");
  const items = recent[seg];
  return (
    <Card data-func-id="FN-DASH-003" className="flex min-w-0 flex-[1.9_1_520px] flex-col gap-4">
      <CardTitle>최근 수집 콘텐츠</CardTitle>
      <SegmentedTabs data-ui-id="MAIN-001-U05" label="수집 경로" items={SEGMENTS} value={seg} onChange={setSeg} />
      <div data-ui-id="MAIN-001-U06" className="flex flex-col">
        {items.map((c) => (
          <RecentItem key={c.id} item={c} />
        ))}
        {items.length === 0 && (
          <p className="m-0 py-6 text-center text-[13px] text-muted">해당 유형의 최근 콘텐츠가 없습니다 [문구 확인 필요]</p>
        )}
      </div>
      <p data-ui-id="MAIN-001-U07" className="m-0 text-[13px] text-muted">
        회색 = 수집 경로 · 색 배지 = 키워드 관련도 (뉴스 키워드 수집분에만 표시)
      </p>
      <Link data-ui-id="MAIN-001-U08" href="/contents" className="text-sm font-bold">
        전체 콘텐츠 보기
      </Link>
    </Card>
  );
}

function RecentItem({ item: c }: { item: ContentSummary }) {
  const via = c.type === "news" ? `키워드 '${c.keyword}'` : c.type === "board" ? `'${c.sourceName}'` : "";
  const meta = [c.outlet, c.published.slice(5, 10), via].filter(Boolean).join(" · ");
  const rel = c.type === "news" && c.relevance ? RELEVANCE_BADGE[c.relevance] : null;
  return (
    <article className="flex flex-col gap-2 border-b border-line-soft py-[18px]">
      <div className="flex items-center gap-2">
        {c.isNew && (
          <Badge tone="blue" strong>
            NEW
          </Badge>
        )}
        <Link href={`/contents/${c.id}`} className="text-[15px] font-bold text-ink hover:text-ink">
          {c.title}
        </Link>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-[13px] text-muted">
        <Badge>{SOURCE_TYPE_LABEL[c.type]}</Badge>
        <span>{meta}</span>
        {rel && <Badge tone={rel[1]}>{rel[0]}</Badge>}
      </div>
      <p className="m-0 truncate text-[13px] text-faint">{c.summary}</p>
    </article>
  );
}

function SourceStatusCard({
  sources,
  onCollect,
  collecting,
}: {
  sources: DashboardData["sources"];
  onCollect: () => void;
  collecting: boolean;
}) {
  return (
    <Card data-func-id="FN-DASH-004" className="flex min-w-0 flex-[1_1_300px] flex-col gap-3.5">
      <div className="flex items-center justify-between">
        <CardTitle>소스별 현황</CardTitle>
        <Button size="sm" data-ui-id="MAIN-001-U10" data-func-id="FN-COL-001" onClick={onCollect} disabled={collecting}>
          지금 수집
        </Button>
      </div>
      <Table data-ui-id="MAIN-001-U09">
        <thead>
          <tr>
            <Th>소스</Th>
            <Th>최근 상태</Th>
            <Th>최근 신규</Th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => {
            const [label, tone] = STATUS_BADGE[s.status];
            return (
              <tr key={s.id}>
                <Td className="pr-2">{s.name}</Td>
                <Td>
                  <Badge tone={tone}>{label}</Badge>
                </Td>
                <Td className="font-mono text-[13px]">
                  {s.recentNew == null ? "—" : s.recentNew > 0 ? `+${s.recentNew}` : "0"}
                </Td>
              </tr>
            );
          })}
        </tbody>
      </Table>
      <p className="m-0 text-[13px] leading-relaxed text-muted">
        최근 신규 = 마지막 수집에서 새로 저장된 글 수 (정기·수동 모두) · — 는 아직 수집 전
      </p>
      <Link data-ui-id="MAIN-001-U11" href="/sources" className="font-bold">
        수집 소스 관리
      </Link>
    </Card>
  );
}

function JobHistory({ jobs }: { jobs: DashboardData["jobs"] }) {
  return (
    <Card className="flex flex-col gap-3.5">
      <div className="flex items-center justify-between">
        <CardTitle>수집 작업 이력</CardTitle>
        <Link data-ui-id="MAIN-001-U13" href="/jobs" className="text-sm font-bold">
          작업 이력 전체
        </Link>
      </div>
      <div className="overflow-x-auto">
        <Table data-ui-id="MAIN-001-U12" className="min-w-[760px]">
          <thead>
            <tr>
              <Th>실행 시각</Th>
              <Th>소스</Th>
              <Th>방식</Th>
              <Th>소요</Th>
              <Th>상태</Th>
              <Th>단계별 건수 / 사유</Th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => {
              const [label, tone] = STATUS_BADGE[j.status];
              const detail =
                j.status === "success" && j.stages
                  ? `검색 ${j.stages.search} → 정제 통과 ${j.stages.clean}`
                  : j.status === "fail"
                    ? j.reason
                    : "—";
              return (
                <tr key={j.id}>
                  <Td className="pr-3 font-mono text-[13px] whitespace-nowrap">{j.time}</Td>
                  <Td className="pr-3">{j.sourceName}</Td>
                  <Td className="pr-3">
                    <Badge>{j.mode}</Badge>
                  </Td>
                  <Td className="pr-3 font-mono text-[13px] whitespace-nowrap">{j.dur == null ? "—" : `${j.dur}초`}</Td>
                  <Td className="pr-3">
                    <Badge tone={tone}>{label}</Badge>
                  </Td>
                  <Td className="text-ink-2">{detail}</Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </div>
    </Card>
  );
}
