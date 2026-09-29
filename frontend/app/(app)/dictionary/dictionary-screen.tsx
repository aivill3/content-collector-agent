"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "@/components/layout/session";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { Switch } from "@/components/ui/switch";
import { Table, Td, Th } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { UnderlineTab, UnderlineTabs } from "@/components/ui/underline-tabs";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import { downloadBlob } from "@/lib/download";
import { useApiData } from "@/lib/use-api-data";
import type { DictEntry, DictKind, DictListParams, DictOrigin, SourceOption } from "@/lib/types";

// SETTING-002 불용어 / SETTING-003 사용자 사전

type Filters = Omit<DictListParams, "page">;

const ORIGINS: DictOrigin[] = ["직접 추가", "키워드 분석에서 추가", "CSV 가져오기", "시스템 공통"];

const UI = {
  stopwords: { screen: "SETTING-002", tabs: "SETTING-002-U01", add: "SETTING-002-U03", bulk: "SETTING-002-U04", tools: "SETTING-002-U05", selbar: "SETTING-002-U06", table: "SETTING-002-U07" },
  compounds: { screen: "SETTING-003", tabs: "SETTING-003-U01", add: "SETTING-003-U04", bulk: "SETTING-003-U05", tools: "SETTING-003-U06", selbar: "SETTING-003-U07", table: "SETTING-003-U08" },
} as const;

const DESC: Record<DictKind, string> = {
  compounds:
    "분석기가 두 단어로 쪼개는 복합어를 하나로 묶습니다. 예) '승단심사' → 승단 + 심사로 쪼개지지 않게 등록. 이미 수집한 글에는 재분석해야 반영됩니다",
  stopwords: "순위·밀도 집계에서 빼는 단어입니다. 거의 모든 글에 나와 의미가 없는 단어를 넣습니다. 저장하는 즉시 모든 화면에 반영됩니다",
};

export function DictionaryScreen({ kind }: { kind: DictKind }) {
  const toast = useToast();
  const confirm = useConfirm();
  const { role } = useSession();
  const isComp = kind === "compounds";
  const ui = UI[kind];

  const [filters, setFilters] = useState<Filters>({ q: "", origin: "all", target: "all", sort: "recent" });
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(1);
  // 페이지를 넘겨도 선택이 유지되도록 항목째 들고 있는다
  const [selected, setSelected] = useState<Map<string, DictEntry>>(new Map());
  const [reanalyzing, setReanalyzing] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(filters.q), 250);
    return () => clearTimeout(t);
  }, [filters.q]);

  const params: DictListParams = { ...filters, q: debouncedQ, page };
  const { data, error, loading, stale, reload } = useApiData(() => api.listDictionary(kind, params), JSON.stringify(params));
  const { data: sources } = useApiData(api.listSourceOptions);

  const updateFilters = (patch: Partial<Filters>) => {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  };
  const targetName = (id: string) => (id === "default" ? "내 기본값" : (sources?.find((s) => s.id === id)?.name ?? id));
  // 시스템 공통 삭제는 관리자만 (와이어프레임) — 서버도 한 번 더 확인한다
  const canDelete = (x: DictEntry) => x.origin !== "시스템 공통" || role === "admin";

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState onRetry={() => reload("full")} />;

  const pageItems = data.items;
  const allChecked = pageItems.length > 0 && pageItems.every((x) => selected.has(x.id));
  const toggleAll = (on: boolean) =>
    setSelected((prev) => {
      const next = new Map(prev);
      for (const x of pageItems) {
        if (on) next.set(x.id, x);
        else next.delete(x.id);
      }
      return next;
    });
  const toggleOne = (x: DictEntry, on: boolean) =>
    setSelected((prev) => {
      const next = new Map(prev);
      if (on) next.set(x.id, x);
      else next.delete(x.id);
      return next;
    });

  // FUNC: FN-DIC-004 — 클릭 즉시 저장 [추정]
  const setEnabled = async (ids: string[], on: boolean) => {
    try {
      await api.setDictEnabled(kind, ids, on);
      reload("quiet");
    } catch {
      toast("변경하지 못했습니다 [문구 확인 필요]");
    }
  };

  // 삭제 확인 대화상자는 와이어프레임에 없음 → 단건은 즉시, 선택 삭제만 확인 [확인 필요]
  const remove = async (ids: string[]) => {
    try {
      const r = await api.deleteDictEntries(kind, ids);
      setSelected(new Map());
      reload("quiet");
      return r;
    } catch {
      toast("삭제하지 못했습니다 [문구 확인 필요]");
      return null;
    }
  };

  const bulkDelete = () => {
    const targets = [...selected.values()];
    const deletable = targets.filter(canDelete);
    const skipped = targets.length - deletable.length;
    confirm({
      title: `${deletable.length}개를 삭제할까요?`,
      okLabel: "삭제",
      body: skipped
        ? `시스템 공통 ${skipped}개는 관리자만 삭제할 수 있어 제외됩니다. [확인 필요] 삭제 확인 정책 미정`
        : "[확인 필요] 삭제 확인 대화상자는 와이어프레임에 없어 추정 구현입니다.",
      onOk: async () => {
        const r = await remove(deletable.map((x) => x.id));
        if (r) toast(`${r.deleted}개를 삭제했습니다`);
      },
    });
  };

  // FUNC: FN-DIC-006
  const reanalyze = async () => {
    setReanalyzing(true);
    try {
      await api.reanalyzeRecent();
      reload("quiet");
      toast("최근 30일 수집분 재분석을 등록했습니다");
    } catch {
      toast("재분석을 등록하지 못했습니다 [문구 확인 필요]");
    } finally {
      setReanalyzing(false);
    }
  };

  return (
    <div data-screen-label="SETTING-002/003 사전" data-screen-id={ui.screen} className="flex flex-col gap-5">
      <PageHeader
        title="사전"
        description="불용어와 사용자 사전을 표로 관리합니다. 수백 개도 검색·필터로 찾고 한 번에 추가·삭제합니다"
      />
      <UnderlineTabs data-ui-id={ui.tabs} label="사전 종류" className="gap-7">
        <UnderlineTab href="/dictionary" active={!isComp} bold>
          불용어 {data.counts.stopwords}
        </UnderlineTab>
        <UnderlineTab href="/dictionary?tab=user" active={isComp} bold>
          사용자 사전 {data.counts.compounds}
        </UnderlineTab>
      </UnderlineTabs>
      <p className="m-0 text-[13px] text-ink-2">{DESC[kind]}</p>

      {isComp && data.pendingCount > 0 && (
        <div
          data-ui-id="SETTING-003-U03"
          data-func-id="FN-DIC-006"
          role="status"
          className="flex flex-wrap items-center gap-4 rounded-card border border-alert-line bg-alert px-5 py-3.5"
        >
          <span className="min-w-[260px] flex-1 text-sm">
            아직 반영되지 않은 변경 <strong>{data.pendingCount}건</strong> — 새로 수집하는 글에는 바로 적용되고, 기존 글은 재분석해야 합니다
          </span>
          {/* 30일 범위 선택 가능 여부 [확인 필요] */}
          <Button size="sm" onClick={reanalyze} disabled={reanalyzing}>
            {reanalyzing ? "재분석 요청 중…" : "최근 30일 재분석"}
          </Button>
        </div>
      )}

      <AddCard kind={kind} uiIds={ui} sources={sources ?? []} filters={{ ...filters, q: debouncedQ }} onAdded={() => {
        setPage(1);
        reload("quiet");
      }} />

      <section data-func-id="FN-DIC-001" className="flex flex-col gap-4 rounded-card border border-line bg-surface p-6">
        <div data-ui-id={ui.tools} className="flex flex-wrap gap-4">
          <Field label="목록 검색" className="flex-[2.4_1_240px]">
            <Input type="search" value={filters.q} onChange={(e) => updateFilters({ q: e.target.value })} />
          </Field>
          <Field label="출처" className="flex-[1_1_150px]">
            <Select value={filters.origin} onChange={(e) => updateFilters({ origin: e.target.value as Filters["origin"] })}>
              <option value="all">전체</option>
              {ORIGINS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="적용 대상" className="flex-[1_1_150px]">
            <Select value={filters.target} onChange={(e) => updateFilters({ target: e.target.value })}>
              <option value="all">전체</option>
              <option value="default">내 기본값</option>
              {sources?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          {/* 정렬 선택지 [확인 필요] */}
          <Field label="정렬" className="flex-[1_1_150px]">
            <Select value={filters.sort} onChange={(e) => updateFilters({ sort: e.target.value as Filters["sort"] })}>
              <option value="recent">최근 추가순</option>
              <option value="old">오래된순</option>
              <option value="abc">가나다순</option>
            </Select>
          </Field>
        </div>

        {selected.size > 0 && (
          <div
            data-ui-id={ui.selbar}
            data-func-id="FN-DIC-005"
            className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] bg-nav-active px-3.5 py-2.5"
          >
            <span className="text-sm font-bold text-primary">{selected.size}개 선택됨</span>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={async () => {
                  const n = selected.size;
                  await setEnabled([...selected.keys()], false);
                  setSelected(new Map());
                  toast(`${n}개 적용을 껐습니다`);
                }}
              >
                적용 끄기
              </Button>
              <Button size="sm" onClick={bulkDelete}>
                선택 삭제
              </Button>
            </div>
          </div>
        )}

        <div aria-busy={stale} className={cx("overflow-x-auto transition-opacity", stale && "opacity-60")}>
          <Table data-ui-id={ui.table} className="min-w-[820px]">
            <thead>
              <tr>
                <Th className="w-11 py-2.5">
                  <input
                    type="checkbox"
                    aria-label="이 페이지 전체 선택"
                    checked={allChecked}
                    onChange={(e) => toggleAll(e.target.checked)}
                    className="m-0 size-[18px] accent-primary"
                  />
                </Th>
                <Th className="py-2.5">{isComp ? "복합어" : "단어"}</Th>
                {isComp && <Th className="py-2.5">품사</Th>}
                <Th className="py-2.5">출처</Th>
                <Th className="py-2.5">적용 대상</Th>
                <Th className="py-2.5">추가일</Th>
                <Th className="py-2.5">적용</Th>
                <Th className="py-2.5">
                  <span className="sr-only">삭제</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map((x) => (
                <tr key={x.id}>
                  <Td className="py-3">
                    <input
                      type="checkbox"
                      aria-label={`${x.word} 선택`}
                      checked={selected.has(x.id)}
                      onChange={(e) => toggleOne(x, e.target.checked)}
                      className="m-0 size-[18px] accent-primary"
                    />
                  </Td>
                  <Td className="py-3 font-bold">
                    <span className="inline-flex items-center gap-2">
                      {x.word}
                      {isComp && x.pending && <Badge tone="orange">미반영</Badge>}
                    </span>
                  </Td>
                  {isComp && (
                    <Td className="py-3">
                      <Badge strong className="text-[11px]">
                        {x.pos}
                      </Badge>
                    </Td>
                  )}
                  <Td className="py-3">
                    <Badge tone={x.origin === "키워드 분석에서 추가" ? "blue" : "gray"}>{x.origin}</Badge>
                  </Td>
                  <Td className="py-3 text-ink-2">{targetName(x.target)}</Td>
                  <Td className="py-3 font-mono text-[13px]">{x.added}</Td>
                  <Td className="py-3">
                    <Switch checked={x.on} label={`${x.word} 적용`} onChange={(on) => setEnabled([x.id], on)} />
                  </Td>
                  <Td className="py-3">
                    {canDelete(x) ? (
                      <Button
                        size="sm"
                        className="px-4"
                        aria-label={`${x.word} 삭제`}
                        onClick={async () => {
                          const r = await remove([x.id]);
                          if (r?.deleted) toast(`'${x.word}'을(를) 삭제했습니다`);
                        }}
                      >
                        삭제
                      </Button>
                    ) : (
                      <span className="text-[13px] text-muted">관리자만</span>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
        {pageItems.length === 0 && (
          <p className="m-0 py-6 text-center text-[13px] text-muted">
            {data.counts[kind] ? "검색 결과가 없습니다 [문구 확인 필요]" : "등록된 단어가 없습니다 [문구 확인 필요]"}
          </p>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-[13px] text-muted">총 {data.total}개 · 50개씩 보기</span>
          <Pagination page={data.page} pageCount={data.pageCount} onChange={setPage} />
        </div>
      </section>
    </div>
  );
}

// FUNC: FN-DIC-002 한 개 추가 / FN-DIC-003 붙여넣기·CSV 가져오기·내보내기
function AddCard({
  kind,
  uiIds,
  sources,
  filters,
  onAdded,
}: {
  kind: DictKind;
  uiIds: { add: string; bulk: string };
  sources: SourceOption[];
  filters: Filters;
  onAdded: () => void;
}) {
  const toast = useToast();
  const isComp = kind === "compounds";
  const fileRef = useRef<HTMLInputElement>(null);
  const [word, setWord] = useState("");
  const [pos, setPos] = useState("NNP");
  const [target, setTarget] = useState("default");
  const [wordErr, setWordErr] = useState("");
  const [pasteOpen, setPasteOpen] = useState(false);
  const [paste, setPaste] = useState("");
  const [busy, setBusy] = useState(false);

  const add = async (words: { word: string; pos?: string }[], origin: DictOrigin) => {
    setBusy(true);
    try {
      const r = await api.addDictWords(kind, words, { target, origin, pos });
      if (r.added) onAdded();
      return r;
    } catch {
      toast("추가하지 못했습니다 [문구 확인 필요]");
      return null;
    } finally {
      setBusy(false);
    }
  };

  const addOne = async () => {
    const w = word.trim();
    if (!w) return setWordErr("단어를 입력하세요 [문구 확인 필요]");
    const r = await add([{ word: w }], "직접 추가");
    if (!r) return;
    if (!r.added) return setWordErr("이미 등록된 단어입니다 [추정]");
    setWord("");
    setWordErr("");
  };

  // 붙여넣기 UI 미정 [확인 필요] — 인라인 입력창으로 구현
  const addPasted = async () => {
    const words = paste.split(/[\n,]/).map((w) => w.trim()).filter(Boolean).map((w) => ({ word: w }));
    const r = await add(words, "직접 추가");
    if (!r) return;
    setPaste("");
    setPasteOpen(false);
    toast(`${r.added}개 추가 · 중복 ${r.skipped}개 건너뜀`);
  };

  // CSV 형식: 1열 단어, (사용자 사전) 2열 품사 [확인 필요]
  const importCsv = async (file: File) => {
    const rows = (await file.text())
      .split(/\r?\n/)
      .map((l) => l.split(",").map((c) => c.replace(/^﻿?"|"$/g, "").trim()))
      .filter((c) => c[0]);
    if (rows.length && /^(단어|복합어|word)$/i.test(rows[0][0])) rows.shift();
    if (!rows.length) return toast("가져올 단어가 없습니다. 파일 형식을 확인하세요 [문구 확인 필요]");
    const r = await add(rows.map((c) => ({ word: c[0], pos: /^NN[PG]$/.test(c[1] ?? "") ? c[1] : undefined })), "CSV 가져오기");
    if (r) toast(`${r.added}개 가져옴 · 중복 ${r.skipped}개 건너뜀`);
  };

  const exportCsv = async () => {
    try {
      downloadBlob(await api.exportDictionary(kind, filters), isComp ? "user-dictionary.csv" : "stopwords.csv");
    } catch {
      toast("CSV를 내보내지 못했습니다 [문구 확인 필요]");
    }
  };

  return (
    <section data-func-id="FN-DIC-002" className="flex flex-col gap-3.5 rounded-card border border-line bg-surface p-6">
      <h2 className="m-0 text-base font-bold">단어 추가</h2>
      <div data-ui-id={uiIds.add} className="flex flex-wrap items-start gap-4">
        <Field
          label={isComp ? "복합어" : "단어"}
          hint={isComp ? "예: 승단심사, 겨루기대회" : "예: 기자, 사진, 제공"}
          error={wordErr}
          className="min-w-[220px] flex-[2.4]"
        >
          <Input
            value={word}
            aria-invalid={!!wordErr}
            onChange={(e) => {
              setWord(e.target.value);
              setWordErr("");
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.nativeEvent.isComposing) {
                e.preventDefault();
                addOne();
              }
            }}
          />
        </Field>
        {isComp && (
          // 품사 선택지 [확인 필요]
          <Field label="품사" className="min-w-40 flex-1">
            <Select value={pos} onChange={(e) => setPos(e.target.value)}>
              <option value="NNP">고유명사 (NNP)</option>
              <option value="NNG">일반명사 (NNG)</option>
            </Select>
          </Field>
        )}
        <Field label="적용 대상" className="min-w-[200px] flex-[1.2]">
          <Select value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="default">내 기본값 (모든 소스)</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <Button variant="primary" className="mt-[25px] px-[18px]" onClick={addOne} disabled={busy}>
          추가
        </Button>
      </div>

      <div data-ui-id={uiIds.bulk} data-func-id="FN-DIC-003" className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-[13px] text-ink-2">
          여러 개를 한 번에: 줄바꿈이나 쉼표로 붙여넣거나 CSV 파일을 가져옵니다. 추가하면 표 맨 위에 바로 나타납니다
        </span>
        <div className="flex flex-wrap gap-2">
          <Button className="h-[38px]" aria-expanded={pasteOpen} onClick={() => setPasteOpen((v) => !v)}>
            여러 개 붙여넣기
          </Button>
          <Button className="h-[38px]" onClick={() => fileRef.current?.click()} disabled={busy}>
            CSV 가져오기
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) importCsv(file);
            }}
          />
          <Button className="h-[38px]" onClick={exportCsv}>
            CSV 내보내기
          </Button>
        </div>
      </div>

      {pasteOpen && (
        <div className="flex flex-col gap-2 rounded-[10px] bg-hover p-3.5">
          <Textarea rows={4} value={paste} onChange={(e) => setPaste(e.target.value)} aria-label="여러 개 붙여넣기" placeholder="줄바꿈 또는 쉼표로 구분" />
          <div className="flex justify-end gap-2">
            <Button size="sm" onClick={() => { setPaste(""); setPasteOpen(false); }}>
              취소
            </Button>
            <Button size="sm" variant="primary" onClick={addPasted} disabled={busy || !paste.trim()}>
              추가
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
