import type { Metadata } from "next";
import { DashboardScreen } from "./dashboard-screen";

export const metadata: Metadata = { title: "대시보드 · 콘텐츠 수집 Agent" };

export default function DashboardPage() {
  return <DashboardScreen />;
}
