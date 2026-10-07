"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox, Field, FieldError, Input, Select } from "@/components/ui/field";
import { Table, Td, Th } from "@/components/ui/table";
import { api, errorText } from "@/lib/api";
import { shortDate } from "@/lib/labels";
import type { SearchPreview } from "@/lib/types";
import { FieldGrid, FormSection } from "./form-section";
import { today, type FormProps } from "./values";

// SOURCE-002 · 2 검색 키워드 / 3 검색 옵션

export function NewsSections({ v, set, err, setErr }: FormProps) {
  const [kwInput, setKwInput] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchErr, setSearchErr] = useState("");
  const [results, setResults] = useState<SearchPreview[] | null>(null);

  // FUNC: FN-SRC-002 키워드 추가/삭제
  const addKeyword = () => {
    const kw = kwInput.trim();
    if (!kw) return setErr({ keywords: "키워드를 입력하세요 [문구 확인 필요]" });
    if (v.keywords.some((k) => k.kw === kw)) return setErr({ keywords: "이미 추가된 키워드입니다 [추정]" });
    set({ keywords: [...v.keywords, { kw, origin: "직접 입력", added: today(), recent: null }] });
    setKwInput("");
    setErr({ keywords: undefined });
  };

  // FUNC: FN-SRC-003 — 첫 키워드로 5건 미리보기
  const searchTest = async () => {
    if (!v.keywords.length) return setSearchErr("키워드를 1개 이상 추가하세요 [문구 확인 필요]");
    setSearchErr("");
    setSearching(true);
    try {
      setResults(await api.searchTest(v.keywords[0].kw));
    } catch (e) {
      setSearchErr(errorText(e, "검색하지 못했습니다 [문구 확인 필요]"));
    } finally {
      setSearching(false);
    }
  };

  return (
    <>
      <FormSection n={2} title="검색 키워드" data-func-id="FN-SRC-002" className="gap-3.5">
        <label htmlFor="kw-input" className="text-[13px] font-semibold">
          키워드 추가
        </label>
        <div data-ui-id="SOURCE-002-U03" className="flex gap-3">
          <Input
            id="kw-input"
            value={kwInput}
            onChange={(e) => setKwInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.nativeEvent.isComposing) {
                e.preventDefault();
                addKeyword();
              }
            }}
            aria-invalid={!!err.keywords}
            className="min-w-0 flex-1"
          />
          <Button variant="primary" className="h-10 px-[18px]" onClick={addKeyword}>
            추가
          </Button>
        </div>
        <FieldError>{err.keywords}</FieldError>
        <p data-ui-id="SOURCE-002-U04" className="m-0 text-[13px] text-muted">
          키워드마다 네이버 뉴스를 따로 검색합니다. 같은 기사가 여러 키워드에 걸리면 한 번만 저장합니다
        </p>
        <Table data-ui-id="SOURCE-002-U05">
          <thead>
            <tr>
              <Th className="w-1/2">키워드</Th>
              <Th>출처</Th>
              <Th>추가일</Th>
              <Th>최근 수집</Th>
              <Th>
                <span className="sr-only">삭제</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {v.keywords.map((k) => (
              <tr key={k.kw}>
                <Td className="py-3 font-bold">{k.kw}</Td>
                <Td className="py-3">
                  <Badge tone={k.origin === "직접 입력" ? "gray" : "blue"}>{k.origin}</Badge>
                </Td>
                <Td className="py-3 font-mono text-[13px]">{k.added}</Td>
                <Td className="py-3 font-mono text-[13px]">{k.recent == null ? "—" : `${k.recent}건`}</Td>
                <Td className="py-3 text-right">
                  <Button
                    size="sm"
                    className="px-4"
                    aria-label={`${k.kw} 삭제`}
                    onClick={() => set({ keywords: v.keywords.filter((x) => x.kw !== k.kw) })}
                  >
                    삭제
                  </Button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
        {v.keywords.length === 0 && (
          <p className="m-0 py-2 text-center text-[13px] text-muted">추가된 키워드가 없습니다 [문구 확인 필요]</p>
        )}
        <p className="m-0 text-[13px] text-muted">
          출처가 &apos;키워드 분석 연관어&apos;인 항목은 키워드 분석 화면의 연관어에서 추가한 키워드입니다
        </p>
      </FormSection>

      <FormSection n={3} title="검색 옵션" data-func-id="FN-SRC-008">
        <FieldGrid>
          <Field label="키워드당 검색 건수" hint="최대 1,000건" error={err.count}>
            <Input
              data-ui-id="SOURCE-002-U06"
              type="number"
              min={1}
              max={1000}
              value={v.count}
              onChange={(e) => set({ count: e.target.value })}
              aria-invalid={!!err.count}
            />
          </Field>
          <Field label="정렬" hint="관련도순 · 최신순">
            <Select data-ui-id="SOURCE-002-U07" value={v.sort} onChange={(e) => set({ sort: e.target.value as "sim" | "date" })}>
              <option value="sim">관련도순</option>
              <option value="date">최신순</option>
            </Select>
          </Field>
          {/* [확인 필요] 선택지 */}
          <Field label="조회 기간" hint="발행일 기준">
            <Select data-ui-id="SOURCE-002-U08" value={v.period} onChange={(e) => set({ period: e.target.value })}>
              <option value="1d">최근 1일</option>
              <option value="3d">최근 3일</option>
              <option value="7d">최근 7일</option>
              <option value="none">제한 없음</option>
            </Select>
          </Field>
        </FieldGrid>
        <Checkbox
          data-ui-id="SOURCE-002-U09"
          label="비한국어 기사도 수집"
          checked={v.nonKorean}
          onChange={(e) => set({ nonKorean: e.target.checked })}
        />
        <div className="flex flex-wrap items-center gap-3">
          <Button data-ui-id="SOURCE-002-U10" data-func-id="FN-SRC-003" onClick={searchTest} disabled={searching}>
            {searching ? "검색 중…" : "검색 테스트"}
          </Button>
          <span className="text-[13px] text-muted">저장 전에 첫 키워드로 실제 검색 결과 5건을 미리 봅니다</span>
        </div>
        <FieldError>{searchErr}</FieldError>
        {results?.length === 0 && (
          <p className="m-0 text-[13px] text-muted">&apos;{v.keywords[0]?.kw}&apos; 검색 결과가 없습니다 [문구 확인 필요]</p>
        )}
        {results && results.length > 0 && (
          <Table data-ui-id="SOURCE-002-U11">
            <thead>
              <tr>
                <Th className="w-[55%]">검색 결과 미리보기</Th>
                <Th>언론사</Th>
                <Th>발행일</Th>
                <Th>키워드</Th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.url}>
                  <Td className="py-3">
                    <a href={r.url} target="_blank" rel="noreferrer" className="hover:underline">
                      {r.title}
                    </a>
                  </Td>
                  <Td className="py-3 text-ink-2">{r.outlet}</Td>
                  <Td className="py-3 font-mono text-[13px]">{shortDate(r.date)}</Td>
                  <Td className="py-3 text-ink-2">{r.keyword}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </FormSection>
    </>
  );
}
