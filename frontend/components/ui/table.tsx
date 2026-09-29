import { cx } from "@/lib/cx";

export function Table({ className, ...rest }: React.TableHTMLAttributes<HTMLTableElement>) {
  // relative: 머리칸의 sr-only 라벨(absolute)이 가로 스크롤 영역 밖으로 빠져 페이지 폭을 늘리지 않게 한다
  return <table className={cx("relative w-full border-collapse text-sm", className)} {...rest} />;
}

export function Th({ className, ...rest }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cx("border-b border-line-soft py-2 text-left text-xs font-medium text-ink-2", className)}
      {...rest}
    />
  );
}

export function Td({ className, ...rest }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cx("border-b border-line-soft py-[13px]", className)} {...rest} />;
}
