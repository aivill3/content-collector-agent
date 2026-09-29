"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";

/**
 * 화면 진입 시 lib/api 를 불러 로딩·오류 상태와 함께 돌려준다.
 *
 * key 가 바뀌면(필터 변경 등) 이전 데이터를 보여 둔 채 다시 불러오고, 그동안 stale 이 true 다.
 *
 * reload("full")    스켈레톤부터 다시 (오류 화면의 '다시 시도')
 * reload("refresh") 데이터는 그대로 두고 refreshing 만 켠다 (새로고침 버튼)
 * reload("quiet")   표시 없이 갱신 (진행 중인 작업 폴링, 변경 후 반영)
 */
export function useApiData<T>(fetcher: () => Promise<T>, key = "") {
  const [state, setState] = useState<{
    data?: T;
    error?: unknown;
    loading: boolean;
    refreshing: boolean;
    loadedKey?: string;
  }>({ loading: true, refreshing: false });
  const [nonce, setNonce] = useState(0);
  const load = useEffectEvent(fetcher);

  useEffect(() => {
    let alive = true;
    load().then(
      (data) => alive && setState({ data, loading: false, refreshing: false, loadedKey: key }),
      (error) => alive && setState({ error, loading: false, refreshing: false, loadedKey: key }),
    );
    return () => {
      alive = false;
    };
  }, [nonce, key]);

  const reload = useCallback((mode: "full" | "refresh" | "quiet" = "full") => {
    if (mode === "full") setState({ loading: true, refreshing: false });
    if (mode === "refresh") setState((s) => ({ ...s, refreshing: true }));
    setNonce((n) => n + 1);
  }, []);

  const { loadedKey, ...rest } = state;
  return { ...rest, stale: !state.loading && loadedKey !== key, reload };
}

/** active 인 동안 interval 마다 onTick 을 부른다 (대기·실행 중인 수집 작업 폴링) */
export function usePollWhile(active: boolean, onTick: () => void, interval = 1000) {
  const tick = useEffectEvent(onTick);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => tick(), interval);
    return () => clearInterval(t);
  }, [active, interval]);
}
