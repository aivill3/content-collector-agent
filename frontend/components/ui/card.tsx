import { cx } from "@/lib/cx";

export function Card({ className, ...rest }: React.HTMLAttributes<HTMLElement>) {
  return <section className={cx("rounded-card border border-line bg-surface p-6", className)} {...rest} />;
}

export function CardTitle({ className, ...rest }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cx("m-0 text-base font-bold", className)} {...rest} />;
}
