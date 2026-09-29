"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { Table, Td, Th } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { UnderlineTab, UnderlineTabs } from "@/components/ui/underline-tabs";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import { SOURCE_TYPE_BADGE, STATUS_BADGE, scheduleText } from "@/lib/labels";
import { useApiData, usePollWhile } from "@/lib/use-api-data";
import type { Source, SourceType } from "@/lib/types";

// SOURCE-001 수집 소스

const TABS = [
  ["all", "전체"],
  ["news", "뉴스 키워드"],
  ["board", "게시판"],
  ["url", "URL"],
] as const;

const HEAD = ["이름", "유형", "대상", "정기 수집", "마지막 수집", "상태", "분석 설정"];

const isBusy = (s: Source) => s.status === "queued" || s.status === "running";

export function SourceListScreen() {
  const toast = useToast();
  const [tab, setTab] = useState<"all" | SourceType>("all");
  // 요청을 보낸 뒤 목록에 '대기'가 반영되기 전까지 버튼을 막는다 (UI 중복 클릭 방지)
  const [requesting, setRequesting] = useState<string[]>([]);
  const { data, error, loading, stale, reload } = useApiData(() => api.listSources(tab), tab);

  usePollWhile(!!data?.some(isBusy), () => reload("quiet"));

  // FUNC: FN-COL-001 — 서버 멱등성 [API 확인 필요]
  const collect = async (s: Source) => {
    setRequesting((ids) => [...ids, s.id]);
    try {
      const res = await api.runCollect([s.id]);
      toast(res.queued > 0 ? `수집 작업 ${res.queued}건을 등록했습니다` : "이미 실행 중인 소스입니다");
      reload("quiet");
    } catch {
      toast("수집 작업을 등록하지 못했습니다 [문구 확인 필요]");
    } finally {
      setRequesting((ids) => ids.filter((id) => id !== s.id));
    }
  };

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState onRetry={() => reload("full")} />;

  return (
    <div data-screen-label="SOURCE-001 수집 소스" data-screen-id="SOURCE-001" className="flex flex-col gap-5">
      <PageHeader
        title="수집 소스"
        description="키워드·게시판·URL 수집 설정을 등록하고 관리합니다"
        actions={
          <ButtonLink href="/sources/new" variant="primary" data-ui-id="SOURCE-001-U01">
            + 소스 추가
          </ButtonLink>
        }
      />

      <div data-ui-id="SOURCE-001-U02" className="flex flex-col gap-3.5">
        <UnderlineTabs label="소스 유형" className="gap-7">
          {TABS.map(([id, label]) => (
            <UnderlineTab key={id} active={tab === id} bold onClick={() => setTab(id)}>
              {label}
            </UnderlineTab>
          ))}
        </UnderlineTabs>
        <p className="m-0 text-[13px] text-ink-2">탭은 같은 표를 유형별로 거르는 필터입니다</p>
      </div>

      <section data-func-id="FN-SRC-001" className="rounded-card border border-line bg-surface px-6 pt-3 pb-6">
        <div aria-busy={stale} className={cx("overflow-x-auto transition-opacity", stale && "opacity-60")}>
          <Table data-ui-id="SOURCE-001-U03" className="min-w-[960px]">
            <thead>
              <tr>
                {HEAD.map((h) => (
                  <Th key={h} className="pt-3.5 pb-2.5">
                    {h}
                  </Th>
                ))}
                <Th className="pt-3.5 pb-2.5">
                  <span className="sr-only">작업</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <SourceRow
                  key={s.id}
                  source={s}
                  busy={isBusy(s) || requesting.includes(s.id)}
                  onCollect={() => collect(s)}
                />
              ))}
            </tbody>
          </Table>
        </div>
        {data.length === 0 && (
          // Empty [추정] [문구 확인 필요]
          <div className="flex flex-col items-center gap-2.5 pt-10 pb-4">
            <p className="m-0 font-semibold">등록된 소스가 없습니다</p>
            <p className="m-0 text-[13px] text-muted">[문구 확인 필요]</p>
            <ButtonLink href="/sources/new" size="sm">
              + 소스 추가
            </ButtonLink>
          </div>
        )}
      </section>
    </div>
  );
}

function SourceRow({ source: s, busy, onCollect }: { source: Source; busy: boolean; onCollect: () => void }) {
  const [typeLabel, typeTone] = SOURCE_TYPE_BADGE[s.type];
  const [statusLabel, statusTone] = STATUS_BADGE[s.status];
  return (
    <tr>
      <Td className="py-3 pr-3">
        <Link href={`/sources/${s.id}/edit`} className="font-bold">
          {s.name}
        </Link>
      </Td>
      <Td className="py-3">
        <Badge tone={typeTone}>{typeLabel}</Badge>
      </Td>
      <Td className="max-w-[220px] truncate py-3 pr-3 text-ink-2">{s.target}</Td>
      <Td className="py-3 text-ink-2">{scheduleText(s)}</Td>
      <Td className="py-3 font-mono text-[13px]">{s.last || "—"}</Td>
      <Td className="py-3">
        <Badge tone={statusTone}>{statusLabel}</Badge>
      </Td>
      <Td className="py-3 text-ink-2">{s.analysis === "custom" ? <Badge tone="blue">개별 설정</Badge> : "내 기본값"}</Td>
      <Td className="py-3 text-right">
        <Button
          size="sm"
          className="px-4"
          data-ui-id="SOURCE-001-U04"
          data-func-id="FN-COL-001"
          aria-label={`${s.name} 지금 수집`}
          onClick={onCollect}
          disabled={busy}
        >
          {busy ? "수집 중…" : "지금 수집"}
        </Button>
      </Td>
    </tr>
  );
}
