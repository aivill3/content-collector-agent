"use client";

import { cx } from "@/lib/cx";

const base = "h-9 rounded-control border px-3 text-sm";

/** 1 · 현재 앞뒤 한 쪽 · 마지막만 보이고 나머지는 … (와이어프레임 '1 2 … N') */
function pageList(page: number, pageCount: number): (number | "gap")[] {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, i) => i + 1);
  const keep = new Set([1, pageCount, page - 1, page, page + 1].filter((n) => n >= 1 && n <= pageCount));
  const out: (number | "gap")[] = [];
  let prev = 0;
  for (const n of [...keep].sort((a, b) => a - b)) {
    if (n - prev > 1) out.push("gap");
    out.push(n);
    prev = n;
  }
  return out;
}

export function Pagination({
  page,
  pageCount,
  onChange,
}: {
  page: number;
  pageCount: number;
  onChange: (page: number) => void;
}) {
  return (
    <nav aria-label="페이지" className="flex gap-1.5">
      <button
        type="button"
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className={cx(base, "min-w-12 border-field bg-surface px-3.5 font-semibold")}
      >
        이전
      </button>
      {pageList(page, pageCount).map((n, i) => {
        if (n === "gap") {
          return (
            <span key={`gap-${i}`} aria-hidden="true" className="flex h-9 min-w-10 items-center justify-center font-bold text-ink-2">
              …
            </span>
          );
        }
        const on = n === page;
        return (
          <button
            key={n}
            type="button"
            aria-current={on ? "page" : undefined}
            onClick={() => onChange(n)}
            className={cx(
              base,
              "min-w-10 font-bold",
              on ? "border-primary bg-nav-active text-primary" : "border-field bg-surface text-ink",
            )}
          >
            {n}
          </button>
        );
      })}
      <button
        type="button"
        onClick={() => onChange(page + 1)}
        disabled={page >= pageCount}
        className={cx(base, "min-w-12 border-field bg-surface px-3.5 font-semibold")}
      >
        다음
      </button>
    </nav>
  );
}
