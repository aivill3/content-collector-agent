import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/** 화면 데이터를 불러오는 동안의 스켈레톤 (시안 공통 Loading) */
export function PageSkeleton() {
  return (
    <div aria-busy="true" aria-label="불러오는 중" className="flex animate-pulse-soft flex-col gap-5">
      <div className="h-[30px] w-[220px] rounded-md bg-line" />
      <div className="h-3.5 w-full max-w-[380px] rounded-md bg-line" />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-6">
        <div className="h-[140px] rounded-card border border-line bg-surface" />
        <div className="h-[140px] rounded-card border border-line bg-surface" />
        <div className="h-[140px] rounded-card border border-line bg-surface" />
      </div>
      <div className="h-[360px] rounded-card border border-line bg-surface" />
    </div>
  );
}

/** 공통 오류 상태 [문구 확인 필요] */
export function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="mx-auto my-20 flex max-w-[560px] flex-col items-start gap-3 rounded-card border border-line bg-surface p-8"
    >
      <Badge tone="orange">오류</Badge>
      <h2 className="m-0 text-lg font-bold">데이터를 불러오지 못했습니다</h2>
      <p className="m-0 text-[13px] text-muted">[문구 확인 필요] 네트워크·서버 오류 시 공통 안내.</p>
      <Button size="sm" onClick={onRetry}>
        다시 시도
      </Button>
    </div>
  );
}

/** 빈 상태 카드 [문구 확인 필요] */
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card border border-line bg-surface p-12 text-center">
      <h2 className="m-0 text-lg font-bold">{title}</h2>
      {description && <p className="m-0 text-[13px] text-muted">{description}</p>}
      {action}
    </div>
  );
}

/** 권한 없음 — 멤버가 관리자 화면에 들어왔을 때 [추정] / 메뉴 숨김 vs 안내 정책 [확인 필요] */
export function DeniedState({ title, description }: { title: string; description?: string }) {
  return (
    <div
      role="alert"
      className="mx-auto my-20 flex max-w-[560px] flex-col items-start gap-3 rounded-card border border-line bg-surface p-8"
    >
      <Badge>권한 없음</Badge>
      <h2 className="m-0 text-lg font-bold">{title}</h2>
      {description && <p className="m-0 text-[13px] text-muted">{description}</p>}
      <Link href="/" className="font-semibold">
        대시보드로 이동
      </Link>
    </div>
  );
}
