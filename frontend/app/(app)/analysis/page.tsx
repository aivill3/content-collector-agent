import type { Metadata } from "next";
import { AnalysisScreen } from "./analysis-screen";

export const metadata: Metadata = { title: "키워드 분석 · 콘텐츠 수집 Agent" };

// ANALYSIS-001 키워드 분석 (+P01 연관어 메뉴)
export default function AnalysisPage() {
  return <AnalysisScreen />;
}
