"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { Field, FieldError, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { SegmentedTabs } from "@/components/ui/segmented-tabs";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import { useApiData } from "@/lib/use-api-data";
import type { AnalysisSettings, Source, SettingsBundle } from "@/lib/types";
import { DensityPreview } from "./density-preview";

// SETTING-001 분석 설정

const NUM_KEYS = [
  "topN", "ttrWarn", "minBody", "densityWarn", "warnMinCount", "warnMinNouns",
  "minMentions", "densTitle", "densNoTitle", "densMinLen",
] as const;
type NumKey = (typeof NUM_KEYS)[number];

/** 입력 중인 값 — 숫자 칸은 문자열로 들고 저장할 때 바꾼다 */
type Draft = Omit<AnalysisSettings, NumKey> & Record<NumKey, string>;

const toDraft = (s: AnalysisSettings): Draft => {
  const d = structuredClone(s) as unknown as Draft;
  for (const k of NUM_KEYS) d[k] = s[k] == null ? "" : String(s[k]);
  return d;
};

const toSettings = (d: Draft): AnalysisSettings => {
  const s = { ...d } as unknown as AnalysisSettings;
  for (const k of NUM_KEYS) (s as unknown as Record<string, number | null>)[k] = d[k] === "" ? null : Number(d[k]);
  return s;
};

const PRESETS = [
  ["strict", "엄격"],
  ["normal", "보통"],
  ["loose", "느슨"],
  ["custom", "사용자 지정"],
] as const;

const METRICS: [keyof AnalysisSettings["metrics"], string][] = [
  ["tokens", "전체 토큰 수"],
  ["unique", "고유 토큰 수"],
  ["nouns", "명사 수"],
  ["sentences", "문장 수"],
  ["avgLen", "평균 문장 길이"],
  ["ttr", "어휘 다양도"],
];

export function SettingsScreen() {
  const [scope, setScope] = useState("default");
  const { data, error, loading, stale, reload } = useApiData(() => api.getSettings(scope), scope);
  const { data: sources } = useApiData(() => api.listSources());

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState onRetry={() => reload("full")} />;

  // 범위를 바꾸면 불러온 값으로 편집을 새로 시작한다
  return (
    <SettingsEditor
      key={data.scope}
      bundle={data}
      sources={sources ?? []}
      loadingScope={stale}
      onScopeChange={setScope}
    />
  );
}

function SettingsEditor({
  bundle,
  sources,
  loadingScope,
  onScopeChange,
}: {
  bundle: SettingsBundle;
  sources: Source[];
  loadingScope: boolean;
  onScopeChange: (scope: string) => void;
}) {
  const toast = useToast();
  const confirm = useConfirm();
  const [saved, setSaved] = useState<Draft>(() => toDraft(bundle.settings));
  const [d, setDraft] = useState<Draft>(saved);
  const [saving, setSaving] = useState(false);

  // 값을 하나라도 바꾸면 '사용자 지정'
  const set = (patch: Partial<Draft>, keepPreset = false) =>
    setDraft((prev) => ({ ...prev, ...patch, ...(keepPreset ? {} : { preset: "custom" as const }) }));

  // Validation — ADMIN-001-U06 허용 범위 (문서 기준). 범위 없는 항목은 숫자 여부만 [확인 필요]
  const ranges = Object.fromEntries(bundle.ranges.map((r) => [r.key, r]));
  const errs: Partial<Record<NumKey, string>> = {};
  for (const k of NUM_KEYS) {
    if (d[k] === "") {
      if (k !== "minBody") errs[k] = "값을 입력하세요";
      continue;
    }
    const v = Number(d[k]);
    if (Number.isNaN(v)) errs[k] = "숫자를 입력하세요";
    else if (ranges[k] && (v < ranges[k].min || v > ranges[k].max)) errs[k] = `허용 범위 ${ranges[k].min}~${ranges[k].max}${ranges[k].unit}`; // [문구 확인 필요]
  }
  const hasErr = Object.keys(errs).length > 0;
  const clean = JSON.stringify(d) === JSON.stringify(saved);

  const scopeSource = sources.find((s) => s.id === bundle.scope);
  const relDisabled = !!scopeSource && scopeSource.type !== "news"; // 게시판·URL 소스 선택 시 비활성 [추정]

  // FUNC: FN-SET-001 적용 범위
  const changeScope = (next: string) => {
    if (clean) return onScopeChange(next);
    confirm({
      title: "저장하지 않은 변경이 있습니다",
      body: "적용 범위를 바꾸면 변경 내용이 사라집니다. [문구 확인 필요]",
      okLabel: "범위 변경",
      onOk: () => onScopeChange(next),
    });
  };

  // FUNC: FN-SET-002 프리셋
  const pickPreset = (id: Draft["preset"]) => {
    if (id === "normal") {
      // [추정] '보통' = 시스템 기본값
      const patch: Partial<Draft> = { preset: "normal" };
      for (const r of bundle.ranges) (patch as Record<string, string>)[r.key] = String(r.def);
      set(patch, true);
    } else if (id === "custom") {
      set({ preset: "custom" }, true);
    } else {
      set({ preset: id }, true);
      toast(`[정책 필요] '${id === "strict" ? "엄격" : "느슨"}' 프리셋 값이 정해지지 않아 수치는 바뀌지 않습니다`);
    }
  };

  // FUNC: FN-SET-007 저장
  const save = async () => {
    setSaving(true);
    try {
      const next = toDraft(await api.saveSettings(bundle.scope, toSettings(d)));
      setSaved(next);
      setDraft(next);
      toast("분석 설정을 저장했습니다. 판정을 새 기준으로 다시 계산합니다");
    } catch {
      toast("저장하지 못했습니다 [문구 확인 필요]");
    } finally {
      setSaving(false);
    }
  };

  const num = (key: NumKey, label: string, desc: string, unit: string, placeholder?: string, disabled?: boolean) => (
    <Row label={label} desc={desc} htmlFor={`set-${key}`}>
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <NumInput id={`set-${key}`} value={d[key]} invalid={!!errs[key]} placeholder={placeholder} disabled={disabled} onChange={(v) => set({ [key]: v })} />
          <span className="text-[13px] text-ink-2">{unit}</span>
        </div>
        <FieldError>{errs[key]}</FieldError>
      </div>
    </Row>
  );

  return (
    <div data-screen-label="SETTING-001 분석 설정" data-screen-id="SETTING-001" className="flex flex-col gap-6">
      <PageHeader
        title="분석 설정"
        description="형태소 지표와 키워드 관련도 기준을 조정합니다. 수치는 저장해 두고 판정만 새 기준으로 다시 계산합니다"
      />

      <section className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] items-start gap-x-8 gap-y-6 rounded-card border border-line bg-surface p-6">
        <Field
          label="적용 범위"
          hint="특정 소스(예: '태권도 뉴스')를 고르면 그 소스에만 적용되는 값을 편집합니다"
          className="[&>span]:leading-normal"
        >
          <Select data-ui-id="SETTING-001-U01" data-func-id="FN-SET-001" value={bundle.scope} onChange={(e) => changeScope(e.target.value)} disabled={loadingScope}>
            <option value="default">내 기본값 (모든 소스)</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <div data-func-id="FN-SET-002" className="flex min-w-0 flex-col gap-2">
          <span id="preset-label" className="text-[13px] font-semibold">
            프리셋
          </span>
          <SegmentedTabs data-ui-id="SETTING-001-U02" mode="radio" size="md" labelledBy="preset-label" items={PRESETS} value={d.preset} onChange={pickPreset} />
          <span className="text-xs text-muted">값을 하나라도 바꾸면 &apos;사용자 지정&apos;이 됩니다</span>
        </div>
        <div data-ui-id="SETTING-001-U03" className="flex flex-col gap-2">
          <span className="text-[13px] font-semibold">적용 순서</span>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge>시스템 기본값</Badge>→<Badge tone={bundle.scope === "default" ? "blue" : "gray"}>내 기본값</Badge>→
            <Badge tone={bundle.scope === "default" ? "gray" : "blue"}>소스별</Badge>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[1.8_1_560px] flex-col gap-6">
          <SettingsCard uiId="SETTING-001-U04" funcId="FN-SET-003" title="글 단위 지표" desc="콘텐츠 상세 화면에 표시할 지표와 경고 기준">
            <Row label="표시할 지표" desc="상세 화면에 보일 지표를 고릅니다">
              <div role="group" aria-label="표시할 지표" className="grid grid-cols-[auto_auto] justify-start gap-x-[18px] gap-y-1.5">
                {METRICS.map(([k, label]) => (
                  <label key={k} className="flex cursor-pointer items-center gap-2 text-sm whitespace-nowrap">
                    <input
                      type="checkbox"
                      checked={d.metrics[k]}
                      onChange={(e) => set({ metrics: { ...d.metrics, [k]: e.target.checked } })}
                      className="m-0 size-[18px] accent-primary"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </Row>
            {num("topN", "상위 키워드 개수", "글마다 보여줄 키워드 수", "개")}
            {num("ttrWarn", "어휘 다양도 경고 기준", "이 값 미만이면 경고 표시 (같은 표현 반복·목록 페이지 오추출 의심)", "")}
            {/* 기본값 [확인 필요] */}
            {num("minBody", "분석 최소 본문 길이", "이보다 짧은 글은 지표를 표시하지 않음", "자", "[N]")}
          </SettingsCard>

          <SettingsCard uiId="SETTING-001-U05" funcId="FN-SET-004" title="단어별 밀도" desc="한 단어가 글에서 차지하는 비율의 계산 방식과 과다 반복 경고">
            <Row label="분모 기준" desc="밀도 = 단어 출현 횟수 ÷ 분모">
              <SegmentedTabs
                mode="radio"
                size="md"
                label="분모 기준"
                items={[["noun", "명사"], ["content", "내용어 전체"]] as const}
                value={d.denom as "noun" | "content"}
                onChange={(denom) => set({ denom })}
              />
            </Row>
            <Row label="품사 범위" desc="집계에 포함할 품사">
              <SegmentedTabs
                mode="radio"
                size="md"
                label="품사 범위"
                items={[["noun", "명사만"], ["vva", "+동사·형용사"], ["foreign", "+외국어"]] as const}
                value={d.posRange as "noun" | "vva" | "foreign"}
                onChange={(posRange) => set({ posRange })}
              />
            </Row>
            {num("densityWarn", "밀도 경고 기준", "한 단어가 이 비율을 넘으면 과다 반복 표시", "%")}
            {/* 범위 [확인 필요] */}
            <Row label="경고 최소 조건" desc="표본이 작으면 경고하지 않음">
              <div className="flex flex-col gap-2">
                <InlineNum label="회 이상 출현" aria="최소 출현 횟수" value={d.warnMinCount} invalid={!!errs.warnMinCount} onChange={(v) => set({ warnMinCount: v })} after />
                <InlineNum label="개 이상 명사" aria="최소 명사 수" value={d.warnMinNouns} invalid={!!errs.warnMinNouns} onChange={(v) => set({ warnMinNouns: v })} after />
                <FieldError>{errs.warnMinCount || errs.warnMinNouns}</FieldError>
              </div>
            </Row>
            <Row label="불용어 · 사용자 사전" desc="단어 목록은 '사전' 메뉴에서 관리합니다">
              <div className="flex flex-col gap-1 text-[13px] text-ink-2">
                <span>
                  불용어 {bundle.dictCounts.stopwords}개 · 사용자 사전 {bundle.dictCounts.compounds}개
                </span>
                <Link href="/dictionary" className="text-sm font-bold">
                  사전 관리 →
                </Link>
              </div>
            </Row>
          </SettingsCard>

          <SettingsCard
            uiId="SETTING-001-U06"
            funcId="FN-SET-005"
            title="키워드 관련도"
            desc={`등록 키워드가 그 글의 주제인지 판정하는 기준${relDisabled ? " — 게시판·URL 소스에는 적용되지 않습니다 [추정]" : ""}`}
            className={cx(relDisabled && "opacity-55")}
          >
            {num("minMentions", "최소 언급 횟수", "미만이면 '스쳐 지나감'", "회", undefined, relDisabled)}
            <Row label="1,000자당 밀도 기준" desc="제목에 키워드가 없으면 더 높은 밀도를 요구">
              <div className="flex flex-col gap-2">
                <InlineNum label="제목 포함" aria="제목 포함 밀도 기준" value={d.densTitle} invalid={!!errs.densTitle} disabled={relDisabled} onChange={(v) => set({ densTitle: v })} />
                <InlineNum label="제목 미포함" aria="제목 미포함 밀도 기준" value={d.densNoTitle} invalid={!!errs.densNoTitle} disabled={relDisabled} onChange={(v) => set({ densNoTitle: v })} />
                <FieldError>{errs.densTitle || errs.densNoTitle}</FieldError>
              </div>
            </Row>
            {num("densMinLen", "밀도 검사 최소 길이", "이보다 짧은 글은 밀도 검사를 건너뜀", "자", undefined, relDisabled)}
            <Row label="제목 포함 필수" desc="켜면 제목에 키워드가 없는 글은 '주제 기사'가 될 수 없음">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={d.requireTitle}
                  disabled={relDisabled}
                  onChange={(e) => set({ requireTitle: e.target.checked })}
                  className="m-0 size-[18px] accent-primary"
                />
                사용
              </label>
            </Row>
            <Row label="'스쳐 지나감' 처리" desc="콘텐츠 목록·대시보드에서의 표시 방식">
              <SegmentedTabs
                mode="radio"
                size="md"
                label="'스쳐 지나감' 처리"
                items={[["hide", "숨김"], ["dim", "흐리게"], ["show", "표시"]] as const}
                value={d.passingMode}
                onChange={(passingMode) => set({ passingMode })}
              />
            </Row>
          </SettingsCard>
        </div>

        <aside
          data-ui-id="SETTING-001-U08"
          data-func-id="FN-SET-006"
          className="flex min-w-0 flex-[1_1_300px] flex-col gap-3.5 rounded-card border border-line bg-surface p-6 lg:sticky lg:top-6"
        >
          <h2 className="m-0 text-base font-bold">변경 미리보기</h2>
          <DensityPreview hist={bundle.densityHistogram} thSaved={Number(saved.densTitle) || 0} thNow={Number(d.densTitle) || 0} />
          <div data-ui-id="SETTING-001-U09" data-func-id="FN-SET-007" className="mt-1.5 flex justify-end gap-2">
            {/* 초기화 기준 [확인 필요] — 마지막 저장값으로 되돌림 */}
            <Button onClick={() => setDraft(saved)} disabled={clean || saving}>
              초기화
            </Button>
            <Button variant="primary" className="px-[18px]" onClick={save} disabled={clean || hasErr || saving}>
              {saving ? "저장 중…" : "저장"}
            </Button>
          </div>
          <span className="text-right text-xs text-muted">
            {bundle.scope === "default" ? "현재 설정" : `'${scopeSource?.name ?? bundle.scope}' 설정`} v{saved.version}
          </span>
        </aside>
      </div>
    </div>
  );
}

function SettingsCard({
  uiId,
  funcId,
  title,
  desc,
  className,
  children,
}: {
  uiId: string;
  funcId: string;
  title: string;
  desc: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section data-ui-id={uiId} data-func-id={funcId} className={cx("flex flex-col rounded-card border border-line bg-surface p-6", className)}>
      <h2 className="m-0 text-base font-bold">{title}</h2>
      <p className="mt-2.5 mb-2 text-[13px] text-muted">{desc}</p>
      {children}
    </section>
  );
}

/** 이름·설명 | 입력 | '즉시 반영' 세 칸. 좁은 화면에서는 한 줄씩 쌓는다 */
function Row({ label, desc, htmlFor, children }: { label: string; desc: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] items-start justify-items-start gap-2.5 border-b border-line-soft py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_auto] md:items-center md:gap-4">
      <div>
        {htmlFor ? (
          <label htmlFor={htmlFor} className="font-bold">
            {label}
          </label>
        ) : (
          <div className="font-bold">{label}</div>
        )}
        <div className="mt-1 text-[13px] leading-normal text-muted">{desc}</div>
      </div>
      <div className="max-w-full min-w-0">{children}</div>
      {/* SETTING-001-U07 — 저장하면 판정에 즉시 반영 */}
      <Badge tone="green">즉시 반영</Badge>
    </div>
  );
}

const numClass = (invalid: boolean) =>
  cx(
    "h-9 w-24 rounded-control border bg-surface px-2.5 text-right font-mono text-sm outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(42,85,153,.15)] disabled:bg-hover",
    invalid ? "border-warn" : "border-field",
  );

function NumInput({
  id,
  value,
  invalid,
  placeholder,
  disabled,
  onChange,
}: {
  id: string;
  value: string;
  invalid: boolean;
  placeholder?: string;
  disabled?: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <input
      id={id}
      inputMode="decimal"
      value={value}
      placeholder={placeholder}
      disabled={disabled}
      aria-invalid={invalid}
      onChange={(e) => onChange(e.target.value)}
      className={numClass(invalid)}
    />
  );
}

/** 라벨이 입력 앞(제목 포함 1.5) 또는 뒤(3 회 이상 출현)에 붙는 숫자 칸 */
function InlineNum({
  label,
  aria,
  value,
  invalid,
  disabled,
  after = false,
  onChange,
}: {
  label: string;
  aria: string;
  value: string;
  invalid: boolean;
  disabled?: boolean;
  after?: boolean;
  onChange: (v: string) => void;
}) {
  const input = (
    <input
      inputMode="decimal"
      aria-label={aria}
      value={value}
      disabled={disabled}
      aria-invalid={invalid}
      onChange={(e) => onChange(e.target.value)}
      className={numClass(invalid)}
    />
  );
  return (
    <label className="flex items-center gap-2 text-[13px] text-ink-2">
      {after ? (
        <>
          {input}
          {label}
        </>
      ) : (
        <>
          <span className="w-[68px]">{label}</span>
          {input}
        </>
      )}
    </label>
  );
}
