"use client";

import { useState } from "react";
import { useSession } from "@/components/layout/session";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { FieldError, Input } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { StatCard, StatGrid } from "@/components/ui/stat-card";
import { DeniedState, ErrorState, PageSkeleton } from "@/components/ui/states";
import { Table, Td, Th } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import { useApiData } from "@/lib/use-api-data";
import type { AdminDefault, AdminPageData, DictEntry } from "@/lib/types";

// ADMIN-001 관리자

export function AdminScreen() {
  const { role } = useSession();
  // [확인 필요] 멤버에게 메뉴를 숨길지 안내할지 — 와이어프레임대로 메뉴는 보이고 들어오면 안내
  if (role !== "admin") {
    return <DeniedState title="관리자만 볼 수 있는 화면입니다" description="[확인 필요] 멤버 접근 시 메뉴 숨김 또는 안내 중 정책 미정" />;
  }
  return <AdminContent />;
}

function AdminContent() {
  const { data, error, loading, reload } = useApiData(api.getAdminPage);

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState onRetry={() => reload("full")} />;

  const pct = (a: number, b: number) => (b ? Math.round((a / b) * 100) : 0);

  return (
    <div data-screen-label="ADMIN-001 관리자" data-screen-id="ADMIN-001" className="flex flex-col gap-6">
      <PageHeader title="관리자" description="서비스 전체 사용량과 시스템 기본값을 관리합니다" />

      <StatGrid label="요약" data-ui-id="ADMIN-001-U01" data-func-id="FN-ADM-001">
        <StatCard label="가입 유저" value={data.users} sub={`이번 달 신규 ${data.newThisMonth}`} />
        {/* 활성 유저 정의 [정책 필요] */}
        <StatCard label="활성 유저 (7일)" value={data.active7} sub={`전체의 ${pct(data.active7, data.users)}%`} />
        <StatCard
          label="네이버 API 오늘 호출"
          value={data.apiToday.toLocaleString()}
          sub={`일일 한도 ${data.apiLimit.toLocaleString()} 대비 ${pct(data.apiToday, data.apiLimit)}%`}
        />
        <StatCard label="작업 큐 대기" value={`${data.queueWait}건`} sub={`평균 대기 ${data.avgWait}초`} />
      </StatGrid>

      {/* 행마다 카드 너비 비율이 다르다 (와이어프레임). 좁으면 한 줄씩 */}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.75fr)_minmax(0,1fr)]">
        <UsageCard usage={data.usage} />
        <QueueCard queue={data.queue} />
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <CoreCard core={data.core} />
        <KeywordCard keywords={data.keywords} />
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.75fr)_minmax(0,1fr)]">
        <DefaultsCard defaults={data.defaults} onSaved={() => reload("quiet")} />
        <CommonStopwordsCard words={data.commonStopwords} onChanged={() => reload("quiet")} />
      </div>
    </div>
  );
}

function UsageCard({ usage }: { usage: AdminPageData["usage"] }) {
  return (
    // 워크스페이스·요금제 개념 [정책 필요] / 관리자의 개별 유저 데이터 열람 범위 [정책 필요]
    <Card data-ui-id="ADMIN-001-U02" data-func-id="FN-ADM-002" className="flex flex-col gap-2.5">
      <CardTitle>전체 사용 현황</CardTitle>
      <div className="overflow-x-auto">
        <Table className="min-w-[560px]">
          <thead>
            <tr>
              <Th>유저</Th>
              <Th>요금제</Th>
              <Th>소스</Th>
              <Th>키워드</Th>
              <Th>30일 수집</Th>
              <Th>최근 접속</Th>
            </tr>
          </thead>
          <tbody>
            {usage.map((u) => (
              <tr key={u.user}>
                <Td>{u.user}</Td>
                <Td>
                  <Badge>{u.plan}</Badge>
                </Td>
                <Td className="font-mono text-[13px]">{u.src}</Td>
                <Td className="font-mono text-[13px]">{u.kw}</Td>
                <Td className="font-mono text-[13px]">{u.n30.toLocaleString()}건</Td>
                <Td className="font-mono text-[13px]">{u.last}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
      {usage.length === 0 && <p className="m-0 py-4 text-center text-[13px] text-muted">유저가 없습니다 [문구 확인 필요]</p>}
    </Card>
  );
}

function QueueCard({ queue: q }: { queue: AdminPageData["queue"] }) {
  const rows: [string, string][] = [
    ["대기", `${q.waiting}건`],
    ["실행 중", `${q.running}건`],
    ["평균 대기 시간", `${q.avgWait}초`],
    ["워커 수", String(q.workers)],
    ["최근 1시간 실패", `${q.fail1h}건`],
  ];
  return (
    <Card data-ui-id="ADMIN-001-U03" data-func-id="FN-ADM-003" className="flex flex-col">
      <CardTitle className="mb-2">작업 큐</CardTitle>
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between border-b border-line-soft py-[15px]">
          <span>{k}</span>
          <span className="font-mono text-[13px]">{v}</span>
        </div>
      ))}
    </Card>
  );
}

function CoreCard({ core }: { core: AdminPageData["core"] }) {
  return (
    <Card data-ui-id="ADMIN-001-U04" data-func-id="FN-ADM-004" className="flex flex-col gap-2.5">
      <CardTitle>전체 핵심어 집계</CardTitle>
      <p className="m-0 text-[13px] text-muted">모든 유저 수집분 합산 · 유저를 식별하지 않음</p>
      <Table>
        <thead>
          <tr>
            <Th className="w-9">#</Th>
            <Th>단어</Th>
            <Th>등장 글</Th>
            <Th>평균 밀도</Th>
          </tr>
        </thead>
        <tbody>
          {core.map((c, i) => (
            <tr key={c.w}>
              <Td className="py-3 text-[13px]">{i + 1}</Td>
              <Td className="py-3">{c.w}</Td>
              <Td className="py-3 font-mono text-[13px]">{c.docs}</Td>
              <Td className="py-3 font-mono text-[13px]">{c.d.toFixed(1)}%</Td>
            </tr>
          ))}
        </tbody>
      </Table>
      {core.length === 0 && <p className="m-0 py-4 text-center text-[13px] text-muted">집계할 데이터가 없습니다 [문구 확인 필요]</p>}
    </Card>
  );
}

function KeywordCard({ keywords }: { keywords: AdminPageData["keywords"] }) {
  return (
    <Card data-ui-id="ADMIN-001-U05" data-func-id="FN-ADM-005" className="flex flex-col gap-2.5">
      <CardTitle>등록 키워드 현황</CardTitle>
      {/* 공유 호출 정책 [정책 필요] */}
      <p className="m-0 text-[13px] text-muted">등록한 유저 수만 표시 · 2명 이상이면 네이버 API를 한 번만 호출해 공유</p>
      <Table>
        <thead>
          <tr>
            <Th>키워드</Th>
            <Th>등록</Th>
            <Th>호출 방식</Th>
          </tr>
        </thead>
        <tbody>
          {keywords.map((k) => (
            <tr key={k.kw}>
              <Td className="py-3">{k.kw}</Td>
              <Td className="py-3 font-mono text-[13px]">{k.n}명</Td>
              <Td className="py-3">
                {k.n >= 2 ? (
                  <Badge tone="blue" strong>
                    API 공유 호출
                  </Badge>
                ) : (
                  <span className="text-muted">—</span>
                )}
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
      {keywords.length === 0 && <p className="m-0 py-4 text-center text-[13px] text-muted">등록된 키워드가 없습니다 [문구 확인 필요]</p>}
    </Card>
  );
}

type DraftRow = AdminDefault & { draft: Record<"def" | "min" | "max", string> };

const FIELDS = [
  ["def", "기본값"],
  ["min", "최소"],
  ["max", "최대"],
] as const;

const fmt = (r: AdminDefault, v: number) => (r.dec ? v.toFixed(r.dec) : v.toLocaleString()) + (r.unit || "");

// FUNC: FN-ADM-006 — 편집 UI 미정 [확인 필요] → 표 안 입력으로 구현. 신규·미설정 유저 적용 범위 [확인 필요]
function DefaultsCard({ defaults, onSaved }: { defaults: AdminDefault[]; onSaved: () => void }) {
  const toast = useToast();
  const [draft, setDraft] = useState<DraftRow[] | null>(null);
  const [saving, setSaving] = useState(false);
  const editing = draft != null;

  const errs: Record<string, string> = {};
  for (const r of draft ?? []) {
    const [d, mn, mx] = FIELDS.map(([f]) => r.draft[f]);
    if ([d, mn, mx].some((v) => v.trim() === "" || Number.isNaN(Number(v)))) errs[r.key] = "숫자를 입력하세요";
    else if (!(Number(mn) <= Number(d) && Number(d) <= Number(mx))) errs[r.key] = "최소 ≤ 기본값 ≤ 최대 [추정]";
  }
  const hasErr = Object.keys(errs).length > 0;

  const startEdit = () =>
    setDraft(defaults.map((r) => ({ ...r, draft: { def: String(r.def), min: String(r.min), max: String(r.max) } })));

  const setCell = (key: string, field: "def" | "min" | "max", v: string) =>
    setDraft((rows) => rows?.map((r) => (r.key === key ? { ...r, draft: { ...r.draft, [field]: v } } : r)) ?? null);

  const save = async () => {
    if (!draft) return;
    setSaving(true);
    try {
      await api.saveAdminDefaults(
        draft.map(({ draft: d, ...r }) => ({ ...r, def: Number(d.def), min: Number(d.min), max: Number(d.max) })),
      );
      setDraft(null);
      onSaved();
      toast("시스템 기본값을 저장했습니다");
    } catch {
      toast("저장하지 못했습니다 [문구 확인 필요]");
    } finally {
      setSaving(false);
    }
  };

  const rows: (AdminDefault | DraftRow)[] = draft ?? defaults;

  return (
    <Card data-ui-id="ADMIN-001-U06" data-func-id="FN-ADM-006" className="flex flex-col gap-2.5">
      <div className="flex items-center justify-between gap-3">
        <CardTitle>시스템 기본값 · 허용 범위</CardTitle>
        {editing ? (
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setDraft(null)} disabled={saving}>
              취소
            </Button>
            <Button size="sm" variant="primary" onClick={save} disabled={hasErr || saving}>
              {saving ? "저장 중…" : "저장"}
            </Button>
          </div>
        ) : (
          <Button size="sm" onClick={startEdit}>
            편집
          </Button>
        )}
      </div>
      <p className="m-0 text-[13px] text-muted">유저는 허용 범위 안에서만 값을 바꿀 수 있습니다</p>
      <Table>
        <thead>
          <tr>
            <Th>항목</Th>
            {FIELDS.map(([, label]) => (
              <Th key={label}>{label}</Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <Td className="py-3">
                {r.label}
                {errs[r.key] && <span className="block text-xs text-warn">{errs[r.key]}</span>}
              </Td>
              {FIELDS.map(([f, label]) => (
                <Td key={f} className="py-3 pr-2 font-mono text-[13px]">
                  {"draft" in r ? (
                    <input
                      inputMode="decimal"
                      aria-label={`${r.label} ${label}`}
                      aria-invalid={!!errs[r.key]}
                      value={r.draft[f]}
                      onChange={(e) => setCell(r.key, f, e.target.value)}
                      className={cx(
                        "h-8 w-20 rounded-md border bg-surface px-2 font-mono text-[13px] outline-none focus:border-primary",
                        errs[r.key] ? "border-warn" : "border-field",
                      )}
                    />
                  ) : (
                    fmt(r, r[f])
                  )}
                </Td>
              ))}
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

// FUNC: FN-ADM-007 — 사전(SETTING-002)의 '시스템 공통' 출처와 같은 목록 [추정]
function CommonStopwordsCard({ words, onChanged }: { words: DictEntry[]; onChanged: () => void }) {
  const toast = useToast();
  const [word, setWord] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const add = async () => {
    const w = word.trim();
    if (!w) return setErr("단어를 입력하세요 [문구 확인 필요]");
    setBusy(true);
    try {
      if (!(await api.addCommonStopword(w))) return setErr("이미 등록된 단어입니다 [추정]");
      setWord("");
      setErr("");
      onChanged();
      toast(`공통 불용어 '${w}'을(를) 추가했습니다`);
    } catch {
      toast("추가하지 못했습니다 [문구 확인 필요]");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (x: DictEntry) => {
    try {
      await api.removeCommonStopword(x.id);
      onChanged();
      toast(`공통 불용어 '${x.word}'을(를) 삭제했습니다`);
    } catch {
      toast("삭제하지 못했습니다 [문구 확인 필요]");
    }
  };

  return (
    <Card data-ui-id="ADMIN-001-U07" data-func-id="FN-ADM-007" className="flex flex-col gap-3.5">
      <CardTitle>공통 불용어</CardTitle>
      <p className="m-0 text-[13px] text-muted">모든 유저에게 기본 적용</p>
      <div className="flex flex-wrap gap-2">
        {words.map((x) => (
          <span key={x.id} className="inline-flex h-[30px] items-center gap-1.5 rounded-full bg-subtle pr-1.5 pl-3 text-[13px]">
            {x.word}
            <button
              type="button"
              aria-label={`${x.word} 삭제`}
              onClick={() => remove(x)}
              className="size-[22px] rounded-full border-none bg-transparent text-sm leading-none text-ink-2 hover:bg-line"
            >
              ×
            </button>
          </span>
        ))}
        {words.length === 0 && <span className="text-[13px] text-muted">등록된 공통 불용어가 없습니다 [문구 확인 필요]</span>}
      </div>
      <div className="flex gap-2">
        <Input
          aria-label="공통 불용어 입력"
          placeholder="단어 입력"
          value={word}
          aria-invalid={!!err}
          onChange={(e) => {
            setWord(e.target.value);
            setErr("");
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.nativeEvent.isComposing) {
              e.preventDefault();
              add();
            }
          }}
          className="min-w-0 flex-1"
        />
        <Button className="h-10" onClick={add} disabled={busy}>
          추가
        </Button>
      </div>
      <FieldError>{err}</FieldError>
    </Card>
  );
}
