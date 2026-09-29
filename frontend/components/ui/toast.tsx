"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

// 공통 Toast — 문구 정책 미정 [문구 확인 필요]

const ToastContext = createContext<(message: string) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [message, setMessage] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const show = useCallback((msg: string) => {
    clearTimeout(timer.current);
    setMessage(msg);
    timer.current = setTimeout(() => setMessage(null), 2800);
  }, []);

  useEffect(() => () => clearTimeout(timer.current), []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      {message && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-8 left-1/2 z-60 max-w-[min(560px,90vw)] -translate-x-1/2 animate-toast-in rounded-[10px] bg-ink px-[18px] py-3 text-sm text-white shadow-[0_8px_24px_rgba(0,0,0,.18)]"
        >
          {message}
        </div>
      )}
    </ToastContext.Provider>
  );
}
