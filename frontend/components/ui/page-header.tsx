/** COMMON-001-U05 페이지 헤더 — 제목·설명·우측 버튼 */
export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header data-ui-id="COMMON-001-U05" className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex flex-col gap-2">
        <h1 className="m-0 text-[28px] font-bold">{title}</h1>
        {description && <p className="m-0 text-muted">{description}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </header>
  );
}
