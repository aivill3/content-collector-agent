import type { Metadata } from "next";
import { JobScreen } from "./job-screen";

export const metadata: Metadata = { title: "수집 작업 · 콘텐츠 수집 Agent" };

// JOB-001 수집 작업
export default function JobsPage() {
  return <JobScreen />;
}
