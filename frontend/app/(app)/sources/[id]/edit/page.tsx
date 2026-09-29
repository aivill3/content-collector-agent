import type { Metadata } from "next";
import { SourceEditScreen } from "./source-edit-screen";

export const metadata: Metadata = { title: "소스 편집 · 콘텐츠 수집 Agent" };

// 소스 편집 — 추가 화면과 같은 폼. 게시판은 ?mode=manual 이면 수동 설정, auto 는 자동 탐지 (수집 작업의 '탐지 다시 실행')
export default async function EditSourcePage({ params, searchParams }: PageProps<"/sources/[id]/edit">) {
  const [{ id }, { mode }] = await Promise.all([params, searchParams]);
  return <SourceEditScreen id={id} mode={mode === "manual" ? "manual" : "auto"} />;
}
