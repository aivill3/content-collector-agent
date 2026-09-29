"use client";

import { Field, Input, Select } from "@/components/ui/field";
import type { Schedule } from "@/lib/types";
import { FieldGrid, FormSection } from "./form-section";
import { scheduleSummary, type FormProps } from "./values";

// 4 수집 일정 · 분석 설정 (뉴스·게시판)

export function ScheduleSection({
  form: { v, set, err },
  news,
  collapsible,
  open,
  onToggle,
}: {
  form: FormProps;
  /** 뉴스·게시판에 따라 화면 요소 ID 가 다르다 */
  news: boolean;
  collapsible: boolean;
  open: boolean;
  onToggle: () => void;
}) {
  const id = (newsId: number, boardId: number) => (news ? `SOURCE-002-U${newsId}` : `SOURCE-003-U${boardId}`);
  return (
    <FormSection
      n={4}
      title="수집 일정 · 분석 설정"
      data-func-id="FN-SRC-009"
      collapsible={collapsible}
      open={open}
      onToggle={onToggle}
      summary={scheduleSummary(v)}
      summaryUiId="SOURCE-004-U11"
    >
      <FieldGrid>
        <Field label="정기 수집" hint="수동 · 매시간 · 매일 · 매주 · 고급(cron)">
          <Select data-ui-id={id(12, 18)} value={v.schedule} onChange={(e) => set({ schedule: e.target.value as Schedule })}>
            <option value="manual">수동</option>
            <option value="hourly">매시간</option>
            <option value="daily">매일</option>
            <option value="weekly">매주</option>
            <option value="cron">고급(cron)</option>
          </Select>
        </Field>
        <Field label="시각" hint="서버 시간대: KST">
          <Input
            data-ui-id={id(13, 19)}
            type="time"
            className="font-mono"
            value={v.time}
            onChange={(e) => set({ time: e.target.value })}
            disabled={v.schedule === "manual" || v.schedule === "hourly"}
          />
        </Field>
        {/* [확인 필요] 개별 설정 선택 시 동작 */}
        <Field label="분석 설정" hint="개별 설정을 고르면 이 소스에만 다른 판정 기준 적용">
          <Select
            data-ui-id={id(14, 20)}
            value={v.analysis}
            onChange={(e) => set({ analysis: e.target.value as "default" | "custom" })}
          >
            <option value="default">내 기본값 사용</option>
            <option value="custom">개별 설정</option>
          </Select>
        </Field>
      </FieldGrid>
      {/* 최소 실행 간격 [정책 필요] */}
      <Field label="고급: cron 식 (선택)" hint="예) 평일 오전 8시. 입력하면 위 선택보다 우선합니다" error={err.cron}>
        <Input
          data-ui-id={id(15, 21)}
          className="font-mono"
          value={v.cron}
          onChange={(e) => set({ cron: e.target.value })}
          placeholder="0 8 * * 1-5"
          aria-invalid={!!err.cron}
        />
      </Field>
    </FormSection>
  );
}
