import { AppShell } from "@/components/layout/app-shell";

// 로그인 후 화면 공통 레이아웃 (COMMON-001)
export default function AppLayout({ children }: LayoutProps<"/">) {
  return <AppShell>{children}</AppShell>;
}
