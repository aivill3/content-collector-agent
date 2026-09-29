/** 요약 숫자 카드 (대시보드·관리자) — 이름 · 큰 숫자 · 보조 설명 */
export function StatCard({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 rounded-card border border-line bg-surface p-6">
      <span className="text-[13px] text-ink-2">{label}</span>
      <span className="font-mono text-[32px] font-semibold tracking-[-0.5px]">{value}</span>
      {sub && <span className="text-[13px] text-muted">{sub}</span>}
    </div>
  );
}

/** 요약 카드 여러 장을 폭에 맞춰 늘어놓는 격자 */
export function StatGrid({ label, children, ...rest }: React.HTMLAttributes<HTMLElement> & { label: string }) {
  return (
    <section aria-label={label} className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,150px),1fr))] gap-3 md:gap-6" {...rest}>
      {children}
    </section>
  );
}
