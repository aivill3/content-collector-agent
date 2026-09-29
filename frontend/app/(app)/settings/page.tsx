import type { Metadata } from "next";
import { SettingsScreen } from "./settings-screen";

export const metadata: Metadata = { title: "분석 설정 · 콘텐츠 수집 Agent" };

// SETTING-001 분석 설정
export default function SettingsPage() {
  return <SettingsScreen />;
}
