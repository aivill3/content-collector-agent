import { cx } from "@/lib/cx";

/** 켜기·끄기 스위치 (사전의 '적용' 열) */
export function Switch({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  /** 화면 낭독기용 이름 — 예: "기자 적용" */
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx(
        "relative h-[26px] w-11 rounded-full border-none p-0 transition-colors",
        checked ? "bg-primary" : "bg-field",
      )}
    >
      <span
        className={cx(
          "absolute top-[3px] size-5 rounded-full bg-white shadow-[0_1px_2px_rgba(0,0,0,.2)] transition-[left]",
          checked ? "left-[21px]" : "left-[3px]",
        )}
      />
    </button>
  );
}
