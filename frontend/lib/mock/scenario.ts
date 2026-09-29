// 시안의 "Tweaks" 패널(역할·데이터 상태·로그인 결과)을 URL 파라미터로 대신한다. 개발 확인용.
//
//   ?data=normal|empty|error   데이터 상태 (정상 / 빈 상태 / 오류)
//   ?role=member|admin         역할
//   ?login=success|fail        로그인 결과
//
// 한 번 지정하면 탭을 닫을 때까지(sessionStorage) 유지된다. 기본값으로 되돌리려면 ?data=normal 처럼 다시 지정한다.

import type { Role } from "@/lib/types";

export interface Scenario {
  data: "normal" | "empty" | "error";
  role: Role;
  login: "success" | "fail";
}

const DEFAULT: Scenario = { data: "normal", role: "member", login: "success" };
const KEY = "cc.mock.scenario";

const OPTIONS: { [K in keyof Scenario]: readonly Scenario[K][] } = {
  data: ["normal", "empty", "error"],
  role: ["member", "admin"],
  login: ["success", "fail"],
};

export function getScenario(): Scenario {
  if (typeof window === "undefined") return DEFAULT;
  let saved: Partial<Scenario> = {};
  try {
    saved = JSON.parse(sessionStorage.getItem(KEY) ?? "{}");
  } catch {
    // 저장소 접근이 막힌 환경이면 기본값으로 동작한다
  }
  const next: Scenario = { ...DEFAULT, ...saved };
  const q = new URLSearchParams(window.location.search);
  let changed = false;
  for (const key of Object.keys(OPTIONS) as (keyof Scenario)[]) {
    const v = q.get(key);
    if (v && (OPTIONS[key] as readonly string[]).includes(v)) {
      (next as unknown as Record<string, string>)[key] = v;
      changed = true;
    }
  }
  if (changed) {
    try {
      sessionStorage.setItem(KEY, JSON.stringify(next));
    } catch {}
  }
  return next;
}
