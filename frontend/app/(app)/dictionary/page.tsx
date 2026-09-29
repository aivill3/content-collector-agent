import type { Metadata } from "next";
import { DictionaryScreen } from "./dictionary-screen";

export const metadata: Metadata = { title: "사전 · 콘텐츠 수집 Agent" };

// SETTING-002 불용어 / SETTING-003 사용자 사전 (?tab=user)
export default async function DictionaryPage({ searchParams }: PageProps<"/dictionary">) {
  const { tab } = await searchParams;
  const kind = tab === "user" ? "compounds" : "stopwords";
  // 탭을 바꾸면 검색·선택·입력을 새로 시작한다
  return <DictionaryScreen key={kind} kind={kind} />;
}
