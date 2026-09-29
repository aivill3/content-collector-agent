"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { SessionContext } from "@/components/layout/session";
import { api } from "@/lib/api";
import { cx } from "@/lib/cx";
import type { User } from "@/lib/types";

// COMMON-001 공통 레이아웃
// 데스크톱(≥1024px)은 고정 사이드바, 그보다 좁으면 상단 바 + 서랍형 사이드바 [추정]

const NAV = [
  { href: "/", label: "대시보드" },
  { href: "/contents", label: "콘텐츠" },
  { href: "/sources", label: "수집 소스" },
  { href: "/jobs", label: "수집 작업" },
  { href: "/analysis", label: "키워드 분석" },
  { href: "/settings", label: "분석 설정" },
  { href: "/dictionary", label: "사전" },
] as const;

const ROLE_LABEL = { member: "멤버", admin: "관리자" } as const;

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
}

function NavLink({ href, label, active, onNavigate }: { href: string; label: string; active: boolean; onNavigate: () => void }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
      className={cx(
        "block rounded-control px-3 py-2.5 text-sm hover:no-underline",
        active ? "bg-nav-active font-bold text-primary hover:text-primary" : "font-medium text-ink hover:bg-canvas hover:text-ink",
      )}
    >
      {label}
    </Link>
  );
}

function GearLink({ className, uiId }: { className?: string; uiId: string }) {
  return (
    <Link
      href="/settings"
      data-ui-id={uiId}
      aria-label="분석 설정"
      title="분석 설정"
      className={cx("flex flex-none items-center justify-center rounded-control text-ink-2 hover:bg-canvas hover:text-ink-2 hover:no-underline", className)}
    >
      ⚙
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);

  // 로그인 확인 — 실제 인증·세션 만료 처리는 [정책 필요]
  useEffect(() => {
    api.getSession().then((u) => {
      if (u) setUser(u);
      else router.replace("/login");
    });
  }, [router]);

  const openDrawer = () => {
    setDrawerOpen(true);
    requestAnimationFrame(() => navRef.current?.querySelector("a")?.focus());
  };
  const closeDrawer = () => {
    setDrawerOpen(false);
    menuButton.current?.focus();
  };

  // ESC 로 서랍 닫기 [추정]
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setDrawerOpen(false);
      menuButton.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  if (!user) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-muted">불러오는 중…</div>;
  }

  const onNavigate = () => setDrawerOpen(false);

  return (
    <SessionContext.Provider value={user}>
      <div data-screen-id="COMMON-001" className="min-h-screen lg:grid lg:grid-cols-[232px_minmax(0,1fr)]">
        {/* 좁은 화면 상단 바 */}
        <div className="sticky top-0 z-30 flex h-14 items-center gap-1.5 border-b border-line bg-surface px-2 lg:hidden">
          <button
            ref={menuButton}
            type="button"
            data-ui-id="COMMON-001-U06"
            aria-label="메뉴 열기"
            aria-controls="cc-nav"
            aria-expanded={drawerOpen}
            onClick={openDrawer}
            className="flex size-11 flex-col items-center justify-center gap-1 rounded-control border-none bg-transparent hover:bg-canvas"
          >
            <span className="h-0.5 w-5 rounded-[1px] bg-ink" />
            <span className="h-0.5 w-5 rounded-[1px] bg-ink" />
            <span className="h-0.5 w-5 rounded-[1px] bg-ink" />
          </button>
          <Link href="/" className="flex-1 text-base font-bold text-ink hover:text-ink hover:no-underline">
            콘텐츠 수집 Agent
          </Link>
          <GearLink uiId="COMMON-001-U07" className="size-11 text-xl" />
        </div>

        {drawerOpen && <div aria-hidden="true" onClick={closeDrawer} className="fixed inset-0 z-40 bg-[rgba(20,20,18,.38)] lg:hidden" />}

        <aside
          id="cc-nav"
          aria-label="사이드바"
          className={cx(
            "flex flex-col overflow-y-auto bg-surface px-4 py-6",
            // 서랍
            "fixed inset-y-0 left-0 z-50 w-[280px] max-w-[85vw] transition-[transform,visibility] duration-200 ease-out",
            drawerOpen ? "visible translate-x-0 shadow-[0_12px_40px_rgba(0,0,0,.18)]" : "invisible -translate-x-full",
            // 데스크톱 고정 사이드바
            "lg:visible lg:sticky lg:top-0 lg:bottom-auto lg:z-auto lg:h-screen lg:w-auto lg:max-w-none lg:translate-x-0 lg:border-r lg:border-line lg:shadow-none",
          )}
        >
          <button
            type="button"
            aria-label="메뉴 닫기"
            onClick={closeDrawer}
            className="absolute top-3.5 right-2.5 size-11 rounded-control border-none bg-transparent text-[22px] leading-none text-ink-2 hover:bg-canvas lg:hidden"
          >
            ×
          </button>
          <Link
            href="/"
            data-ui-id="COMMON-001-U01"
            onClick={onNavigate}
            className="px-3 pt-1 pb-7 text-base font-bold text-ink hover:text-ink hover:no-underline"
          >
            콘텐츠 수집 Agent
          </Link>
          <nav ref={navRef} aria-label="주 메뉴" data-ui-id="COMMON-001-U02" className="flex flex-col gap-1">
            {NAV.map((n) => (
              <NavLink key={n.href} {...n} active={isActive(pathname, n.href)} onNavigate={onNavigate} />
            ))}
          </nav>
          {/* [확인 필요] 관리자 메뉴의 멤버 노출 여부 — 와이어프레임대로 양쪽 모두 표시 */}
          <div data-ui-id="COMMON-001-U03" className="mt-[18px] flex flex-col gap-1">
            <div className="px-3 pb-1.5 text-xs text-muted">관리자 전용</div>
            <NavLink href="/admin" label="관리자" active={isActive(pathname, "/admin")} onNavigate={onNavigate} />
          </div>
          <div className="flex-1" />
          {/* [확인 필요] 로그아웃·계정 메뉴 없음 (Gap) */}
          <div data-ui-id="COMMON-001-U04" className="flex items-center gap-2.5 border-t border-line px-3 pt-4">
            <div aria-hidden="true" className="size-8 flex-none rounded-full bg-subtle" />
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="truncate text-[13px] font-bold">{user.name}</span>
              <span className="text-xs text-muted">{ROLE_LABEL[user.role]}</span>
            </div>
            <GearLink uiId="COMMON-001-U08" className="ml-auto size-9 text-lg" />
          </div>
        </aside>

        <main className="min-w-0 px-4 pt-5 pb-12 md:px-6 md:pt-7 md:pb-14 lg:px-10 lg:pt-9 lg:pb-16">{children}</main>
      </div>
    </SessionContext.Provider>
  );
}
