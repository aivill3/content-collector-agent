"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox, Field, FieldError, Input, Select } from "@/components/ui/field";
import { Table, Td, Th } from "@/components/ui/table";
import { UnderlineTab, UnderlineTabs } from "@/components/ui/underline-tabs";
import { api, errorText } from "@/lib/api";
import { shortDate } from "@/lib/labels";
import { cx } from "@/lib/cx";
import type { BoardDetectResult } from "@/lib/types";
import { BoardManual, type ManualState } from "./board-manual";
import { FieldGrid, FormSection } from "./form-section";
import { scopeSummary, type BoardMode, type FormProps } from "./values";

// SOURCE-003/004 · 2 목록 탐지 / 3 수집 범위

/** 자동 탐지 결과 — 탭을 오가도 남도록 폼 화면이 들고 있는다. 미리보기 글은 후보마다 함께 온다 */
export interface AutoState {
  detect: BoardDetectResult | null;
  candIdx: number;
}

export const INITIAL_AUTO: AutoState = { detect: null, candIdx: 0 };

export function BoardDetectSection({
  form,
  mode,
  modeHref,
  auto,
  setAuto,
  manual,
  setManual,
}: {
  form: FormProps;
  mode: BoardMode;
  /** 탭 전환은 URL(?mode=)로 — 입력값은 그대로 유지된다 [확인 필요] */
  modeHref: (mode: BoardMode) => string;
  auto: AutoState;
  setAuto: (next: AutoState) => void;
  manual: ManualState;
  setManual: (next: ManualState) => void;
}) {
  return (
    <FormSection n={2} title="목록 탐지">
      <UnderlineTabs data-ui-id="SOURCE-003-U04" label="탐지 방식" className="gap-6">
        <UnderlineTab href={modeHref("auto")} active={mode === "auto"}>
          자동 탐지
        </UnderlineTab>
        <UnderlineTab href={modeHref("manual")} active={mode === "manual"}>
          수동 설정 (페이지에서 선택)
        </UnderlineTab>
      </UnderlineTabs>
      {mode === "auto" ? (
        <BoardAuto form={form} state={auto} setState={setAuto} />
      ) : (
        <BoardManual state={manual} setState={setManual} boardUrl={form.v.boardUrl} />
      )}
    </FormSection>
  );
}

function BoardAuto({ form: { v, set, setErr }, state, setState }: { form: FormProps; state: AutoState; setState: (next: AutoState) => void }) {
  const [detecting, setDetecting] = useState(false);
  const [detectErr, setDetectErr] = useState("");

  // FUNC: FN-SRC-004 — robots.txt 확인 → 목록 수집 → 후보 묶음 (묶음별 글 미리보기 포함)
  const detect = async () => {
    const url = v.boardUrl.trim();
    if (!url) return setErr({ boardUrl: "게시판 목록 URL을 입력하세요" });
    setErr({ boardUrl: undefined });
    setDetectErr("");
    setDetecting(true);
    try {
      const d = await api.detectBoard(url);
      // 편집 중이면 저장해 둔 묶음을 그대로 고른다. 사라졌으면 1순위
      const saved = d.candidates.findIndex((c) => c.pattern === v.listPattern);
      const idx = Math.max(0, saved);
      setState({ detect: d, candIdx: idx });
      set({ listPattern: d.candidates[idx]?.pattern ?? "" });
    } catch (e) {
      setDetectErr(errorText(e, "탐지하지 못했습니다 [문구 확인 필요]"));
    } finally {
      setDetecting(false);
    }
  };

  // FUNC: FN-SRC-005 — 후보 묶음 채택 (미리보기는 탐지 결과에 있어 다시 요청하지 않는다)
  const pick = (i: number) => {
    if (!state.detect) return;
    set({ listPattern: state.detect.candidates[i].pattern });
    setState({ ...state, candIdx: i });
  };

  const d = state.detect;
  const posts = d?.candidates[state.candIdx]?.posts ?? [];
  return (
    <div data-func-id="FN-SRC-004" className="flex flex-col gap-3.5">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="primary" data-ui-id="SOURCE-003-U05" onClick={detect} disabled={detecting}>
          {detecting ? "탐지 중…" : "탐지 실행"}
        </Button>
        {d ? (
          <span data-ui-id="SOURCE-003-U06" className="flex items-center gap-2.5 text-[13px] text-ink-2">
            <Badge tone={d.robots ? "green" : "orange"}>{d.robots ? "robots.txt 허용" : "robots.txt 차단"}</Badge>
            {/* robots 차단이면 목록 페이지를 요청하지 않는다 */}
            {!d.robots
              ? "이 게시판은 수집할 수 없습니다 [문구 확인 필요]"
              : d.httpOk
                ? "목록 페이지 응답 정상"
                : "목록 페이지 응답 오류 [문구 확인 필요]"}
          </span>
        ) : (
          !detecting && <span className="text-[13px] text-muted">목록 URL을 넣고 탐지를 실행하세요 [문구 확인 필요]</span>
        )}
      </div>
      <FieldError>{detectErr}</FieldError>
      {d?.httpOk && d.candidates.length === 0 && (
        <p className="m-0 text-[13px] text-muted">
          글 목록으로 보이는 링크 묶음을 찾지 못했습니다. 자바스크립트로 목록을 그리는 게시판일 수 있습니다 — &apos;수동 설정&apos; 탭을 사용하세요 [문구 확인 필요]
        </p>
      )}
      {d && d.candidates.length > 0 && (
        <>
          <div data-ui-id="SOURCE-003-U07" data-func-id="FN-SRC-005" role="radiogroup" aria-labelledby="cand-label" className="flex flex-col gap-2">
            <span id="cand-label" className="text-[13px] font-semibold">
              후보 묶음 — 글 번호만 다른 링크가 많이 반복된 순서
            </span>
            {d.candidates.map((c, i) => {
              const on = state.candIdx === i;
              return (
                <label
                  key={c.pattern}
                  className={cx(
                    "flex cursor-pointer items-center gap-3 rounded-control border px-3.5 py-3",
                    on ? "border-primary bg-nav-active" : "border-line bg-surface",
                  )}
                >
                  <input type="radio" name="cand" checked={on} onChange={() => pick(i)} className="m-0 accent-primary" />
                  <span className="flex-1 truncate font-mono text-[13px]">{c.pattern}</span>
                  <span className="text-xs text-ink-2">{c.links}개 링크</span>
                  {on && <span className="text-xs font-bold text-primary">채택</span>}
                </label>
              );
            })}
          </div>
          <Table data-ui-id="SOURCE-003-U08">
            <thead>
              <tr>
                <Th className="w-[45%]">채택 묶음으로 찾은 글 (미리보기)</Th>
                <Th className="whitespace-nowrap">날짜</Th>
                <Th>URL</Th>
              </tr>
            </thead>
            <tbody>
              {posts.map((p) => (
                <tr key={p.url}>
                  <Td className="py-3">{p.title}</Td>
                  <Td className="py-3 pr-3 font-mono text-[13px] whitespace-nowrap">{shortDate(p.date)}</Td>
                  <Td className="py-3 font-mono text-[13px] break-all">{p.url}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <p data-ui-id="SOURCE-003-U09" className="m-0 text-[13px] text-muted">
            결과가 이상하면 다른 후보를 고르거나 &apos;수동 설정&apos; 탭에서 페이지를 보며 직접 선택합니다
          </p>
        </>
      )}
    </div>
  );
}

export function BoardScopeSection({
  form: { v, set },
  collapsible,
  open,
  onToggle,
}: {
  form: FormProps;
  collapsible: boolean;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <FormSection
      n={3}
      title="수집 범위"
      data-func-id="FN-SRC-008"
      collapsible={collapsible}
      open={open}
      onToggle={onToggle}
      summary={scopeSummary(v)}
      summaryUiId="SOURCE-004-U10"
    >
      <FieldGrid>
        <Field label="페이지 파라미터" hint="주소에서 페이지 번호 이름 (…&page=2)">
          <Input data-ui-id="SOURCE-003-U10" className="font-mono" value={v.pageParam} onChange={(e) => set({ pageParam: e.target.value })} />
        </Field>
        {/* 상한 [정책 필요] */}
        <Field label="페이지 수" hint="목록 1쪽, 2쪽… 몇 쪽까지 볼지">
          <Input data-ui-id="SOURCE-003-U11" type="number" min={1} value={v.pages} onChange={(e) => set({ pages: e.target.value })} />
        </Field>
        <Field label="최대 글 수" hint="한 번에 가져올 글 개수 상한">
          <Input data-ui-id="SOURCE-003-U12" type="number" min={1} value={v.maxPosts} onChange={(e) => set({ maxPosts: e.target.value })} />
        </Field>
        {/* [확인 필요] 정규식 여부 */}
        <Field label="포함 URL 패턴 (선택)">
          <Input data-ui-id="SOURCE-003-U13" className="font-mono" value={v.urlPattern} onChange={(e) => set({ urlPattern: e.target.value })} />
        </Field>
        <Field label="최소 본문 길이" hint="자">
          <Input data-ui-id="SOURCE-003-U14" type="number" min={0} value={v.minLen} onChange={(e) => set({ minLen: e.target.value })} />
        </Field>
        <Field label="조회 기간">
          <Select data-ui-id="SOURCE-003-U15" value={v.boardPeriod} onChange={(e) => set({ boardPeriod: e.target.value })}>
            <option value="none">제한 없음</option>
            <option value="7d">최근 7일</option>
            <option value="30d">최근 30일</option>
          </Select>
        </Field>
      </FieldGrid>
      <Checkbox
        data-ui-id="SOURCE-003-U16"
        label="'공지' 줄 제외"
        hint="상단 고정 공지가 매번 수집되는 것을 막습니다"
        checked={v.skipNotice}
        onChange={(e) => set({ skipNotice: e.target.checked })}
      />
      <Checkbox
        data-ui-id="SOURCE-003-U17"
        label="비한국어 글도 수집"
        checked={v.nonKorean}
        onChange={(e) => set({ nonKorean: e.target.checked })}
      />
    </FormSection>
  );
}
