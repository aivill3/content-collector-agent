"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

// 공통 확인 Modal — [모달 닫기 정책 확인 필요] ESC·바깥 클릭 닫기는 추정 구현

export interface ConfirmOptions {
  title: string;
  body?: string;
  okLabel?: string;
  onOk: () => void;
}

const ConfirmContext = createContext<(options: ConfirmOptions) => void>(() => {});

export function useConfirm() {
  return useContext(ConfirmContext);
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [modal, setModal] = useState<ConfirmOptions | null>(null);
  const okRef = useRef<HTMLButtonElement>(null);
  const confirm = useCallback((options: ConfirmOptions) => setModal(options), []);

  useEffect(() => {
    if (!modal) return;
    okRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setModal(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modal]);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {modal && (
        <div
          onClick={() => setModal(null)}
          className="fixed inset-0 z-70 flex items-center justify-center bg-[rgba(20,20,18,.38)] p-6"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="cc-modal-title"
            onClick={(e) => e.stopPropagation()}
            className="flex w-full max-w-[420px] flex-col gap-3 rounded-card bg-surface p-6 shadow-[0_16px_48px_rgba(0,0,0,.2)]"
          >
            <h2 id="cc-modal-title" className="m-0 text-[17px] font-bold">
              {modal.title}
            </h2>
            {modal.body && <p className="m-0 text-sm leading-relaxed text-ink-2">{modal.body}</p>}
            <div className="mt-2 flex justify-end gap-2">
              <Button className="h-[38px]" onClick={() => setModal(null)}>
                취소
              </Button>
              <Button
                ref={okRef}
                variant="primary"
                className="h-[38px] font-semibold"
                onClick={() => {
                  setModal(null);
                  modal.onOk();
                }}
              >
                {modal.okLabel ?? "확인"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}
