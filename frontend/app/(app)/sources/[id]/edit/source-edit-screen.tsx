"use client";

import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useApiData } from "@/lib/use-api-data";
import { SourceForm } from "../../_form/source-form";
import type { BoardMode } from "../../_form/values";

export function SourceEditScreen({ id, mode }: { id: string; mode: BoardMode }) {
  const { data, error, loading, reload } = useApiData(() => api.getSource(id), id);

  if (loading) return <PageSkeleton />;
  if (error) return <ErrorState onRetry={() => reload("full")} />;
  if (!data) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="소스 편집" />
        <div role="alert" className="flex flex-col items-start gap-2.5 rounded-card border border-line bg-surface p-8">
          <strong>소스를 찾을 수 없습니다</strong>
          <span className="text-[13px] text-muted">[확인 필요] 삭제된 소스 처리 정책 미정</span>
          <Link href="/sources" className="font-semibold">
            ← 수집 소스
          </Link>
        </div>
      </div>
    );
  }
  // 불러온 값으로 폼을 시작한다. 다른 소스로 넘어가면 새로 시작하도록 key 를 둔다
  return <SourceForm key={data.id} type={data.type} mode={mode} source={data} />;
}
