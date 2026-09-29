import type { Metadata } from "next";
import { ContentListScreen } from "./content-list-screen";

export const metadata: Metadata = { title: "콘텐츠 · 콘텐츠 수집 Agent" };

// CONTENT-001 콘텐츠 목록
// ?q= 는 키워드 분석의 "이 단어가 나온 글 보기"에서 넘어올 때 쓴다 (FLOW-014)
export default async function ContentsPage({ searchParams }: PageProps<"/contents">) {
  const { q } = await searchParams;
  const initialQ = typeof q === "string" ? q : "";
  // 다른 검색어로 다시 들어오면 필터를 새로 시작한다
  return <ContentListScreen key={initialQ} initialQ={initialQ} />;
}
