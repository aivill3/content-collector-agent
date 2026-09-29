"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { Field, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { SegmentedTabs } from "@/components/ui/segmented-tabs";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { Table, Td, Th } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import { POS_RANGE_LABEL, PRESET_LABEL, denomLabel } from "@/lib/labels";
import { useApiData } from "@/lib/use-api-data";
import type { AnalysisOverview, AnalysisParams, RelatedWord, Source } from "@/lib/types";
import { DailyChart } from "./daily-chart";

// ANALYSIS-001 키워드 분석

const PERIODS = [
  ["7", "7일"],
  ["30", "30일"],
] as const;

const CHART_DAYS = [
  ["30", "30일"],
  ["90", "90일"],
] as const;

export function AnalysisScreen() {
  const [params, setParams] = useState<AnalysisParams>({ period: "7", sourceId: "all" });
  const { data, error, loading, stale, reload } = useApiData(() => api.getAnalysis(params), JSON.stringify(params));
  const { data: sourceOptions } = useApiData(api.listSourceOptions);

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState onRetry={() => reload("full")} />;

  const { basis } = data;

  return (
    <div data-screen-label="ANALYSIS-001 키워드 분석" data-screen-id="ANALYSIS-001" className="flex flex-col gap-6">
      <PageHeader
        title="키워드 분석"
        description="수집된 글에서 무슨 이야기가 많은지, 등록 키워드가 잘 맞는지 봅니다"
        actions={
          <div data-func-id="FN-ANL-007" className="flex items-center gap-2">
            <SegmentedTabs
              data-ui-id="ANALYSIS-001-U01"
              mode="radio"
              size="md"
              className="shrink-0"
              label="분석 기간"
              items={PERIODS}
              value={params.period}
              onChange={(period) => setParams((p) => ({ ...p, period }))}
            />
            {/* [확인 필요] 소스 선택 UI 미정 — 버튼 모양의 Select 로 구현. MOCK 은 소스별로 값이 바뀌지 않는다 */}
            <Select
              data-ui-id="ANALYSIS-001-U02"
              aria-label="소스"
              value={params.sourceId}
              onChange={(e) => setParams((p) => ({ ...p, sourceId: e.target.value }))}
              className="h-11 w-auto cursor-pointer px-3 font-semibold"
            >
              <option value="all">전체 소스</option>
              {sourceOptions?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </div>
        }
      />

      <div
        data-ui-id="ANALYSIS-001-U03"
        className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-sm text-ink-2"
      >
        <span>적용 중인 분석 설정:</span>
        <Badge tone="blue" strong>
          {PRESET_LABEL[basis.preset]}
        </Badge>
        <span className="flex-1">
          분모 {denomLabel(basis.denom)} · {POS_RANGE_LABEL[basis.posRange] ?? basis.posRange}
        </span>
        <Link href="/settings" className="font-bold">
          설정 변경
        </Link>
      </div>

      <div
        aria-busy={stale}
        className={cx(
          "grid grid-cols-[repeat(auto-fit,minmax(min(100%,420px),1fr))] items-stretch gap-6 transition-opacity",
          stale && "opacity-60",
        )}
      >
        <CoreCard core={data.core} />
        <RisingCard rising={data.rising} />
        <HitCard hit={data.hit} />
        <RelatedCard />
      </div>

      <TrendCard />
    </div>
  );
}

function CoreCard({ core }: { core: AnalysisOverview["core"] }) {
  return (
    <Card data-ui-id="ANALYSIS-001-U04" data-func-id="FN-ANL-001" className="flex flex-col gap-2.5">
      <CardTitle>핵심어 순위</CardTitle>
      <p className="m-0 text-[13px] text-muted">순위 기준: 등장한 글 수 · 평균 밀도가 높으면 중심어, 낮으면 배경어</p>
      <Table>
        <thead>
          <tr>
            <Th className="w-9">#</Th>
            <Th>단어</Th>
            <Th>등장 글</Th>
            <Th>평균 밀도</Th>
            <Th>성격</Th>
          </tr>
        </thead>
        <tbody>
          {core.map((c, i) => (
            <tr key={c.w}>
              <Td className="py-3 text-[13px]">{i + 1}</Td>
              <Td className="py-3">{c.w}</Td>
              <Td className="py-3 font-mono text-[13px]">{c.docs}</Td>
              <Td className="py-3 font-mono text-[13px]">{c.d.toFixed(1)}%</Td>
              <Td className="py-3">
                {/* 중심어·배경어 경계값 [정책 필요] */}
                {c.kind === "center" ? <Badge tone="blue">중심어</Badge> : <Badge>배경어</Badge>}
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
      {core.length === 0 && <p className="m-0 py-4 text-center text-[13px] text-muted">분석할 수집 데이터가 없습니다 [문구 확인 필요]</p>}
    </Card>
  );
}

function RisingCard({ rising }: { rising: AnalysisOverview["rising"] }) {
  return (
    <Card data-ui-id="ANALYSIS-001-U05" data-func-id="FN-ANL-002" className="flex flex-col gap-2.5">
      <CardTitle>급상승 키워드</CardTitle>
      <p className="m-0 mb-1.5 text-[13px] text-muted">최근 7일 등장 글 수 ÷ 직전 4주 주평균</p>
      {rising.map((r) => (
        <div key={r.w} className="flex items-center gap-3 border-b border-line-soft py-2.5">
          <span className="flex-1">{r.w}</span>
          <span className="text-[13px] text-ink-2">{r.n}건</span>
          <Badge tone="orange" strong>
            ▲ {r.x}배
          </Badge>
        </div>
      ))}
      {rising.length === 0 && <p className="m-0 py-4 text-center text-[13px] text-muted">급상승 키워드가 없습니다 [문구 확인 필요]</p>}
    </Card>
  );
}

const HIT_PARTS = [
  { key: "main", label: "주제 기사 — 키워드가 주된 내용", short: "주된 내용", color: "bg-rel-main" },
  { key: "partial", label: "부분 언급 — 일부 단락만 다룸", short: "일부만 다룸", color: "bg-rel-partial" },
  { key: "passing", label: "스쳐 지나감 — 한두 번 언급", short: "한두 번 언급", color: "bg-rel-passing" },
] as const;

function HitCard({ hit }: { hit: AnalysisOverview["hit"] }) {
  return (
    <Card data-ui-id="ANALYSIS-001-U06" data-func-id="FN-ANL-003" className="flex flex-col gap-3.5">
      <CardTitle>키워드별 수집 적중도</CardTitle>
      <p className="m-0 text-[13px] leading-relaxed text-muted">
        검색 결과에는 키워드가 한 번만 나와도 포함됩니다. 모은 글 중 그 키워드가 실제로 주된 내용인 글이 얼마나 되는지 봅니다
      </p>
      <div className="flex flex-wrap gap-4 text-xs text-ink-2">
        {HIT_PARTS.map((p) => (
          <span key={p.key} className="flex items-center gap-1.5">
            <span className={cx("size-2.5 rounded-sm", p.color)} />
            {p.label}
          </span>
        ))}
      </div>
      {hit.map((h) => {
        const summary = HIT_PARTS.map((p) => `${p.short} ${h[p.key]}%`).join(" · ");
        return (
          <div key={h.kw} className="flex flex-col gap-2 border-b border-line-soft py-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm">
                <strong>{h.kw}</strong> 로 모은 글 {h.n}건
              </span>
              {/* 권장 배지 기준 [정책 필요] — MOCK: 스쳐 지나감 50% 이상 */}
              {h.warn && (
                <Badge tone="orange" strong>
                  키워드 수정 권장
                </Badge>
              )}
            </div>
            <div role="img" aria-label={summary} className="flex h-3 gap-0.5 overflow-hidden rounded-md">
              {HIT_PARTS.filter((p) => h[p.key] > 0).map((p) => (
                <span key={p.key} title={`${p.short} ${h[p.key]}%`} className={p.color} style={{ flex: `${h[p.key]} 1 0` }} />
              ))}
            </div>
            <span className="text-xs text-ink-2">{summary}</span>
          </div>
        );
      })}
      {hit.length === 0 && <p className="m-0 py-4 text-center text-[13px] text-muted">등록된 뉴스 키워드가 없습니다 [문구 확인 필요]</p>}
      <p className="m-0 text-[13px] leading-relaxed text-ink-2">
        &apos;한두 번 언급&apos;이 많으면 키워드가 너무 넓거나 다른 뜻으로 쓰이는 경우 → 키워드를 좁히거나 바꾸세요
      </p>
    </Card>
  );
}

function RelatedCard() {
  const { data: newsSources } = useApiData(() => api.listSources("news"));
  const [srcId, setSrcId] = useState<string | null>(null);
  const [kw, setKw] = useState<string | null>(null);
  const [openChip, setOpenChip] = useState<number | null>(null);

  const src: Source | undefined = newsSources?.find((s) => s.id === srcId) ?? newsSources?.[0];
  const kwOptions = src?.keywords?.map((k) => k.kw) ?? [];
  const keyword = kw && kwOptions.includes(kw) ? kw : (kwOptions[0] ?? "");

  const { data: words, reload } = useApiData(
    () => (src && keyword ? api.getRelatedWords(src.id, keyword) : Promise.resolve([])),
    `${src?.id}|${keyword}`,
  );

  if (newsSources && newsSources.length === 0) {
    return (
      <Card data-ui-id="ANALYSIS-001-U07" data-func-id="FN-ANL-004" className="flex flex-col gap-3.5">
        <CardTitle>연관어</CardTitle>
        <p className="m-0 py-4 text-center text-[13px] text-muted">
          뉴스 키워드 소스가 없습니다. 연관어는 뉴스 키워드로 모은 글에서 찾습니다 [문구 확인 필요]
        </p>
      </Card>
    );
  }

  return (
    <Card data-ui-id="ANALYSIS-001-U07" data-func-id="FN-ANL-004" className="flex flex-col gap-3.5">
      <CardTitle>연관어</CardTitle>
      <div className="grid grid-cols-2 gap-3">
        <Field label="기준 소스">
          <Select
            value={src?.id ?? ""}
            onChange={(e) => {
              setSrcId(e.target.value);
              setKw(null);
              setOpenChip(null);
            }}
          >
            {newsSources?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="기준 키워드">
          <Select
            value={keyword}
            onChange={(e) => {
              setKw(e.target.value);
              setOpenChip(null);
            }}
          >
            {kwOptions.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <p className="m-0 text-[13px] text-muted">이 키워드로 모은 글에 함께 자주 나온 단어 (함께 나온 글 수 순)</p>
      {words && src && (
        <RelatedChips
          words={words}
          source={src}
          open={openChip}
          setOpen={setOpenChip}
          onChanged={() => reload("quiet")}
        />
      )}
      {words?.length === 0 && <p className="m-0 text-[13px] text-muted">연관어가 없습니다 [문구 확인 필요]</p>}
      <p className="m-0 text-[13px] text-muted">
        추가한 검색 키워드는 수집 소스 › &apos;{src?.name ?? "[소스 이름]"}&apos; 편집 화면의 키워드 목록에서 확인합니다
      </p>
    </Card>
  );
}

function RelatedChips({
  words,
  source,
  open,
  setOpen,
  onChanged,
}: {
  words: RelatedWord[];
  source: Source;
  open: number | null;
  setOpen: (i: number | null) => void;
  onChanged: () => void;
}) {
  const router = useRouter();
  const toast = useToast();
  const wrap = useRef<HTMLDivElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);

  // Esc·바깥 클릭으로 닫기 [추정], 열리면 첫 항목에 포커스
  useEffect(() => {
    if (open == null) return;
    menu.current?.querySelector<HTMLButtonElement>("button:not(:disabled)")?.focus();
    const onDown = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(null);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(null);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, setOpen]);

  const word = open != null ? words[open] : null;

  // FUNC: FN-ANL-005 — 이동 여부 vs 토스트만 [확인 필요] → 기획서 동작 열 기준 이동
  const run = async (action: () => Promise<void>, message: string, href: string) => {
    setBusy(true);
    try {
      await action();
      setOpen(null);
      onChanged();
      toast(message);
      router.push(href);
    } catch {
      toast("처리하지 못했습니다 [문구 확인 필요]");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div ref={wrap} className="relative">
      <div className="flex flex-wrap gap-2">
        {words.map((r, i) => {
          const on = open === i;
          return (
            <button
              key={r.w}
              type="button"
              aria-haspopup="menu"
              aria-expanded={on}
              onClick={() => setOpen(on ? null : i)}
              className={cx(
                "inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13px] text-ink",
                on ? "border-2 border-primary bg-nav-active" : "m-px border border-field bg-surface hover:bg-hover",
              )}
            >
              {r.w} <span className="text-xs text-muted">{r.n}</span>
            </button>
          );
        })}
      </div>

      {word && (
        // ANALYSIS-001-P01 연관어 액션 메뉴
        <div
          ref={menu}
          data-screen-id="ANALYSIS-001-P01"
          role="menu"
          aria-label={`'${word.w}' 작업`}
          className="absolute top-[calc(100%+8px)] left-0 z-20 flex w-[300px] max-w-full flex-col rounded-[10px] border border-line bg-surface p-1.5 shadow-[0_10px_30px_rgba(0,0,0,.12)]"
        >
          <MenuItem
            uiId="ANALYSIS-001-P01-U01"
            title="검색 키워드로 추가"
            desc={word.isKeyword ? "이미 이 소스의 검색 키워드입니다 [추정]" : `'${source.name}' 소스가 이 단어로도 검색`}
            disabled={word.isKeyword || busy}
            onClick={() =>
              run(
                () => api.addSourceKeyword(source.id, word.w),
                `'${word.w}'을(를) '${source.name}' 검색 키워드에 추가했습니다`,
                `/sources/${source.id}/edit`,
              )
            }
          />
          <MenuItem
            uiId="ANALYSIS-001-P01-U02"
            title="불용어로 등록"
            desc={word.isStopword ? "이미 불용어에 있습니다 [추정]" : "의미 없는 단어면 순위에서 제외"}
            disabled={word.isStopword || busy}
            onClick={() => run(() => api.addStopword(word.w), `'${word.w}'을(를) 불용어로 등록했습니다`, "/dictionary")}
          />
          {/* 검색어 적용 [추정] */}
          <MenuItem
            uiId="ANALYSIS-001-P01-U03"
            title="이 단어가 나온 글 보기"
            disabled={busy}
            onClick={() => router.push(`/contents?q=${encodeURIComponent(word.w)}`)}
          />
        </div>
      )}
    </div>
  );
}

function MenuItem({
  uiId,
  title,
  desc,
  disabled,
  onClick,
}: {
  uiId: string;
  title: string;
  desc?: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      data-ui-id={uiId}
      disabled={disabled}
      onClick={onClick}
      className="flex flex-col gap-1 rounded-md border-none bg-transparent p-3 text-left whitespace-normal hover:bg-canvas"
    >
      <strong className="text-sm">{title}</strong>
      {desc && <span className="text-xs text-ink-2">{desc}</span>}
    </button>
  );
}

function TrendCard() {
  const [days, setDays] = useState<"30" | "90">("30");
  const { data, error, stale } = useApiData(() => api.getDailyCounts(Number(days)), days);

  return (
    <Card data-ui-id="ANALYSIS-001-U08" data-func-id="FN-ANL-006" className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <CardTitle>일별 수집 추이</CardTitle>
        <SegmentedTabs mode="radio" size="md" label="추이 기간" items={CHART_DAYS} value={days} onChange={setDays} />
      </div>
      {error ? (
        <p className="m-0 py-8 text-center text-[13px] text-muted">추이를 불러오지 못했습니다 [문구 확인 필요]</p>
      ) : !data ? (
        <div className="h-[170px] animate-pulse-soft rounded-md bg-subtle" />
      ) : (
        <div aria-busy={stale} className={cx("transition-opacity", stale && "opacity-60")}>
          <DailyChart data={data} days={Number(days)} />
        </div>
      )}
    </Card>
  );
}
