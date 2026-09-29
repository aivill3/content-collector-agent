import { cx } from "@/lib/cx";

/**
 * 번호가 붙은 폼 카드.
 * collapsible 이면 '접기' 버튼이 생기고, 접힌 상태에서는 초록 번호 + 요약 한 줄만 보인다 (게시판 수동 설정).
 */
export function FormSection({
  n,
  title,
  collapsible = false,
  open = true,
  onToggle,
  summary,
  summaryUiId,
  className,
  children,
  ...rest
}: {
  n: number;
  title: string;
  collapsible?: boolean;
  open?: boolean;
  onToggle?: () => void;
  summary?: string;
  summaryUiId?: string;
} & React.HTMLAttributes<HTMLElement>) {
  if (collapsible && !open) {
    return (
      <section
        data-ui-id={summaryUiId}
        className="flex flex-wrap items-center gap-3.5 rounded-card border border-line bg-surface px-6 py-[18px]"
      >
        <StepNumber n={n} done />
        <h2 className="m-0 text-base font-bold">{title}</h2>
        <span className="min-w-[200px] flex-1 text-[13px] text-ink-2">{summary}</span>
        <ToggleButton expanded={false} onClick={onToggle}>
          펼치기
        </ToggleButton>
      </section>
    );
  }
  return (
    <section className={cx("flex flex-col gap-4 rounded-card border border-line bg-surface p-6", className)} {...rest}>
      <div className="flex items-center gap-2.5">
        <StepNumber n={n} />
        <h2 className="m-0 text-base font-bold">{title}</h2>
        {collapsible && (
          <ToggleButton expanded onClick={onToggle} className="ml-auto">
            접기
          </ToggleButton>
        )}
      </div>
      {children}
    </section>
  );
}

function StepNumber({ n, done = false }: { n: number; done?: boolean }) {
  return (
    <span
      className={cx(
        "flex size-[26px] flex-none items-center justify-center rounded-full text-xs font-bold",
        done ? "bg-success-soft text-success" : "bg-primary-soft text-primary",
      )}
    >
      {n}
    </span>
  );
}

function ToggleButton({
  expanded,
  onClick,
  className,
  children,
}: {
  expanded: boolean;
  onClick?: () => void;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-expanded={expanded}
      onClick={onClick}
      className={cx("border-none bg-transparent text-sm font-bold text-primary", className)}
    >
      {children}
    </button>
  );
}

/** 필드를 2~3열로 늘어놓는 격자 */
export function FieldGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">{children}</div>;
}
