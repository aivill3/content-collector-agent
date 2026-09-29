import Link from "next/link";
import { cx } from "@/lib/cx";

type Variant = "primary" | "secondary";
type Size = "sm" | "md" | "lg";

const VARIANT: Record<Variant, string> = {
  primary: "border-none bg-primary font-bold text-white hover:bg-primary-hover",
  secondary: "border border-field bg-surface font-semibold text-ink hover:bg-hover",
};

// sm 36px · md 44px · lg 48px (시안 버튼 높이)
const SIZE: Record<Size, string> = {
  sm: "h-9 px-3.5 text-sm",
  md: "h-11 px-4 text-sm",
  lg: "h-12 px-4 text-[15px]",
};

function classes(variant: Variant, size: Size, className?: string) {
  return cx(
    "inline-flex items-center justify-center gap-1.5 rounded-control transition-colors",
    VARIANT[variant],
    SIZE[size],
    className,
  );
}

type ButtonProps = React.ComponentProps<"button"> & { variant?: Variant; size?: Size };

export function Button({ variant = "secondary", size = "md", className, type = "button", ...rest }: ButtonProps) {
  return <button type={type} className={classes(variant, size, className)} {...rest} />;
}

type ButtonLinkProps = React.ComponentProps<typeof Link> & { variant?: Variant; size?: Size };

/** 버튼 모양의 링크 (화면 이동용) */
export function ButtonLink({ variant = "secondary", size = "md", className, ...rest }: ButtonLinkProps) {
  return <Link className={cx(classes(variant, size, className), "no-underline hover:no-underline")} {...rest} />;
}
