// 웹 게시용 클래식 스크립트 번들 (mock/data.js + services/api.js). 원본 수정 시 함께 갱신.
(function(){
// MOCK DATA — 실제 비즈니스 데이터 아님. 백엔드/DB 스키마 미확정 [API 확인 필요]
// 필드 구성은 기획서 7장 데이터 정의(DATA-004~023)를 따른다.

const PARAS = [
  '대회 조직위원회는 이번 대회에 전국 각지의 선수들이 참가한다고 밝혔다. (샘플 본문)',
  '관계자는 경기 운영 방식과 일정이 일부 조정되었으며 참가 신청은 다음 달까지 받는다고 설명했다.',
  '현장에서는 겨루기와 품새 종목이 함께 진행되며, 심판진은 사전 교육을 거쳐 배정된다.',
  '지역 협회는 유소년 선수 육성을 위한 프로그램을 확대하겠다는 계획도 함께 발표했다.',
  '대회 결과는 공식 누리집을 통해 순차적으로 공개될 예정이다.',
];
const REMOVED = [
  { after: 0, reason: '사진 캡션', text: '▲ 지난 대회 개회식 모습 (사진=샘플)' },
  { after: 2, reason: '관련기사 목록', text: '[관련기사] 샘플 관련기사 제목 1 · 샘플 관련기사 제목 2' },
  { after: 4, reason: '기자 바이라인 · 이메일', text: '홍길동 기자 reporter@example.com' },
  { after: 4, reason: '저작권 문구', text: '저작권자 © 샘플일보 무단전재 및 재배포 금지' },
];
const TOP_WORDS = [
  ['태권도', 'NNP', 12, 3.1], ['대회', 'NNG', 9, 2.3], ['선수', 'NNG', 7, 1.8], ['국기원', 'NNP', 5, 1.3],
  ['참가', 'VV', 4, 1.0], ['협회', 'NNG', 4, 1.0], ['WT', 'SL', 3, 0.8], ['일정', 'NNG', 3, 0.8],
  ['겨루기', 'NNG', 3, 0.8], ['품새', 'NNG', 2, 0.5], ['심판', 'NNG', 2, 0.5], ['유소년', 'NNG', 2, 0.5],
  ['운영', 'NNG', 2, 0.5], ['발표', 'NNG', 2, 0.5], ['지역', 'NNG', 2, 0.5],
].map(([w, pos, n, d]) => ({ w, pos, n, d }));

let seq = 0;
function content(o) {
  seq += 1;
  return {
    id: 'C' + String(seq).padStart(3, '0'),
    url: 'https://example.com/article/' + seq,
    collected: '2026-09-28 08:0' + (seq % 10),
    isNew: false, keyword: null, relevance: null,
    mentions: 6, density: 2.1, titleHas: true, length: 1840,
    metrics: { tokens: 412, unique: 238, nouns: 176, sentences: 21, avgLen: 43.2, ttr: 0.58 },
    topWords: TOP_WORDS, analyzedVersion: 3, staleDict: true,
    paragraphs: PARAS, removed: REMOVED,
    ...o,
  };
}

function createMockStore() {
  seq = 0;
  const sources = [
    { id: 'S1', name: '태권도 뉴스', type: 'news', target: '태권도, 국기원', schedule: 'daily', time: '08:00', cron: '', last: '09-28 08:00', status: 'success', analysis: 'default', recentNew: 12,
      keywords: [
        { kw: '태권도', origin: '직접 입력', added: '2026-09-01', recent: 42 },
        { kw: '국기원', origin: '직접 입력', added: '2026-09-01', recent: 18 },
      ], count: 30, sort: 'sim', period: '3d', nonKorean: false },
    { id: 'S2', name: '승단심사 뉴스', type: 'news', target: '승단심사', schedule: 'hourly', time: '', cron: '', last: '09-28 09:00', status: 'success', analysis: 'custom', recentNew: 3,
      keywords: [{ kw: '승단심사', origin: '직접 입력', added: '2026-09-10', recent: 9 }], count: 30, sort: 'date', period: '3d', nonKorean: false },
    { id: 'S3', name: '협회 공지사항', type: 'board', target: 'example.or.kr/bbs/board.php?bo_table=notice', boardUrl: 'https://example.or.kr/bbs/board.php?bo_table=notice', schedule: 'daily', time: '09:00', cron: '', last: '09-28 09:00', status: 'zero3', analysis: 'default', recentNew: 0,
      pageParam: 'page', pages: 2, maxPosts: 50, urlPattern: '', minLen: 30, boardPeriod: 'none', skipNotice: true, nonKorean: false },
    { id: 'S4', name: '지역 협회 공지', type: 'board', target: 'example.kr/notice', boardUrl: 'https://example.kr/notice', schedule: 'manual', time: '', cron: '', last: '09-27 14:10', status: 'robots', analysis: 'default', recentNew: 0,
      pageParam: 'page', pages: 1, maxPosts: 30, urlPattern: '', minLen: 30, boardPeriod: 'none', skipNotice: true, nonKorean: false },
    { id: 'S5', name: '참고 기사 모음', type: 'url', target: 'URL 3개', schedule: 'manual', time: '', cron: '', last: '', status: 'idle', analysis: 'default', recentNew: null,
      urls: 'https://example.com/a/1\nhttps://example.com/a/2\nhttps://example.com/a/3', minLen: 30, nonKorean: false },
  ];

  const contents = [
    content({ title: '전국 태권도 선수권 대회 일정 발표', sourceId: 'S1', type: 'news', outlet: '샘플일보', published: '2026-09-28 07:40', daysAgo: 0, keyword: '태권도', relevance: 'main', isNew: true, summary: '대회 조직위원회는 전국 각지의 선수들이 참가한다고 밝혔다.' }),
    content({ title: '승단심사 제도 개편안 공청회 열려', sourceId: 'S2', type: 'news', outlet: '샘플경제', published: '2026-09-28 07:10', daysAgo: 0, keyword: '승단심사', relevance: 'partial', isNew: true, mentions: 3, density: 1.2, summary: '개편안의 주요 내용과 현장 의견이 공유됐다.' }),
    content({ title: '[공지] 하반기 심판 교육 안내', sourceId: 'S3', type: 'board', outlet: '협회 공지사항', published: '2026-09-27 18:00', daysAgo: 1, isNew: true, summary: '하반기 심판 교육 일정과 신청 방법 안내.' }),
    content({ title: '국기원, 해외 지도자 연수 확대', sourceId: 'S1', type: 'news', outlet: '샘플신문', published: '2026-09-27 15:20', daysAgo: 1, keyword: '국기원', relevance: 'main', summary: '해외 지도자 대상 연수 과정을 늘린다.' }),
    content({ title: '지역 체육 행사 종합 안내', sourceId: 'S5', type: 'url', outlet: '샘플포털', published: '2026-09-27 11:00', daysAgo: 1, summary: '여러 종목 행사 일정 중 태권도 시범이 포함됐다.' }),
    content({ title: '주말 스포츠 소식 모음', sourceId: 'S1', type: 'news', outlet: '샘플방송', published: '2026-09-26 21:00', daysAgo: 2, keyword: '태권도', relevance: 'passing', mentions: 1, density: 0.3, titleHas: false, summary: '여러 종목 결과 가운데 한 줄 언급.' }),
    content({ title: '승단심사 합격자 발표 일정 공개', sourceId: 'S2', type: 'news', outlet: '샘플일보', published: '2026-09-26 10:30', daysAgo: 2, keyword: '승단심사', relevance: 'main', summary: '합격자 발표 일정과 확인 방법.' }),
    content({ title: '청소년 태권도 교실 참가자 모집', sourceId: 'S1', type: 'news', outlet: '샘플지역', published: '2026-09-25 09:15', daysAgo: 3, keyword: '태권도', relevance: 'partial', mentions: 4, density: 1.4, summary: '지역 청소년을 대상으로 교실을 연다.' }),
    content({ title: '[공지] 품새 대회 참가 신청 연장', sourceId: 'S3', type: 'board', outlet: '협회 공지사항', published: '2026-09-24 17:40', daysAgo: 4, summary: '참가 신청 기간이 연장되었습니다.' }),
    content({ title: '생활체육 참여율 조사 결과', sourceId: 'S1', type: 'news', outlet: '샘플경제', published: '2026-09-23 08:00', daysAgo: 5, keyword: '태권도', relevance: 'passing', mentions: 1, density: 0.2, titleHas: false, summary: '종목별 참여율 표에 한 차례 등장.' }),
    content({ title: '국기원 원장 기자간담회 요지', sourceId: 'S1', type: 'news', outlet: '샘플신문', published: '2026-09-20 14:00', daysAgo: 8, keyword: '국기원', relevance: 'main', summary: '향후 운영 계획을 밝혔다.' }),
    content({ title: '겨루기 규정 개정 해설', sourceId: 'S5', type: 'url', outlet: '샘플블로그', published: '2026-09-15 12:00', daysAgo: 13, summary: '개정 규정의 주요 변경 사항 정리.' }),
  ];

  const stage = (a, b, c, d, e, f) => ({ search: a, dedup: b, period: c, fresh: d, body: e, clean: f });
  const jobs = [
    { id: 'J9', time: '09-28 09:00', sourceId: 'S2', mode: '정기', dur: 14, status: 'success', count: 3, stages: stage(30, 27, 12, 4, 4, 3) },
    { id: 'J8', time: '09-28 09:00', sourceId: 'S3', mode: '정기', dur: 6, status: 'fail', count: 0, reason: '목록 페이지에서 글을 찾지 못했습니다. 자바스크립트로 목록을 그리는 게시판이거나 선택자가 맞지 않습니다.' },
    { id: 'J7', time: '09-28 08:00', sourceId: 'S1', mode: '정기', dur: 22, status: 'success', count: 12, stages: stage(60, 51, 30, 14, 13, 12) },
    { id: 'J6', time: '09-27 14:10', sourceId: 'S4', mode: '수동', dur: 2, status: 'fail', count: 0, reason: 'robots.txt가 이 경로의 수집을 허용하지 않습니다.' },
    { id: 'J5', time: '09-27 11:00', sourceId: 'S5', mode: '수동', dur: 9, status: 'success', count: 2, stages: stage(3, 3, 3, 3, 2, 2) },
    { id: 'J4', time: '09-27 09:00', sourceId: 'S3', mode: '정기', dur: 5, status: 'fail', count: 0, reason: '목록 페이지에서 글을 찾지 못했습니다. 자바스크립트로 목록을 그리는 게시판이거나 선택자가 맞지 않습니다.' },
  ];

  const dict = (word, origin, target, added, on, extra) => ({ id: 'D' + Math.random().toString(36).slice(2, 8), word, origin, target, added, on, ...extra });
  const stopwords = [
    dict('기자', '시스템 공통', 'default', '2026-08-01', true),
    dict('사진', '시스템 공통', 'default', '2026-08-01', true),
    dict('제공', '시스템 공통', 'default', '2026-08-01', true),
    dict('뉴스', '시스템 공통', 'default', '2026-08-01', true),
    dict('무단전재', '시스템 공통', 'default', '2026-08-01', true),
    dict('관계자', '직접 추가', 'S1', '2026-09-20', true),
    dict('오늘', '키워드 분석에서 추가', 'default', '2026-09-18', true),
    dict('이번', '직접 추가', 'default', '2026-09-12', true),
    dict('밝혔다', 'CSV 가져오기', 'default', '2026-09-05', false),
    dict('따르면', 'CSV 가져오기', 'default', '2026-09-05', false),
  ];
  const compounds = [
    dict('승단심사', '직접 추가', 'S2', '2026-09-27', true, { pos: 'NNP', pending: true }),
    dict('겨루기대회', '직접 추가', 'default', '2026-09-26', true, { pos: 'NNG', pending: true }),
    dict('국기원장', 'CSV 가져오기', 'default', '2026-09-10', true, { pos: 'NNP', pending: false }),
    dict('세계태권도', '시스템 공통', 'default', '2026-08-01', true, { pos: 'NNG', pending: false }),
    dict('품새대회', '직접 추가', 'S1', '2026-09-08', true, { pos: 'NNP', pending: false }),
    dict('유소년부', 'CSV 가져오기', 'default', '2026-09-05', false, { pos: 'NNG', pending: false }),
    dict('심판교육', '직접 추가', 'default', '2026-09-02', true, { pos: 'NNP', pending: false }),
    dict('태권도원', '시스템 공통', 'default', '2026-08-01', true, { pos: 'NNP', pending: false }),
  ];

  // 분석 설정 기본값 — 기획서 FN-SET-007 / ADMIN-001-U06 기준
  const settings = {
    version: 3, preset: 'custom',
    metrics: { tokens: true, unique: false, nouns: true, sentences: true, avgLen: false, ttr: true },
    topN: 15, ttrWarn: 0.35, minBody: null /* [확인 필요] 기본값 미정 */,
    denom: 'content', posRange: 'vva', densityWarn: 8, warnMinCount: 3, warnMinNouns: 50,
    minMentions: 4, densTitle: 1.5, densNoTitle: 3.0, densMinLen: 600, requireTitle: false, passingMode: 'dim',
  };
  const adminDefaults = [
    { key: 'topN', label: '상위 키워드 개수', def: 15, min: 5, max: 30, unit: '' },
    { key: 'ttrWarn', label: '어휘 다양도 경고 기준', def: 0.35, min: 0.10, max: 0.80, unit: '', dec: 2 },
    { key: 'densityWarn', label: '밀도 경고 기준', def: 8, min: 3, max: 20, unit: '%' },
    { key: 'minMentions', label: '최소 언급 횟수', def: 4, min: 1, max: 20, unit: '회' },
    { key: 'densTitle', label: '1,000자당 밀도 (제목 포함)', def: 1.5, min: 0.3, max: 10.0, unit: '', dec: 1 },
    { key: 'densNoTitle', label: '1,000자당 밀도 (제목 미포함)', def: 3.0, min: 0.3, max: 10.0, unit: '', dec: 1 },
    { key: 'densMinLen', label: '밀도 검사 최소 길이', def: 600, min: 100, max: 3000, unit: '자' },
  ];

  const daily = Array.from({ length: 90 }, (_, i) => {
    const base = 8 + Math.round(6 * Math.sin(i / 5) + (i % 7) * 0.8);
    return { news: base + 6, board: 2 + (i % 3), url: i % 9 === 0 ? 2 : 0 };
  });

  const analysis = {
    core: [
      ['태권도', 42, 3.1, 'center'], ['대회', 31, 1.2, 'background'], ['국기원', 18, 2.6, 'center'], ['선수', 27, 0.9, 'background'],
      ['승단심사', 9, 2.8, 'center'], ['오늘', 30, 0.6, 'background'], ['지역', 19, 0.7, 'background'], ['겨루기', 11, 1.9, 'center'],
      ['품새', 10, 1.7, 'center'], ['협회', 16, 0.8, 'background'],
    ].map(([w, docs, d, kind]) => ({ w, docs, d, kind })),
    rising: [['승단심사', 9, 3.2], ['겨루기', 11, 2.6], ['유소년', 6, 2.1], ['심판', 7, 1.9], ['품새', 10, 1.7], ['연수', 5, 1.5]].map(([w, n, x]) => ({ w, n, x })),
    hit: [
      { kw: '태권도', n: 42, main: 55, partial: 25, passing: 20 },
      { kw: '승단심사', n: 9, main: 70, partial: 20, passing: 10 },
      { kw: '국기원', n: 18, main: 15, partial: 20, passing: 65 },
    ],
    related: {
      '태권도': [['품새', 14], ['겨루기', 12], ['대한태권도협회', 9], ['세계선수권', 8], ['유소년', 6], ['시범단', 5], ['심판', 5], ['국가대표', 4]],
      '국기원': [['승단심사', 7], ['연수', 6], ['원장', 5], ['해외지도자', 4], ['단증', 3]],
      '승단심사': [['합격자', 5], ['단증', 4], ['품새', 3], ['국기원', 3]],
    },
  };

  const admin = {
    users: 128, newThisMonth: 14, active7: 71, apiToday: 4820, apiLimit: 25000, queueWait: 3, avgWait: 12,
    usage: [
      ['샘플협회 / 김멤버', '베이직', 5, 4, 312, '09-28'], ['샘플미디어 / 이멤버', '프로', 12, 20, 2140, '09-28'],
      ['샘플연구소 / 박멤버', '베이직', 2, 3, 88, '09-25'], ['개인 / 최멤버', '무료', 1, 1, 12, '09-19'],
    ].map(([user, plan, src, kw, n30, last]) => ({ user, plan, src, kw, n30, last })), // 요금제 명칭은 MOCK [정책 필요]
    queue: { waiting: 3, running: 2, avgWait: 12, workers: 4, fail1h: 1 },
    core: [['태권도', 380, 2.4], ['대회', 290, 1.1], ['선수', 244, 0.9], ['경기', 198, 1.3], ['국가대표', 120, 1.8], ['협회', 111, 0.7]].map(([w, docs, d]) => ({ w, docs, d })),
    keywords: [['태권도', 6], ['국기원', 3], ['승단심사', 1], ['품새', 1]].map(([kw, n]) => ({ kw, n })),
  };

  const dashboard = { today: 15, delta: +4, successRate: 83, failCount: 2, nextTime: '10:00', nextSource: '승단심사 뉴스' };

  return { sources, contents, jobs, stopwords, compounds, settings, savedSettings: JSON.parse(JSON.stringify(settings)), adminDefaults, daily, analysis, admin, dashboard };
}

const mockSearchResults = (kw) => [1, 2, 3, 4, 5].map((i) => ({ title: `${kw} 관련 샘플 기사 제목 ${i}`, outlet: ['샘플일보', '샘플신문', '샘플경제', '샘플방송', '샘플지역'][i - 1], date: `09-${29 - i}`, kw }));

const mockDetect = (url) => ({
  robots: true, httpOk: true,
  candidates: [
    { pattern: url.replace(/^https?:\/\//, '').split('?')[0] + '?bo_table=notice&wr_id={n}', links: 15 },
    { pattern: url.replace(/^https?:\/\//, '').split('/')[0] + '/bbs/board.php?bo_table=free&wr_id={n}', links: 6 },
    { pattern: url.replace(/^https?:\/\//, '').split('/')[0] + '/page/{n}', links: 3 },
  ],
});

const mockBoardPosts = (candidateIndex) => [1, 2, 3, 4].map((i) => ({
  title: candidateIndex === 0 ? `공지 게시글 샘플 제목 ${i}` : `다른 묶음 게시글 ${i}`,
  date: `09-${28 - i}`, url: `…wr_id=${120 - i}`,
}));

// SERVICE LAYER (UI → Service → API)
// 실제 내부 API Endpoint / Request·Response Schema는 기획서에서 확정되지 않았다.
// 아래 함수는 모두 Mock 이며 지연(latency)만 흉내 낸다. 실제 연동 시 이 파일만 교체한다. [API 확인 필요]


const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const api = {
  // 초기 데이터 조회 — [API 확인 필요]
  async fetchInitial() { await wait(400); return createMockStore(); },

  // FUNC: FN-AUTH-001 — 인증 결과는 Tweak(loginResult)로 시뮬레이션. 세션·유지 정책 [정책 필요]
  async login({ email, password, keep }, forceFail) {
    await wait(700);
    if (forceFail) return { ok: false };
    return { ok: true, user: { name: email.split('@')[0] || '[사용자 이름]' } };
  },

  // FUNC: FN-SRC-003 — 네이버 뉴스 검색 5건 미리보기 (실제 호출은 서버 경유) [API 확인 필요]
  async searchTest(keyword) { await wait(900); return mockSearchResults(keyword); },

  // FUNC: FN-SRC-004 — robots.txt 확인 → 목록 수집 → 후보 묶음 [API 확인 필요]
  async detectBoard(url) { await wait(1100); return mockDetect(url); },
  async boardPreview(candidateIndex) { await wait(300); return mockBoardPosts(candidateIndex); },

  // FUNC: FN-SRC-007 — 주소별 확인. 접속 실패 상태는 [추정]
  async checkUrls(urls, minLen) {
    await wait(1000);
    return urls.map((u, i) => {
      if (/robots|blocked/.test(u) || i === 3) return { url: u, result: 'robots', text: '수집하지 않음' };
      const len = i === 2 ? Math.max(0, minLen - 8) : 1200 + i * 310;
      if (len < minLen) return { url: u, result: 'short', text: `${len}자 · 최소 길이 미만` };
      return { url: u, result: 'ok', text: `${len.toLocaleString()}자` };
    });
  },

  // FUNC: FN-SRC-010 — 소스 저장 [API 확인 필요]
  async saveSource(source) { await wait(700); return { ...source, id: source.id || 'S' + Date.now().toString(36) }; },

  // FUNC: FN-SET-007 [API 확인 필요]
  async saveSettings(s) { await wait(700); return { ...s, version: s.version + 1 }; },

  // FUNC: FN-CNT-007 / FN-DIC-006 — 재분석 작업 등록 [API 확인 필요]
  async reanalyze() { await wait(1200); return { ok: true }; },

  // FUNC: FN-ADM-006 / FN-ADM-007 [API 확인 필요]
  async saveAdminDefaults(rows) { await wait(600); return rows; },
};

window.CCMock = { createMockStore, mockSearchResults, mockDetect, mockBoardPosts };
window.CCApi = api;
})();
