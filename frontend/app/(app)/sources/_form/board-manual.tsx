"use client";

import { Button } from "@/components/ui/button";
import { Table, Td, Th } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { cx } from "@/lib/cx";
import type { BoardSelectors } from "@/lib/types";

// SOURCE-004 수동 설정 — 사이트 화면을 보며 목록 한 줄 → 글 링크 → (제목·날짜·본문) 순서로 클릭해 지정한다.
// [확인 필요] 대상 사이트 렌더링 방식 — 지금은 MOCK 미리보기이고, 클릭 위치를 선택자로 바꾸는 계산도 흉내만 낸다.

type StepStatus = "selecting" | "done" | "optional" | "wait" | "skipped";
type StepKey = "s1" | "s2" | "s3" | "s4" | "s5";

export interface ManualState {
  steps: Record<StepKey, StepStatus>;
  selRow: number | null; // 미리보기에서 고른 줄
  mode: "title" | "date" | null; // 선택 사항 단계에서 지금 고르는 대상
  previewPage: "list" | "post";
  sel: BoardSelectors;
}

export const INITIAL_MANUAL: ManualState = {
  steps: { s1: "selecting", s2: "wait", s3: "optional", s4: "optional", s5: "wait" },
  selRow: null,
  mode: null,
  previewPage: "list",
  sel: { row: "", link: "" },
};

/** 필수 단계(목록 한 줄·글 링크)를 마쳤는지 — 마치기 전에는 저장 비활성 [추정] */
export const manualComplete = (m: ManualState) => m.steps.s1 === "done" && m.steps.s2 === "done";

const STEP_STATE: Record<StepStatus, [string, string]> = {
  selecting: ["선택 중", "text-primary"],
  done: ["선택됨", "text-success"],
  optional: ["선택 사항", "text-ink-2"],
  wait: ["대기", "text-ink-2"],
  skipped: ["건너뜀", "text-ink-2"],
};

const PREVIEW_ROWS = ["공지", "124", "123", "122", "121", "120"];

export function BoardManual({
  state: m,
  setState,
  boardUrl,
}: {
  state: ManualState;
  setState: (next: ManualState) => void;
  boardUrl: string;
}) {
  const toast = useToast();
  const st = m.steps;
  const s2done = st.s2 === "done";
  const patch = (p: Partial<ManualState>) => setState({ ...m, ...p });
  const setSteps = (p: Partial<ManualState["steps"]>, extra?: Partial<ManualState>) =>
    setState({ ...m, ...extra, steps: { ...st, ...p } });

  const instruction =
    st.s1 === "selecting"
      ? "미리보기에서 글 한 줄을 클릭하세요 [추정]"
      : st.s2 === "selecting"
        ? "미리보기에서 글 제목을 클릭하세요"
        : m.mode === "title"
          ? "미리보기에서 제목을 클릭하세요 [추정]"
          : m.mode === "date"
            ? "미리보기에서 날짜를 클릭하세요 [추정]"
            : st.s5 === "selecting"
              ? "본문이 있는 부분을 클릭하세요 [추정]"
              : "필수 단계를 마쳤습니다 [문구 확인 필요]";

  const steps: { n: number; key: StepKey; title: string; desc: string; actions: { label: string; disabled?: boolean; onClick: () => void }[] }[] = [
    {
      n: 1, key: "s1", title: "목록 한 줄",
      desc: st.s1 === "done" ? "같은 모양의 줄 5개를 찾았습니다 (점선 표시) · 공지 줄 1개 제외" : "미리보기에서 글이 있는 줄 하나를 클릭합니다 [추정]",
      // 이후 단계 초기화 [확인 필요]
      actions: st.s1 === "done" ? [{ label: "다시 선택", onClick: () => setState(INITIAL_MANUAL) }] : [],
    },
    { n: 2, key: "s2", title: "글 링크", desc: "줄 안에서 글로 들어가는 링크. 주황색 후보를 클릭하면 확정됩니다", actions: [] },
    {
      n: 3, key: "s3", title: "제목", desc: "건너뛰면 링크 글자를 제목으로 씁니다",
      actions: [
        { label: "페이지에서 선택", disabled: !s2done, onClick: () => setSteps({ s3: "selecting" }, { mode: "title", previewPage: "list" }) },
        { label: "건너뛰기", disabled: !s2done, onClick: () => setSteps({ s3: "skipped" }, { mode: null }) },
      ],
    },
    {
      n: 4, key: "s4", title: "날짜", desc: "건너뛰면 줄 전체에서 날짜 형태를 찾습니다",
      actions: [
        { label: "페이지에서 선택", disabled: !s2done, onClick: () => setSteps({ s4: "selecting" }, { mode: "date", previewPage: "list" }) },
        { label: "건너뛰기", disabled: !s2done, onClick: () => setSteps({ s4: "skipped" }, { mode: null }) },
      ],
    },
    {
      n: 5, key: "s5", title: "본문 영역", desc: "첫 번째 글을 열어 본문이 있는 부분을 클릭합니다. 건너뛰면 자동 추출",
      actions: [{ label: "첫 글 열기", disabled: !s2done, onClick: () => setSteps({ s5: "selecting" }, { previewPage: "post", mode: null }) }],
    },
  ];

  const pageUrl = boardUrl || "https://[사이트]/bbs/board.php?bo_table=notice";

  return (
    <div data-func-id="FN-SRC-006" className="flex flex-col gap-4">
      <p data-ui-id="SOURCE-004-U03" className="m-0 text-[13px] text-ink-2">
        사이트 화면을 그대로 불러옵니다. 오른쪽 순서대로 원하는 부분을 클릭하면 같은 모양의 다른 글도 함께 잡힙니다
      </p>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,380px),1fr))] items-start gap-5">
        {/* 사이트 미리보기 (MOCK) */}
        <div data-ui-id="SOURCE-004-U04" className="overflow-hidden rounded-[10px] border border-line bg-surface">
          <div className="flex flex-wrap items-center gap-2.5 border-b border-line bg-canvas px-3 py-2">
            <div role="tablist" aria-label="미리보기 페이지" className="flex gap-0.5">
              {(
                [
                  ["list", "목록 페이지"],
                  ["post", "글 페이지"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={m.previewPage === id}
                  onClick={() => patch({ previewPage: id })}
                  className={cx(
                    "h-[34px] rounded-control border-none px-3.5 text-[13px] font-semibold",
                    m.previewPage === id ? "bg-surface shadow-[0_1px_2px_rgba(0,0,0,.1)]" : "bg-transparent",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="min-w-[120px] flex-1 truncate font-mono text-xs text-ink-2">
              {m.previewPage === "list" ? pageUrl : `${pageUrl}&wr_id=124`}
            </span>
            <Button size="sm" className="h-[34px] text-[13px]" onClick={() => toast("미리보기를 다시 불러왔습니다 (MOCK)")}>
              새로고침
            </Button>
          </div>

          {m.previewPage === "list" ? (
            <div data-ui-id="SOURCE-004-U05" className="p-5">
              <div className="mb-3.5 h-[34px] rounded-md bg-subtle" />
              <div className="mb-3 h-3.5 w-[140px] rounded-md bg-subtle" />
              {/* 좁은 화면에서는 겹치지 않도록 가로로 스크롤한다 */}
              <div className="overflow-x-auto pt-3">
                <div className="flex min-w-[400px] flex-col gap-1 border-t-2 border-line-strong pt-1.5">
                  {PREVIEW_ROWS.map((no, i) => (
                    <PreviewRow key={no} index={i} no={no} m={m} setState={setState} />
                  ))}
                </div>
              </div>
              <div className="mt-4 flex justify-center gap-1.5">
                {[1, 2, 3].map((n) => (
                  <span key={n} className="flex size-[30px] items-center justify-center rounded border border-field text-xs">
                    {n}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3 p-5">
              <div className="h-[22px] w-3/5 rounded-md bg-line" />
              <div className="h-3 w-[30%] rounded-md bg-subtle" />
              <div
                onClick={() => st.s5 === "selecting" && setSteps({ s5: "done" })}
                className={cx(
                  "relative flex flex-col gap-2 rounded-md border-2 p-3",
                  st.s5 === "done" ? "border-primary bg-nav-active" : st.s5 === "selecting" ? "cursor-pointer border-dashed border-warn" : "border-transparent",
                )}
              >
                <div className="h-2.5 rounded-[5px] bg-line" />
                <div className="h-2.5 w-[94%] rounded-[5px] bg-line" />
                <div className="h-2.5 w-[88%] rounded-[5px] bg-line" />
                <div className="h-2.5 w-[70%] rounded-[5px] bg-line" />
                {st.s5 === "done" && <Tag className="-top-[11px] right-2 bg-primary">본문 영역</Tag>}
              </div>
              <div className="h-3 w-2/5 rounded-md bg-subtle" />
            </div>
          )}
        </div>

        {/* 단계 안내 */}
        <div className="flex flex-col gap-3">
          <div data-ui-id="SOURCE-004-U06" role="status" className="rounded-control bg-nav-active px-3.5 py-3 text-sm font-semibold text-primary">
            {instruction}
          </div>
          <div data-ui-id="SOURCE-004-U07" className="flex flex-col gap-2.5">
            {steps.map((s) => {
              const [stateLabel, stateColor] = STEP_STATE[st[s.key]];
              const active = st[s.key] === "selecting";
              return (
                <div
                  key={s.key}
                  className={cx(
                    "flex flex-col gap-2 rounded-[10px] bg-surface p-3.5",
                    active ? "border-2 border-primary" : "m-px border border-line",
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="flex size-[22px] items-center justify-center rounded-full bg-subtle text-[11px] font-bold">{s.n}</span>
                    <strong className="flex-1 text-sm">{s.title}</strong>
                    <span className={cx("text-xs font-semibold", stateColor)}>{stateLabel}</span>
                  </div>
                  <p className="m-0 ml-8 text-[13px] leading-[1.55] text-ink-2">{s.desc}</p>
                  {s.actions.length > 0 && (
                    <div className="ml-8 flex flex-wrap gap-2">
                      {s.actions.map((a) => (
                        <Button key={a.label} size="sm" className="h-[34px] text-[13px]" disabled={a.disabled} onClick={a.onClick}>
                          {a.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <details data-ui-id="SOURCE-004-U08" className="rounded-[10px] border border-line bg-surface px-3.5 py-3">
            <summary className="cursor-pointer text-[13px] font-semibold">고급: 선택된 값(선택자) 보기·직접 수정</summary>
            <div className="mt-3 flex flex-col gap-2.5">
              <SelectorInput label="목록 한 줄" placeholder="(선택 전)" value={m.sel.row} onChange={(row) => patch({ sel: { ...m.sel, row } })} />
              <SelectorInput label="글 링크" placeholder="(선택 중)" value={m.sel.link} onChange={(link) => patch({ sel: { ...m.sel, link } })} />
            </div>
          </details>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <strong className="text-[13px]">추출 결과 미리보기 — 지금 선택으로 가져올 글</strong>
        <Table data-ui-id="SOURCE-004-U09">
          <thead>
            <tr>
              <Th className="w-[62%]">제목</Th>
              <Th>날짜</Th>
              <Th>URL</Th>
            </tr>
          </thead>
          <tbody>
            {s2done &&
              [1, 2, 3, 4].map((i) => (
                <tr key={i}>
                  <Td className="py-3">[게시글 제목]</Td>
                  <Td className="py-3 font-mono text-[13px]">[MM-DD]</Td>
                  <Td className="py-3 font-mono text-[13px]">…wr_id={125 - i}</Td>
                </tr>
              ))}
          </tbody>
        </Table>
        {!s2done && <p className="m-0 py-2 text-[13px] text-muted">글 링크를 선택하면 가져올 글이 표시됩니다 [추정]</p>}
      </div>
    </div>
  );
}

function PreviewRow({
  index: i,
  no,
  m,
  setState,
}: {
  index: number;
  no: string;
  m: ManualState;
  setState: (next: ManualState) => void;
}) {
  const st = m.steps;
  const notice = i === 0;
  const isSel = m.selRow === i;
  const sameShape = st.s1 === "done" && !notice && !isSel;
  const titlePick = isSel && (st.s2 === "selecting" || m.mode === "title");
  const datePick = isSel && m.mode === "date";
  const rowPickable = st.s1 === "selecting" && !notice;

  const onRow = () => {
    if (rowPickable) setState({ ...m, selRow: i, steps: { ...st, s1: "done", s2: "selecting" }, sel: { ...m.sel, row: "#bo_list tbody tr" } });
  };
  const onTitle = (e: React.MouseEvent) => {
    if (!isSel) return;
    if (st.s2 === "selecting") {
      e.stopPropagation();
      setState({ ...m, steps: { ...st, s2: "done" }, sel: { ...m.sel, link: "td.subject a" } });
    } else if (m.mode === "title") {
      e.stopPropagation();
      setState({ ...m, steps: { ...st, s3: "done" }, mode: null });
    }
  };
  const onDate = (e: React.MouseEvent) => {
    if (isSel && m.mode === "date") {
      e.stopPropagation();
      setState({ ...m, steps: { ...st, s4: "done" }, mode: null });
    }
  };

  return (
    <div
      onClick={onRow}
      className={cx(
        "relative flex items-center gap-2 rounded border-2 p-2.5",
        rowPickable ? "cursor-pointer hover:bg-hover" : "cursor-default",
        isSel ? "border-primary bg-nav-active" : sameShape ? "border-dashed border-primary" : "border-transparent",
      )}
    >
      {isSel && <Tag className="-top-[11px] left-1.5 bg-primary">목록 한 줄</Tag>}
      <span className="w-14 text-xs text-ink-2">{no}</span>
      <span className="flex min-w-0 flex-1 items-center gap-1.5">
        <span
          onClick={onTitle}
          className={cx(
            "rounded-[3px] px-1 py-0.5 text-[13px] whitespace-nowrap underline",
            titlePick && "cursor-pointer bg-alert outline-2 outline-warn",
          )}
        >
          [게시글 제목]
        </span>
        {isSel && st.s2 === "selecting" && <Tag className="static bg-warn">글 링크?</Tag>}
      </span>
      <span className="w-[70px] text-xs text-ink-2">[작성자]</span>
      <span
        onClick={onDate}
        className={cx("w-[60px] rounded-[3px] px-1 py-0.5 font-mono text-xs", datePick && "cursor-pointer outline-2 outline-warn")}
      >
        [MM-DD]
      </span>
    </div>
  );
}

function Tag({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={cx("absolute rounded px-2 py-px text-[11px] font-bold text-white", className)}>{children}</span>;
}

function SelectorInput({
  label,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs font-semibold">
      {label}
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-control border border-field px-2.5 font-mono text-xs font-normal outline-none focus:border-primary"
      />
    </label>
  );
}
