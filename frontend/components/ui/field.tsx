import { cx } from "@/lib/cx";

const control =
  "w-full rounded-control border border-field bg-surface text-sm font-normal text-ink outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(42,85,153,.15)] disabled:bg-hover";

/** 텍스트 입력 — 기본 40px, 로그인처럼 큰 입력은 className 으로 h-11 */
export function Input({ className, ...rest }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cx(control, "h-10 px-3", className)} {...rest} />;
}

export function Select({ className, ...rest }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cx(control, "h-10 px-2.5", className)} {...rest} />;
}

export function Textarea({ className, ...rest }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cx(control, "resize-y p-3 leading-normal", className)} {...rest} />;
}

/** 입력 아래 오류 문구 — 자리를 차지하지 않도록 비어 있으면 그리지 않는다 */
export function FieldError({ children }: { children?: React.ReactNode }) {
  if (!children) return null;
  return <span className="text-xs font-normal text-warn">{children}</span>;
}

/** 라벨이 위에 붙는 필드 묶음. hint 는 회색 안내, error 는 주황 오류 */
export function Field({
  label,
  hint,
  error,
  className,
  children,
}: {
  label: string;
  hint?: React.ReactNode;
  error?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <label className={cx("flex min-w-0 flex-col gap-2 text-[13px] font-semibold", className)}>
      {label}
      {children}
      {hint && <span className="text-xs font-normal text-muted">{hint}</span>}
      <FieldError>{error}</FieldError>
    </label>
  );
}

export function Checkbox({
  label,
  hint,
  className,
  ...rest
}: Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> & { label: string; hint?: string }) {
  return (
    <label className={cx("flex cursor-pointer flex-col gap-1", className)}>
      <span className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="m-0 size-[18px] accent-primary" {...rest} />
        {label}
      </span>
      {hint && <span className="ml-[26px] text-xs text-muted">{hint}</span>}
    </label>
  );
}
