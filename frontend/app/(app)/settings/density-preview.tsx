"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { cx } from "@/lib/cx";
import { RELEVANCE_BADGE } from "@/lib/labels";
import type { Relevance, SettingsBundle } from "@/lib/types";

// FN-SET-006 변경 미리보기 — 1,000자당 밀도 분포와, 기준값에 따른 판정 건수 변화.
// MOCK 판정: 기준값 이상 = 주제 기사, 기준값의 1/2 이상 = 부분 언급, 그 미만 = 스쳐 지나감 (구간 분포로 근사)
// 구간은 시작값으로 판정한다 — 그래야 점선 오른쪽 막대가 정확히 '주제 기사'가 된다.
// 막대 색은 판정 결과 — 적중도 막대·관련도 배지와 같은 계열이다.

type Histogram = SettingsBundle["densityHistogram"];

const ORDER: Relevance[] = ["main", "partial", "passing"];
const COLOR: Record<Relevance, string> = { main: "bg-rel-main", partial: "bg-rel-partial", passing: "bg-rel-passing" };

function classOf(value: number, th: number): Relevance {
  return value >= th ? "main" : value >= th / 2 ? "partial" : "passing";
}

function classify(h: Histogram, th: number): Record<Relevance, number> {
  const out = { main: 0, partial: 0, passing: 0 };
  h.counts.forEach((n, i) => {
    out[classOf(i * h.binWidth, th)] += n;
  });
  return out;
}

export function DensityPreview({ hist, thSaved, thNow }: { hist: Histogram; thSaved: number; thNow: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const before = classify(hist, thSaved);
  const after = classify(hist, thNow);
  const total = hist.counts.reduce((a, b) => a + b, 0);
  const max = Math.max(1, ...hist.counts);
  const maxV = hist.counts.length * hist.binWidth;
  const linePos = Math.min(100, Math.max(0, (thNow / maxV) * 100));

  return (
    <>
      <p className="m-0 text-[13px] text-muted">최근 7일 수집분 {total}건 기준 · 저장 전 결과</p>
      {ORDER.map((r) => {
        const [label, tone] = RELEVANCE_BADGE[r];
        return (
          <div key={r} className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span className={cx("size-2.5 rounded-sm", COLOR[r])} aria-hidden="true" />
              <Badge tone={tone}>{label}</Badge>
            </span>
            <span className="font-mono text-sm tabular-nums">
              {before[r]} → <strong>{after[r]}</strong>
            </span>
          </div>
        );
      })}

      <strong className="mt-1 text-[13px]">1,000자당 밀도 분포</strong>
      <div className="relative">
        <div
          role="img"
          aria-label={`밀도 분포. 기준값 ${thNow} 이상 ${after.main}건, 부분 언급 ${after.partial}건, 스쳐 지나감 ${after.passing}건`}
          onPointerLeave={() => setHover(null)}
          className="relative flex h-[110px] items-end gap-1.5 border-b border-line"
        >
          {hist.counts.map((n, i) => {
            const cls = classOf(i * hist.binWidth, thNow);
            return (
              // 칸 전체가 가리키기 대상
              <div key={i} onPointerEnter={() => setHover(i)} className="flex h-full flex-1 items-end">
                <span
                  className={cx("block w-full rounded-t", COLOR[cls], hover === i && "brightness-110")}
                  style={{ height: `${(n / max) * 100}%` }}
                />
              </div>
            );
          })}
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 border-l-2 border-dashed border-primary"
            style={{ left: `${linePos}%` }}
          />
        </div>
        {hover != null && (
          <div
            aria-hidden="true"
            className={cx(
              "pointer-events-none absolute bottom-full z-10 mb-2 rounded-control border border-line bg-surface px-3 py-2 text-xs whitespace-nowrap shadow-[0_8px_24px_rgba(0,0,0,.12)]",
              hover < 3 ? "translate-x-0" : hover > hist.counts.length - 4 ? "-translate-x-full" : "-translate-x-1/2",
            )}
            style={{ left: `${((hover + 0.5) / hist.counts.length) * 100}%` }}
          >
            <div className="font-semibold text-ink">
              밀도 {(hover * hist.binWidth).toFixed(2)}~{((hover + 1) * hist.binWidth).toFixed(2)}
            </div>
            <div className="text-ink-2">
              {hist.counts[hover]}건 · {RELEVANCE_BADGE[classOf(hover * hist.binWidth, thNow)][0]}
            </div>
          </div>
        )}
      </div>
      <div className="flex justify-between font-mono text-[11px] text-muted">
        <span>0</span>
        <span>{maxV.toFixed(1)}</span>
      </div>
      <p className="m-0 text-xs leading-[1.55] text-muted">
        점선 = 현재 기준값 ({thNow.toFixed(1)}). 오른쪽 막대가 &apos;주제 기사&apos;로 판정됩니다
      </p>
    </>
  );
}
