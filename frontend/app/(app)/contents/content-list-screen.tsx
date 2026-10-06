"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { SegmentedTabs } from "@/components/ui/segmented-tabs";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { Table, Td, Th } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import { downloadBlob } from "@/lib/download";
import { RELEVANCE_BADGE } from "@/lib/labels";
import { useApiData } from "@/lib/use-api-data";
import type { ContentListParams, ContentSummary } from "@/lib/types";

// CONTENT-001 콘텐츠 목록

type Filters = Omit<ContentListParams, "page">;

const RELEVANCES = [
  ["all", "전체"],
  ["main", "주제 기사"],
  ["partial", "부분 언급"],
  ["passing", "스쳐 지나감"],
] as const;

const PASSING_NOTE = { dim: "흐리게 표시", hide: "숨김", show: "그대로 표시" } as const;

const defaultFilters = (q = ""): Filters => ({ q, sourceId: "all", period: q ? "all" : "7", relevance: "all" });

export function ContentListScreen({ initialQ }: { initialQ: string }) {
  const toast = useToast();
  const [filters, setFilters] = useState<Filters>(() => defaultFilters(initialQ));
  const [page, setPage] = useState(1);
  // 검색어는 입력이 멈춘 뒤에 조회한다
  const [debouncedQ, setDebouncedQ] = useState(filters.q);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(filters.q), 250);
    return () => clearTimeout(t);
  }, [filters.q]);

  const params: ContentListParams = { ...filters, q: debouncedQ, page };
  const { data, error, loading, stale, reload } = useApiData(() => api.listContents(params), JSON.stringify(params));
  const { data: sourceOptions } = useApiData(api.listSourceOptions);

  // 필터를 바꾸면 1페이지로 [추정]
  const update = (patch: Partial<Filters>) => {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  };
  const reset = () => {
    setFilters(defaultFilters());
    setDebouncedQ("");
    setPage(1);
  };

  // FUNC: FN-CNT-002 — 현재 필터 결과 전체를 CSV 로 [추정] / 포함 열 [확인 필요]
  const exportCsv = async () => {
    setExporting(true);
    try {
      const { blob, count } = await api.exportContents({ ...filters, q: debouncedQ });
      downloadBlob(blob, "contents.csv");
      toast(`${count}건을 CSV로 내보냈습니다`);
    } catch {
      toast("CSV를 내보내지 못했습니다 [문구 확인 필요]");
    } finally {
      setExporting(false);
    }
  };

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState onRetry={() => reload("full")} />;

  const empty = data.total === 0;
  // 키워드 관련도 분석이 없으면(백엔드 연결 시) 관련도 필터·열·안내를 감춘다
  const analyzed = data.analyzed;

  return (
    <div data-screen-label="CONTENT-001 콘텐츠 목록" data-screen-id="CONTENT-001" className="flex flex-col gap-6">
      <PageHeader
        title="콘텐츠"
        description={analyzed ? "수집된 글을 소스·기간·관련도로 걸러 봅니다" : "수집된 글을 소스·기간으로 걸러 봅니다"}
        actions={
          // 0건이면 비활성 [추정]
          <Button data-ui-id="CONTENT-001-U01" data-func-id="FN-CNT-002" onClick={exportCsv} disabled={empty || exporting}>
            CSV 내보내기
          </Button>
        }
      />

      <section
        data-func-id="FN-CNT-001"
        aria-label="필터"
        className="flex flex-wrap items-end gap-4 rounded-card border border-line bg-surface p-6"
      >
        {/* [확인 필요] 검색 대상(제목/본문) — 제목·요약으로 가정 */}
        <Field label="검색" className="flex-[2.4_1_240px]">
          <Input data-ui-id="CONTENT-001-U02" type="search" value={filters.q} onChange={(e) => update({ q: e.target.value })} />
        </Field>
        <Field label="소스" className="flex-[1_1_160px]">
          <Select data-ui-id="CONTENT-001-U03" value={filters.sourceId} onChange={(e) => update({ sourceId: e.target.value })}>
            <option value="all">전체 소스</option>
            {sourceOptions?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        {/* [확인 필요] 선택지 목록 — 최근 7일 외 항목은 추정 */}
        <Field label="기간" className="flex-[.9_1_140px]">
          <Select
            data-ui-id="CONTENT-001-U04"
            value={filters.period}
            onChange={(e) => update({ period: e.target.value as Filters["period"] })}
          >
            <option value="7">최근 7일</option>
            <option value="30">최근 30일</option>
            <option value="all">전체</option>
          </Select>
        </Field>
        {analyzed && (
          <div className="flex max-w-full min-w-0 flex-[0_1_auto] flex-col gap-2">
            <span id="rel-label" className="text-[13px] font-semibold">
              키워드 관련도
            </span>
            <SegmentedTabs
              data-ui-id="CONTENT-001-U05"
              mode="radio"
              labelledBy="rel-label"
              items={RELEVANCES}
              value={filters.relevance}
              onChange={(relevance) => update({ relevance })}
            />
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4 rounded-card border border-line bg-surface px-6 pt-3 pb-6">
        <div aria-busy={stale} className={cx("overflow-x-auto transition-opacity", stale && "opacity-60")}>
          <Table data-ui-id="CONTENT-001-U06" className="min-w-[820px]">
            <thead>
              <tr>
                <Th className="w-[44%] pt-3.5 pb-2.5">제목</Th>
                <Th className="pt-3.5 pb-2.5">출처</Th>
                <Th className="pt-3.5 pb-2.5">발행일</Th>
                <Th className="pt-3.5 pb-2.5">수집 경로</Th>
                {analyzed && <Th className="pt-3.5 pb-2.5">관련도</Th>}
              </tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <ContentRow
                  key={c.id}
                  item={c}
                  showRelevance={analyzed}
                  dim={data.passingMode === "dim" && c.relevance === "passing"}
                />
              ))}
            </tbody>
          </Table>
        </div>
        {empty && (
          // Empty [문구 확인 필요]
          <div className="flex flex-col items-center gap-2.5 py-8">
            <p className="m-0 font-semibold">조건에 맞는 콘텐츠가 없습니다</p>
            <p className="m-0 text-[13px] text-muted">[문구 확인 필요]</p>
            <Button size="sm" onClick={reset}>
              필터 초기화
            </Button>
          </div>
        )}
        <div data-ui-id="CONTENT-001-U08" className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-[13px] text-muted">
            총 {data.total}건
            {analyzed && <> · &apos;스쳐 지나감&apos;은 분석 설정에 따라 {PASSING_NOTE[data.passingMode]}</>}
          </span>
          <Pagination page={data.page} pageCount={data.pageCount} onChange={setPage} />
        </div>
      </section>
    </div>
  );
}

function ContentRow({ item: c, dim, showRelevance }: { item: ContentSummary; dim: boolean; showRelevance: boolean }) {
  const path =
    c.type === "news"
      ? c.keyword
        ? `키워드 '${c.keyword}'`
        : "뉴스 키워드"
      : c.type === "board"
        ? `게시판 '${c.sourceName}'`
        : "URL 수집";
  const rel = c.relevance ? RELEVANCE_BADGE[c.relevance] : (["—", "gray"] as const);
  return (
    <tr data-ui-id="CONTENT-001-U07" className={cx(dim && "opacity-45")}>
      <Td className="py-3 pr-4">
        <Link href={`/contents/${c.id}`} className="block font-bold text-ink hover:text-ink">
          {c.title}
        </Link>
        <span className="mt-1 block max-w-[460px] truncate text-xs text-faint">{c.summary}</span>
      </Td>
      <Td className="py-3 text-ink-2">{c.outlet}</Td>
      <Td className="py-3 font-mono text-[13px]">{c.published.slice(5, 10)}</Td>
      <Td className="py-3 text-ink-2">{path}</Td>
      {showRelevance && (
        <Td className="py-3">
          <Badge tone={rel[1]}>{rel[0]}</Badge>
        </Td>
      )}
    </tr>
  );
}
