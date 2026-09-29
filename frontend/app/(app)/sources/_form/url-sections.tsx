"use client";

import { useState } from "react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox, Field, Input, Select, Textarea } from "@/components/ui/field";
import { Table, Td, Th } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { UrlCheckResult } from "@/lib/types";
import { FormSection } from "./form-section";
import { urlList, type FormProps } from "./values";

// SOURCE-005 · 2 글 주소 / 3 옵션 / 4 분석 설정

const RESULT_BADGE: Record<UrlCheckResult["result"], [string, BadgeTone]> = {
  ok: ["확인됨", "green"],
  short: ["본문 짧음", "orange"],
  robots: ["robots 차단", "orange"],
};

export function UrlSections({ v, set, err, setErr }: FormProps) {
  const [checking, setChecking] = useState(false);
  const [results, setResults] = useState<UrlCheckResult[] | null>(null);

  const lines = v.urls.split("\n").map((x) => x.trim()).filter(Boolean);
  const dup = lines.length - new Set(lines).size;

  // FUNC: FN-SRC-007
  const check = async () => {
    const list = urlList(v.urls);
    if (!list.length) return setErr({ urls: "주소를 1개 이상 입력하세요" });
    setErr({ urls: undefined });
    setChecking(true);
    try {
      setResults(await api.checkUrls(list, Number(v.minLen) || 0));
    } catch {
      setErr({ urls: "주소를 확인하지 못했습니다 [문구 확인 필요]" });
    } finally {
      setChecking(false);
    }
  };

  return (
    <>
      <FormSection n={2} title="글 주소" data-func-id="FN-SRC-007" className="gap-3.5">
        <Field label="주소 목록" hint={`한 줄에 하나씩 · ${lines.length}개 입력됨 · 중복 ${dup}개 제외`} error={err.urls}>
          <Textarea
            data-ui-id="SOURCE-005-U03"
            rows={5}
            value={v.urls}
            onChange={(e) => set({ urls: e.target.value })}
            aria-invalid={!!err.urls}
            placeholder="https://[사이트]/[글 주소 1]"
            className="font-mono text-[13px]"
          />
        </Field>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" data-ui-id="SOURCE-005-U04" onClick={check} disabled={checking}>
            {checking ? "확인 중…" : "주소 확인"}
          </Button>
          <span className="text-[13px] text-muted">각 주소에 접속해 본문을 가져올 수 있는지 미리 확인합니다</span>
        </div>
        {results && (
          <>
            <Table data-ui-id="SOURCE-005-U05">
              <thead>
                <tr>
                  <Th className="w-[58%]">주소</Th>
                  <Th>확인 결과</Th>
                  <Th>본문</Th>
                </tr>
              </thead>
              <tbody>
                {results.map((u) => {
                  const [label, tone] = RESULT_BADGE[u.result];
                  return (
                    <tr key={u.url}>
                      <Td className="py-3 pr-3 font-mono text-[13px] break-all">{u.url}</Td>
                      <Td className="py-3">
                        <Badge tone={tone}>{label}</Badge>
                      </Td>
                      <Td className="py-3 text-ink-2">{u.text}</Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
            {/* MOCK — 본문 미리보기 자리 */}
            <div data-ui-id="SOURCE-005-U06" className="flex flex-col gap-2 rounded-[10px] bg-subtle p-4">
              <strong className="text-[13px]">첫 번째 글 본문 미리보기</strong>
              <strong className="text-[15px]">[글 제목]</strong>
              <span className="text-[13px] text-muted">[사이트명] · [발행일]</span>
              {["w-full", "w-[94%]", "w-[97%]", "w-[70%]"].map((w) => (
                <div key={w} className={`h-[9px] rounded-[5px] bg-field ${w}`} />
              ))}
            </div>
          </>
        )}
      </FormSection>

      <FormSection n={3} title="옵션" className="gap-3.5">
        <Field label="최소 본문 길이" hint="자" className="max-w-[350px]">
          <Input data-ui-id="SOURCE-005-U07" type="number" min={0} value={v.minLen} onChange={(e) => set({ minLen: e.target.value })} />
        </Field>
        <Checkbox
          data-ui-id="SOURCE-005-U08"
          label="비한국어 글도 수집"
          checked={v.nonKorean}
          onChange={(e) => set({ nonKorean: e.target.checked })}
        />
      </FormSection>

      <FormSection n={4} title="분석 설정" className="gap-3.5">
        <Field label="분석 설정" hint="글 단위 지표·단어별 밀도에 적용 (키워드 관련도는 해당 없음)" className="max-w-[530px]">
          <Select
            data-ui-id="SOURCE-005-U09"
            value={v.analysis}
            onChange={(e) => set({ analysis: e.target.value as "default" | "custom" })}
          >
            <option value="default">내 기본값 사용</option>
            <option value="custom">개별 설정</option>
          </Select>
        </Field>
        <p data-ui-id="SOURCE-005-U10" className="m-0 text-[13px] text-ink-2">
          URL 수집은 한 번만 실행합니다. 정기 수집이 필요하면 게시판 유형을 사용하세요
        </p>
      </FormSection>
    </>
  );
}
