// SERVICE LAYER (UI → Service → API)
// 실제 내부 API Endpoint / Request·Response Schema는 기획서에서 확정되지 않았다.
// 아래 함수는 모두 Mock 이며 지연(latency)만 흉내 낸다. 실제 연동 시 이 파일만 교체한다. [API 확인 필요]
import { createMockStore, mockSearchResults, mockDetect, mockBoardPosts } from '../mock/data.js';

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

export const api = {
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
