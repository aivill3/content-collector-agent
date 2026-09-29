import type { Metadata } from "next";
import { ContentDetailScreen } from "./content-detail-screen";

export const metadata: Metadata = { title: "콘텐츠 상세 · 콘텐츠 수집 Agent" };

// CONTENT-002 콘텐츠 상세 · 정제 본문 / CONTENT-003 원본 본문 (?tab=raw)
export default async function ContentDetailPage({ params, searchParams }: PageProps<"/contents/[id]">) {
  const [{ id }, { tab }] = await Promise.all([params, searchParams]);
  return <ContentDetailScreen id={id} tab={tab === "raw" ? "raw" : "clean"} />;
}
