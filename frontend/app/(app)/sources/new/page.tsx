import type { Metadata } from "next";
import type { SourceType } from "@/lib/types";
import { SourceForm } from "../_form/source-form";

export const metadata: Metadata = { title: "소스 추가 · 콘텐츠 수집 Agent" };

const TYPES: SourceType[] = ["news", "board", "url"];

// SOURCE-002~005 소스 추가 — ?type=news|board|url, 게시판은 &mode=manual 이면 수동 설정
export default async function NewSourcePage({ searchParams }: PageProps<"/sources/new">) {
  const { type, mode } = await searchParams;
  const t = TYPES.find((x) => x === type) ?? "news";
  return <SourceForm type={t} mode={mode === "manual" ? "manual" : "auto"} source={null} />;
}
