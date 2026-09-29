import Link from "next/link";
import { cx } from "@/lib/cx";

/** 밑줄 탭 목록. 탭 사이 간격은 className 으로 (gap-6 / gap-7) */
export function UnderlineTabs({ label, className, ...rest }: React.HTMLAttributes<HTMLDivElement> & { label: string }) {
  return <div role="tablist" aria-label={label} className={cx("flex border-b border-line", className)} {...rest} />;
}

type TabProps = {
  active: boolean;
  /** 선택되지 않은 탭도 굵게 (수집 소스 유형 탭) */
  bold?: boolean;
  children: React.ReactNode;
} & ({ href: string; onClick?: never } | { href?: never; onClick: () => void });

/** href 가 있으면 링크(URL 로 탭 상태를 남길 때), 없으면 버튼 */
export function UnderlineTab({ active, bold = false, href, onClick, children }: TabProps) {
  const className = cx(
    "-mb-px border-0 border-b-2 bg-transparent px-0.5 py-2.5 text-sm hover:no-underline",
    active ? "border-primary text-ink hover:text-ink" : "border-transparent text-ink-2 hover:text-ink-2",
    active || bold ? "font-bold" : "font-medium",
  );
  if (href) {
    return (
      <Link href={href} scroll={false} role="tab" aria-selected={active} className={className}>
        {children}
      </Link>
    );
  }
  return (
    <button type="button" role="tab" aria-selected={active} onClick={onClick} className={className}>
      {children}
    </button>
  );
}
