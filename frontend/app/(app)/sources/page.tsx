import type { Metadata } from "next";
import { SourceListScreen } from "./source-list-screen";

export const metadata: Metadata = { title: "수집 소스 · 콘텐츠 수집 Agent" };

// SOURCE-001 수집 소스
export default function SourcesPage() {
  return <SourceListScreen />;
}
