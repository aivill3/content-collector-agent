"use client";

import { useState } from "react";
import { Table, Td, Th } from "@/components/ui/table";
import { cx } from "@/lib/cx";
import type { DailyCount } from "@/lib/types";

// FN-ANL-006 일별 수집 추이 — 소스 유형별 누적 막대
// 막대에 올리면 그날의 유형별 건수가 툴팁으로 나오고, '표로 보기'로 모든 값을 볼 수 있다.

const SERIES = [
  { key: "news", label: "뉴스", color: "bg-series-news" },
  { key: "board", label: "게시판", color: "bg-series-board" },
  { key: "url", label: "URL", color: "bg-series-url" },
] as const;

const GAP = 2; // 누적 조각 사이 틈 (px)

/** MOCK 데이터에 날짜가 없어 오늘 기준 며칠 전으로 표시한다 */
const dayLabel = (daysAgo: number) => (daysAgo === 0 ? "오늘" : `${daysAgo}일 전`);

export function DailyChart({ data, days }: { data: DailyCount[]; days: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const total = (d: DailyCount) => d.news + d.board + d.url;
  const max = Math.max(1, ...data.map(total));

  if (data.every((d) => total(d) === 0)) {
    return <p className="m-0 py-12 text-center text-[13px] text-muted">이 기간에 수집한 글이 없습니다 [문구 확인 필요]</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="relative">
        <div
          role="img"
          aria-label={`최근 ${days}일 일별 수집 건수 누적 막대 그래프. 최대 ${max}건`}
          onPointerLeave={() => setHover(null)}
          className={cx("flex h-[170px] items-end border-b border-line", days > 30 ? "gap-0.5" : "gap-[3px]")}
        >
          {data.map((d, i) => {
            const parts = SERIES.filter((s) => d[s.key] > 0);
            const topKey = parts.at(-1)?.key;
            const gaps = Math.max(0, parts.length - 1) * GAP;
            return (
              // 칸 전체가 가리키기 대상 — 막대보다 넓다
              <div
                key={i}
                onPointerEnter={() => setHover(i)}
                className="flex h-full min-w-0 flex-1 flex-col-reverse"
                style={{ gap: GAP }}
              >
                {parts.map((s) => (
                  <span
                    key={s.key}
                    className={cx("block", s.color, s.key === topKey && "rounded-t", hover === i && "brightness-110")}
                    style={{ height: `calc((100% - ${gaps}px) * ${d[s.key] / max})` }}
                  />
                ))}
              </div>
            );
          })}
        </div>
        {hover != null && data[hover] && <Tooltip d={data[hover]} daysAgo={data.length - 1 - hover} x={(hover + 0.5) / data.length} />}
      </div>

      <div className="flex justify-between text-[11px] text-muted">
        <span>{dayLabel(data.length - 1)}</span>
        <span>오늘</span>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-xs text-ink-2">
        <span>최근 {days}일 · 소스 유형별 누적</span>
        {SERIES.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5">
            <span className={cx("size-2.5 rounded-sm", s.color)} />
            {s.label}
          </span>
        ))}
        <button
          type="button"
          aria-expanded={showTable}
          onClick={() => setShowTable((v) => !v)}
          className="ml-auto border-none bg-transparent p-0 text-xs font-semibold text-primary hover:underline"
        >
          {showTable ? "표 닫기" : "표로 보기"}
        </button>
      </div>

      {showTable && (
        <div className="max-h-72 overflow-y-auto">
          <Table>
            <thead className="sticky top-0 bg-surface">
              <tr>
                <Th>날짜</Th>
                {SERIES.map((s) => (
                  <Th key={s.key} className="text-right">
                    {s.label}
                  </Th>
                ))}
                <Th className="text-right">합계</Th>
              </tr>
            </thead>
            <tbody>
              {data
                .map((d, i) => ({ d, daysAgo: data.length - 1 - i }))
                .reverse()
                .map(({ d, daysAgo }) => (
                  <tr key={daysAgo}>
                    <Td className="py-2">{dayLabel(daysAgo)}</Td>
                    {SERIES.map((s) => (
                      <Td key={s.key} className="py-2 text-right font-mono text-[13px] tabular-nums">
                        {d[s.key]}
                      </Td>
                    ))}
                    <Td className="py-2 text-right font-mono text-[13px] font-semibold tabular-nums">{total(d)}</Td>
                  </tr>
                ))}
            </tbody>
          </Table>
        </div>
      )}
    </div>
  );
}

function Tooltip({ d, daysAgo, x }: { d: DailyCount; daysAgo: number; x: number }) {
  // 가장자리에서는 툴팁이 차트 밖으로 나가지 않게 기준점을 바꾼다
  const align = x < 0.15 ? "translate-x-0" : x > 0.85 ? "-translate-x-full" : "-translate-x-1/2";
  return (
    // 값은 '표로 보기'에도 있으므로 화면 낭독기에는 툴팁을 읽히지 않는다
    <div
      aria-hidden="true"
      className={cx(
        "pointer-events-none absolute bottom-full z-10 mb-2 min-w-[140px] rounded-control border border-line bg-surface px-3 py-2.5 text-xs shadow-[0_8px_24px_rgba(0,0,0,.12)]",
        align,
      )}
      style={{ left: `${x * 100}%` }}
    >
      <div className="mb-1.5 font-semibold text-ink">{dayLabel(daysAgo)}</div>
      {SERIES.map((s) => (
        <div key={s.key} className="flex items-center gap-2 py-0.5 text-ink-2">
          <span className={cx("size-2 rounded-sm", s.color)} />
          <span className="flex-1">{s.label}</span>
          <span className="font-mono tabular-nums text-ink">{d[s.key]}</span>
        </div>
      ))}
      <div className="mt-1 flex justify-between border-t border-line-soft pt-1 font-semibold text-ink">
        <span>합계</span>
        <span className="font-mono tabular-nums">{d.news + d.board + d.url}</span>
      </div>
    </div>
  );
}
