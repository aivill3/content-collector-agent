"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { Table, Td, Th } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { UnderlineTab, UnderlineTabs } from "@/components/ui/underline-tabs";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import { POS_RANGE_LABEL, RELEVANCE_BADGE, SOURCE_TYPE_LABEL, denomLabel } from "@/lib/labels";
import { useApiData } from "@/lib/use-api-data";
import type { AnalyzedContentDetail, Content, ContentMetrics } from "@/lib/types";

// CONTENT-002 정제 본문 / CONTENT-003 원본 본문

type Tab = "clean" | "raw";

const METRIC_ROWS: [keyof ContentMetrics, string][] = [
  ["tokens", "전체 토큰 수"],
  ["unique", "고유 토큰 수"],
  ["nouns", "명사 수"],
  ["sentences", "문장 수"],
  ["avgLen", "문장당 평균 글자 수"],
  ["ttr", "어휘 다양도"],
];

const header = <PageHeader title="콘텐츠 상세" description="본문과 형태소 지표, 키워드 관련도를 함께 봅니다" />;

export function ContentDetailScreen({ id, tab }: { id: string; tab: Tab }) {
  const { data, error, loading, reload } = useApiData(() => api.getContent(id), id);
  const screenId = tab === "raw" ? "CONTENT-003" : "CONTENT-002";

  if (loading) return <PageSkeleton />;
  if (error) return <ErrorState onRetry={() => reload("full")} />;

  return (
    <div data-screen-label="CONTENT-002/003 콘텐츠 상세" data-screen-id={screenId} className="flex flex-col gap-6">
      {header}
      {!data ? (
        <div role="alert" className="flex flex-col items-start gap-2.5 rounded-card border border-line bg-surface p-8">
          <strong>글을 찾을 수 없습니다</strong>
          <span className="text-[13px] text-muted">[확인 필요] 삭제된 글 처리 정책 미정</span>
          <Link href="/contents" className="font-semibold">
            ← 콘텐츠 목록
          </Link>
        </div>
      ) : (
        <div className="flex flex-wrap items-start gap-6">
          <Body content={data.content} tab={tab} />
          <aside className="flex min-w-0 flex-[1_1_300px] flex-col gap-4">
            {data.analyzed ? (
              <>
                {data.content.type === "news" && <RelevanceCard detail={data} />}
                <MetricsCard detail={data} />
                <TopWordsCard detail={data} onReanalyzed={() => reload("quiet")} />
              </>
            ) : (
              <CollectInfoCard content={data.content} />
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

function Body({ content: c, tab }: { content: Content; tab: Tab }) {
  const toast = useToast();
  const rel = c.relevance ? RELEVANCE_BADGE[c.relevance] : null;
  const meta = [
    c.outlet,
    c.published ? `발행 ${c.published}` : null,
    `수집 ${c.collected}`,
    c.keyword ? `키워드 '${c.keyword}'` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  // FUNC: FN-CNT-006 — 복사 대상은 정제 본문으로 가정 [확인 필요]
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(c.title + "\n\n" + c.paragraphs.join("\n\n"));
      toast("본문을 복사했습니다");
    } catch {
      toast("복사하지 못했습니다 [문구 확인 필요]");
    }
  };

  return (
    <article className="flex min-h-[720px] min-w-0 flex-[1.75_1_520px] flex-col gap-3.5 rounded-card border border-line bg-surface p-6">
      <Link data-ui-id="CONTENT-002-U01" href="/contents" className="text-[13px] font-semibold">
        ← 콘텐츠 목록
      </Link>
      <h2 data-ui-id="CONTENT-002-U02" className="m-0 text-2xl font-bold text-pretty">
        {c.title}
      </h2>
      <div data-ui-id="CONTENT-002-U03" className="flex flex-wrap items-center gap-2 text-[13px] text-muted">
        <Badge>{SOURCE_TYPE_LABEL[c.type]}</Badge>
        <span>{meta}</span>
        {rel && <Badge tone={rel[1]}>{rel[0]}</Badge>}
      </div>
      <div className="flex gap-2">
        <a
          data-ui-id="CONTENT-002-U04"
          data-func-id="FN-CNT-005"
          href={c.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-9 items-center rounded-control border border-field bg-surface px-3.5 text-sm font-semibold text-ink hover:bg-hover hover:text-ink hover:no-underline"
        >
          원문 열기
        </a>
        <Button size="sm" data-ui-id="CONTENT-002-U05" data-func-id="FN-CNT-006" onClick={copy}>
          복사
        </Button>
      </div>

      <UnderlineTabs data-ui-id="CONTENT-002-U06" label="본문 보기" className="mt-1.5 gap-6">
        <UnderlineTab href={`/contents/${c.id}`} active={tab === "clean"}>
          정제 본문
        </UnderlineTab>
        <UnderlineTab href={`/contents/${c.id}?tab=raw`} active={tab === "raw"}>
          원본 본문 (정제 전)
        </UnderlineTab>
      </UnderlineTabs>

      {tab === "clean" ? (
        <div data-ui-id="CONTENT-002-U07" className="flex flex-col gap-3.5 text-[15px] leading-[1.8] text-ink">
          {c.paragraphs.map((p, i) => (
            <p key={i} className="m-0">
              {p}
            </p>
          ))}
        </div>
      ) : c.rawBody !== undefined ? (
        // 백엔드 연결 시: 정제 전 본문을 그대로 보여 준다 (제거 위치 표시는 아직 없다)
        <>
          <p data-ui-id="CONTENT-003-U07" className="m-0 text-[13px] leading-relaxed text-muted">
            수집 직후 추출된 그대로의 본문입니다. 필요한 내용이 정제에서 지워졌다면 정제 본문과 비교해 확인합니다
          </p>
          <div data-ui-id="CONTENT-003-U08" className="flex flex-col gap-2.5 text-[15px] leading-[1.8] text-ink">
            {c.rawBody
              .split(/\n+/)
              .filter((p) => p.trim())
              .map((p, i) => (
                <p key={i} className="m-0">
                  {p}
                </p>
              ))}
          </div>
        </>
      ) : (
        <>
          <p data-ui-id="CONTENT-003-U07" className="m-0 text-[13px] leading-relaxed text-muted">
            수집 직후 추출된 그대로의 본문입니다. 정제 규칙이 지운 부분을 주황색으로 표시합니다 — 필요한 내용이 지워졌다면
            여기서 확인합니다
          </p>
          <div data-ui-id="CONTENT-003-U08" data-func-id="FN-CNT-004" className="flex flex-col gap-2.5 text-[15px] leading-[1.8] text-ink">
            {c.paragraphs.map((p, i) => (
              <RawParagraph key={i} text={p} removed={c.removed.filter((r) => r.after === i)} />
            ))}
          </div>
        </>
      )}
    </article>
  );
}

function RawParagraph({ text, removed }: { text: string; removed: Content["removed"] }) {
  return (
    <>
      <p className="m-0">{text}</p>
      {removed.map((r, i) => (
        <div
          key={i}
          data-ui-id="CONTENT-003-U09"
          className="flex flex-wrap items-center justify-between gap-4 rounded-md bg-alert px-3 py-2"
        >
          <span className="text-sm text-alert-ink">{r.text}</span>
          <span className="text-xs font-semibold whitespace-nowrap text-warn">정제에서 제거: {r.reason}</span>
        </div>
      ))}
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line-soft py-3.5">
      <span>{label}</span>
      {children}
    </div>
  );
}

/** 키워드 분석 전(백엔드 연결 시) — 수집 정보와 검색 키워드 순위 */
function CollectInfoCard({ content: c }: { content: Content }) {
  const mono = "font-mono text-[13px]";
  const hits = c.hits ?? [];
  return (
    <Card className="flex flex-col">
      <h3 className="m-0 mb-2 text-base font-bold">수집 정보</h3>
      <Row label="수집 경로">
        <span>{SOURCE_TYPE_LABEL[c.type]}</span>
      </Row>
      <Row label="본문 길이">
        <span className={mono}>{c.length.toLocaleString()}자</span>
      </Row>
      {hits.length > 0 && (
        <>
          <h4 className="mt-4 mb-1 text-sm font-bold">검색 키워드</h4>
          <Table>
            <thead>
              <tr>
                <Th>키워드</Th>
                <Th>순위</Th>
                <Th>찾은 시각</Th>
              </tr>
            </thead>
            <tbody>
              {hits.map((h) => (
                <tr key={h.keyword}>
                  <Td className="py-3">{h.keyword}</Td>
                  <Td className={cx("py-3", mono)}>{h.rank}위</Td>
                  <Td className={cx("py-3", mono)}>{h.foundAt}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </>
      )}
      <p className="mt-3.5 mb-0 text-[13px] text-muted">키워드 관련도·형태소 지표는 분석 기능이 연결되면 표시됩니다</p>
    </Card>
  );
}

function RelevanceCard({ detail: { content: c, settings: s } }: { detail: AnalyzedContentDetail }) {
  const rel = c.relevance ? RELEVANCE_BADGE[c.relevance] : null;
  const mono = "font-mono text-[13px]";
  return (
    <Card data-ui-id="CONTENT-002-U08" className="flex flex-col">
      <h3 className="m-0 mb-4 text-base font-bold">키워드 관련도</h3>
      <div className="flex items-center justify-between pb-2.5">
        <span className="font-semibold">등록 키워드 &apos;{c.keyword}&apos;</span>
        {rel && <Badge tone={rel[1]}>{rel[0]}</Badge>}
      </div>
      <Row label="언급 횟수">
        <span className={mono}>{c.mentions}회</span>
      </Row>
      <Row label="1,000자당 밀도">
        <span className={mono}>{c.density.toFixed(2)}</span>
      </Row>
      <Row label="제목 포함">
        <span className={mono}>{c.titleHas ? "예" : "아니요"}</span>
      </Row>
      <Row label="본문 길이">
        <span className={mono}>{c.length.toLocaleString()}자</span>
      </Row>
      <p className="mt-3.5 mb-2 text-[13px] text-muted">
        판정 기준: 제목 포함 시 밀도 {s.densTitle.toFixed(1)} 이상, 최소 언급 {s.minMentions}회 —
      </p>
      <Link href="/settings" className="font-semibold">
        분석 설정
      </Link>
    </Card>
  );
}

function MetricsCard({ detail: { content: c, settings: s } }: { detail: AnalyzedContentDetail }) {
  const m = c.metrics;
  const format = (k: keyof ContentMetrics) => (k === "avgLen" ? m.avgLen.toFixed(1) : k === "ttr" ? m.ttr.toFixed(2) : m[k]);
  const ttrLow = m.ttr < s.ttrWarn;
  return (
    <Card data-ui-id="CONTENT-002-U09" className="flex flex-col">
      <h3 className="m-0 mb-2 text-base font-bold">글 단위 지표</h3>
      {/* [추정] 표시 항목은 SETTING-001-U04 '표시할 지표' 설정을 따른다 */}
      {METRIC_ROWS.filter(([k]) => s.metrics[k]).map(([k, label]) => (
        <Row key={k} label={label}>
          <span className="flex items-center gap-2.5">
            {k === "ttr" && (
              <span className={cx("text-xs text-warn", ttrLow ? "font-bold" : "font-normal")}>
                기준 {s.ttrWarn.toFixed(2)} 미만 시 경고
              </span>
            )}
            <span className="font-mono text-[13px]">{format(k)}</span>
          </span>
        </Row>
      ))}
    </Card>
  );
}

function TopWordsCard({
  detail: { content: c, settings: s },
  onReanalyzed,
}: {
  detail: AnalyzedContentDetail;
  onReanalyzed: () => void;
}) {
  const toast = useToast();
  const [reanalyzing, setReanalyzing] = useState(false);

  // FUNC: FN-CNT-007
  const reanalyze = async () => {
    setReanalyzing(true);
    try {
      await api.reanalyzeContent(c.id);
      onReanalyzed();
      toast("이 글을 현재 분석 설정으로 재분석했습니다");
    } catch {
      toast("재분석하지 못했습니다 [문구 확인 필요]");
    } finally {
      setReanalyzing(false);
    }
  };

  return (
    <Card data-ui-id="CONTENT-002-U10" className="flex flex-col gap-2.5">
      <h3 className="m-0 text-base font-bold">상위 키워드</h3>
      <p className="m-0 text-[13px] text-muted">
        분모: {denomLabel(s.denom)} · 품사: {POS_RANGE_LABEL[s.posRange] ?? s.posRange} (분석 설정 기준)
      </p>
      <Table>
        <thead>
          <tr>
            <Th>#</Th>
            <Th>단어</Th>
            <Th>품사</Th>
            <Th>횟수</Th>
            <Th>밀도</Th>
          </tr>
        </thead>
        <tbody>
          {c.topWords.slice(0, s.topN).map((w, i) => (
            <tr key={w.w}>
              <Td className="py-3 text-[13px]">{i + 1}</Td>
              <Td className="py-3">{w.w}</Td>
              <Td className="py-3">
                <Badge strong className="text-[11px]">
                  {w.pos}
                </Badge>
              </Td>
              <Td className="py-3 font-mono text-[13px]">{w.n}</Td>
              <Td className="py-3 font-mono text-[13px]">{w.d.toFixed(1)}%</Td>
            </tr>
          ))}
        </tbody>
      </Table>
      <div data-ui-id="CONTENT-002-U11" data-func-id="FN-CNT-007" className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <span className="text-[13px] text-muted">
          분석 설정 v{c.analyzedVersion}으로 분석됨{c.staleDict ? " (사용자 사전 변경 이전)" : ""}
        </span>
        <Button size="sm" onClick={reanalyze} disabled={reanalyzing}>
          {reanalyzing ? "재분석 중…" : "재분석"}
        </Button>
      </div>
    </Card>
  );
}
