"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { Field, Input } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import type { Source, SourceType } from "@/lib/types";
import { INITIAL_MANUAL, manualComplete, type ManualState } from "./board-manual";
import { BoardDetectSection, BoardScopeSection, INITIAL_AUTO, type AutoState } from "./board-sections";
import { FormSection } from "./form-section";
import { NewsSections } from "./news-sections";
import { ScheduleSection } from "./schedule-section";
import { UrlSections } from "./url-sections";
import {
  basicSummary,
  initialValues,
  toInput,
  validate,
  type BoardMode,
  type FormErrors,
  type FormProps,
  type FormValues,
} from "./values";

// SOURCE-002 뉴스 키워드 · SOURCE-003 게시판 자동 탐지 · SOURCE-004 게시판 수동 설정 · SOURCE-005 URL
// 유형 카드·탐지 탭은 URL 만 바꾸고 이 컴포넌트는 그대로 남아, 입력한 공통 필드가 유지된다 [확인 필요]

const TYPES: { type: SourceType; label: string; desc: string; placeholder: string; uiId: string }[] = [
  { type: "news", label: "뉴스 키워드", desc: "키워드로 네이버 뉴스를 검색해 모읍니다", placeholder: "[예: 태권도 뉴스]", uiId: "SOURCE-002" },
  { type: "board", label: "게시판", desc: "게시판 목록에서 새 글을 계속 모읍니다", placeholder: "[예: 협회 공지사항]", uiId: "SOURCE-003" },
  { type: "url", label: "URL", desc: "주소를 넣은 글의 본문만 한 번 가져옵니다", placeholder: "[예: 참고 기사 모음]", uiId: "SOURCE-005" },
];

// [확인 필요] 편집 모드 제목 — 와이어프레임에 없어 추가 화면과 동일하게 표시
const META = {
  "SOURCE-002": { title: "소스 추가 · 뉴스 키워드", desc: "검색할 키워드와 검색 옵션을 정합니다", footer: "SOURCE-002-U16" },
  "SOURCE-003": { title: "소스 추가 · 게시판", desc: "게시판 URL을 넣고 탐지 결과를 확인한 뒤 저장합니다", footer: "SOURCE-003-U22" },
  "SOURCE-004": { title: "소스 추가 · 게시판", desc: "사이트 화면에서 목록과 글 링크를 직접 클릭해 지정합니다", footer: "SOURCE-004-U12" },
  "SOURCE-005": { title: "소스 추가 · URL", desc: "글 주소를 넣으면 그 글들의 본문을 한 번 가져옵니다", footer: "SOURCE-005-U11" },
} as const;

export function SourceForm({ type, mode, source }: { type: SourceType; mode: BoardMode; source: Source | null }) {
  const router = useRouter();
  const toast = useToast();
  const confirm = useConfirm();

  const [v, setV] = useState<FormValues>(() => initialValues(source));
  const [err, setErrState] = useState<FormErrors>({});
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState({ basic: false, scope: false, sched: false });
  const [auto, setAuto] = useState<AutoState>(INITIAL_AUTO);
  const [manual, setManual] = useState<ManualState>(INITIAL_MANUAL);

  const form: FormProps = {
    v,
    set: (patch) => {
      setV((prev) => ({ ...prev, ...patch }));
      setDirty(true);
    },
    err,
    setErr: (patch) => setErrState((prev) => ({ ...prev, ...patch })),
  };

  const isBoard = type === "board";
  const isManual = isBoard && mode === "manual";
  const screenId = type === "news" ? "SOURCE-002" : type === "url" ? "SOURCE-005" : isManual ? "SOURCE-004" : "SOURCE-003";
  const meta = META[screenId];
  const typeMeta = TYPES.find((t) => t.type === type)!;
  const editId = source?.id ?? null;

  const hrefFor = (t: SourceType, m: BoardMode = "auto") => {
    const modeQs = t === "board" && m === "manual" ? "mode=manual" : "";
    if (editId) return `/sources/${editId}/edit${modeQs ? `?${modeQs}` : ""}`;
    return `/sources/new?type=${t}${modeQs ? `&${modeQs}` : ""}`;
  };
  const toggle = (k: keyof typeof open) => setOpen((o) => ({ ...o, [k]: !o[k] }));

  // FUNC: FN-SRC-010 저장 / 저장 후 바로 수집
  const save = async (run: boolean) => {
    const e = validate(v, type);
    setErrState(e);
    if (Object.values(e).some(Boolean)) {
      toast("입력값을 확인하세요 [문구 확인 필요]");
      return;
    }
    setSaving(true);
    try {
      const selectors = isManual ? manual.sel : (source?.selectors ?? null);
      const saved = await api.saveSource(toInput(v, type, editId, selectors));
      setDirty(false);
      if (run) {
        await api.runCollect([saved.id]);
        router.push("/jobs"); // 이동 화면 [확인 필요]
      } else {
        toast("소스를 저장했습니다");
        router.push("/sources"); // [추정]
      }
    } catch {
      toast("저장하지 못했습니다 [문구 확인 필요]");
      setSaving(false);
    }
  };

  // 취소 — 입력 폐기 확인 [추정]
  const cancel = () => {
    if (!dirty) return router.push("/sources");
    confirm({
      title: "입력한 내용을 저장하지 않고 나갈까요?",
      body: "[문구 확인 필요] 이탈 시 입력값 보존 정책은 정해지지 않았습니다.",
      okLabel: "나가기",
      onOk: () => router.push("/sources"),
    });
  };

  const saveBlocked = saving || (isManual && !manualComplete(manual)); // 필수 단계 미완료 시 비활성 [추정]

  return (
    <div data-screen-label="SOURCE-002~005 소스 추가" data-screen-id={screenId} className="flex flex-col gap-5">
      <PageHeader title={meta.title} description={meta.desc} />

      {/* 1 기본 정보 */}
      <FormSection
        n={1}
        title="기본 정보"
        className="gap-[18px]"
        collapsible={isManual}
        open={open.basic}
        onToggle={() => toggle("basic")}
        summary={basicSummary(v)}
        summaryUiId="SOURCE-004-U01"
      >
        <div data-ui-id={`${typeMeta.uiId}-U01`} role="radiogroup" aria-label="소스 유형" className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3">
          {TYPES.map((t) => {
            const on = t.type === type;
            return (
              <button
                key={t.type}
                type="button"
                role="radio"
                aria-checked={on}
                // 편집 모드 유형 변경 불가 [추정]
                disabled={!!editId && !on}
                onClick={() => !on && router.push(hrefFor(t.type), { scroll: false })}
                className={cx(
                  "flex flex-col items-start gap-2 rounded-[10px] p-4 text-left",
                  on ? "border-2 border-primary bg-nav-active" : "m-px border border-line bg-surface hover:bg-hover",
                )}
              >
                <span className={cx("text-[15px] font-bold", on ? "text-primary" : "text-ink")}>{t.label}</span>
                <span className="text-[13px] font-normal whitespace-normal text-muted">{t.desc}</span>
              </button>
            );
          })}
        </div>
        <Field label="소스 이름" error={err.name}>
          <Input
            data-ui-id={`${typeMeta.uiId}-U02`}
            value={v.name}
            onChange={(e) => form.set({ name: e.target.value })}
            placeholder={typeMeta.placeholder}
            aria-invalid={!!err.name}
          />
        </Field>
        {isBoard && (
          <Field label="게시판 목록 URL" hint="게시글 목록이 보이는 페이지 주소" error={err.boardUrl}>
            <Input
              data-ui-id="SOURCE-003-U03"
              type="url"
              className="font-mono"
              value={v.boardUrl}
              onChange={(e) => form.set({ boardUrl: e.target.value })}
              placeholder="https://[사이트]/bbs/board.php?bo_table=notice"
              aria-invalid={!!err.boardUrl}
            />
          </Field>
        )}
      </FormSection>

      {type === "news" && <NewsSections {...form} />}

      {isBoard && (
        <>
          <BoardDetectSection
            form={form}
            mode={mode}
            modeHref={(m) => hrefFor("board", m)}
            auto={auto}
            setAuto={setAuto}
            manual={manual}
            setManual={setManual}
          />
          <BoardScopeSection form={form} collapsible={isManual} open={open.scope} onToggle={() => toggle("scope")} />
        </>
      )}

      {type === "url" && <UrlSections {...form} />}

      {type !== "url" && (
        <ScheduleSection form={form} news={type === "news"} collapsible={isManual} open={open.sched} onToggle={() => toggle("sched")} />
      )}

      <div data-ui-id={meta.footer} data-func-id="FN-SRC-010" className="flex flex-wrap justify-end gap-2">
        <Button onClick={cancel} disabled={saving}>
          취소
        </Button>
        <Button onClick={() => save(true)} disabled={saveBlocked}>
          저장 후 바로 수집
        </Button>
        <Button variant="primary" className="px-[18px]" onClick={() => save(false)} disabled={saveBlocked}>
          {saving ? "저장 중…" : "저장"}
        </Button>
      </div>
    </div>
  );
}
