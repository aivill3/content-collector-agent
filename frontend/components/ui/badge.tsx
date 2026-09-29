import { cx } from "@/lib/cx";

export type BadgeTone = "gray" | "green" | "orange" | "blue";

const TONE: Record<BadgeTone, string> = {
  gray: "bg-subtle text-ink-2",
  green: "bg-success-soft text-success",
  orange: "bg-warn-soft text-warn",
  blue: "bg-primary-soft text-primary",
};

export function Badge({
  tone = "gray",
  strong = false,
  className,
  children,
}: {
  tone?: BadgeTone;
  /** NEW 배지처럼 굵게 */
  strong?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs",
        strong ? "font-bold" : "font-semibold",
        TONE[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
