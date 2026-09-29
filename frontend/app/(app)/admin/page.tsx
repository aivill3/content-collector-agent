import type { Metadata } from "next";
import { AdminScreen } from "./admin-screen";

export const metadata: Metadata = { title: "관리자 · 콘텐츠 수집 Agent" };

// ADMIN-001 관리자
export default function AdminPage() {
  return <AdminScreen />;
}
