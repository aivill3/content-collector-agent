"use client";

import { cx } from "@/lib/cx";

/**
 * 회색 바탕 안에서 선택된 항목만 흰색으로 뜨는 선택기.
 * mode="tabs"  대시보드 수집 경로처럼 내용을 바꾸는 탭 (role=tab, 36px)
 * mode="radio" 콘텐츠 관련도 필터처럼 값 하나를 고르는 라디오 (role=radio, 32px)
 * size 로 높이를 바꿀 수 있다 (키워드 분석 기간 라디오는 36px)
 */
export function SegmentedTabs<T extends string>({
  items,
  value,
  onChange,
  label,
  labelledBy,
  mode = "tabs",
  size,
  className,
  ...rest
}: {
  items: readonly (readonly [T, string])[];
  value: T;
  onChange: (value: T) => void;
  label?: string;
  labelledBy?: string;
  mode?: "tabs" | "radio";
  size?: "sm" | "md";
  className?: string;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "onChange">) {
  const radio = mode === "radio";
  const small = (size ?? (radio ? "sm" : "md")) === "sm";
  return (
    <div
      role={radio ? "radiogroup" : "tablist"}
      aria-label={label}
      aria-labelledby={labelledBy}
      className={cx("flex rounded-[10px] bg-subtle p-1", radio ? "gap-0.5 overflow-x-auto" : "gap-1", className)}
      {...rest}
    >
      {items.map(([id, text]) => {
        const on = id === value;
        return (
          <button
            key={id}
            type="button"
            role={radio ? "radio" : "tab"}
            aria-checked={radio ? on : undefined}
            aria-selected={radio ? undefined : on}
            onClick={() => onChange(id)}
            className={cx(
              "rounded-control border-none text-sm",
              small ? "h-8 px-3" : "h-9 px-3.5",
              on ? "bg-surface font-bold text-ink shadow-[0_1px_2px_rgba(0,0,0,.08)]" : "bg-transparent font-medium text-ink-2",
            )}
          >
            {text}
          </button>
        );
      })}
    </div>
  );
}
