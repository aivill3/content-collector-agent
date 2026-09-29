import Link from "next/link";
import { Badge } from "@/components/ui/badge";

// 없는 주소 — 문구 [문구 확인 필요]
export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="flex w-full max-w-[560px] flex-col items-start gap-3 rounded-card border border-line bg-surface p-8">
        <Badge>404</Badge>
        <h1 className="m-0 text-lg font-bold">페이지를 찾을 수 없습니다</h1>
        <p className="m-0 text-[13px] text-muted">주소가 바뀌었거나 삭제된 페이지입니다. [문구 확인 필요]</p>
        <Link href="/" className="font-semibold">
          대시보드로 이동
        </Link>
      </div>
    </main>
  );
}
