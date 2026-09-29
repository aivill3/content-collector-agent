"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";

function LinkButton({ uiId, children, onClick }: { uiId: string; children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      data-ui-id={uiId}
      onClick={onClick}
      className="border-none bg-transparent p-0 text-sm font-semibold text-primary hover:text-primary-strong hover:underline"
    >
      {children}
    </button>
  );
}

export function LoginForm() {
  const router = useRouter();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [keep, setKeep] = useState(false);
  const [fieldErr, setFieldErr] = useState<{ email?: string; password?: string }>({});
  const [loginError, setLoginError] = useState(false);
  const [loggingIn, setLoggingIn] = useState(false);

  // FUNC: FN-AUTH-001 로그인
  // [Validation Rule 확인 필요] 기획서는 필수만 확정, 이메일 형식 검증은 [추정] → 필수 검증만 구현
  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err: typeof fieldErr = {};
    if (!email.trim()) err.email = "필수 입력 항목입니다";
    if (!password) err.password = "필수 입력 항목입니다";
    setFieldErr(err);
    setLoginError(false);
    if (err.email || err.password) return;

    setLoggingIn(true);
    const res = await api.login({ email, password, keep });
    if (!res.ok) {
      setLoggingIn(false);
      setLoginError(true);
      setPassword(""); // 비밀번호 처리 [정책 필요]
      return;
    }
    router.replace("/");
  };

  // 연결 화면이 정의되지 않은 링크
  const tbd = (what: string) => () => toast(`[확인 필요] ${what} — 연결 화면이 정의되지 않았습니다`);

  return (
    <form onSubmit={onSubmit} noValidate className="flex w-full max-w-[400px] flex-col">
      <h1 data-ui-id="MEMBER-001-U02" className="m-0 mb-[26px] text-[26px] font-bold">
        로그인
      </h1>
      {loginError && (
        <div data-ui-id="MEMBER-001-U03" role="alert" className="mb-[22px] rounded-control bg-warn-soft px-3.5 py-3 text-[13px] text-warn">
          이메일 또는 비밀번호가 올바르지 않습니다
        </div>
      )}

      <label htmlFor="login-email" className="mb-2 text-[13px] font-semibold">
        이메일
      </label>
      <Input
        id="login-email"
        data-ui-id="MEMBER-001-U04"
        type="email"
        autoComplete="email"
        placeholder="name@company.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        aria-invalid={!!fieldErr.email}
        aria-describedby="login-email-err"
        className="h-11"
      />
      <div id="login-email-err" className="min-h-[22px] pt-1 text-xs text-warn">
        {fieldErr.email}
      </div>

      <label htmlFor="login-pw" className="mt-1.5 mb-2 text-[13px] font-semibold">
        비밀번호
      </label>
      <Input
        id="login-pw"
        data-ui-id="MEMBER-001-U05"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        aria-invalid={!!fieldErr.password}
        aria-describedby="login-pw-err"
        className="h-11"
      />
      <div id="login-pw-err" className="min-h-[22px] pt-1 text-xs text-warn">
        {fieldErr.password}
      </div>

      <div className="mt-2 mb-[18px] flex items-center justify-between">
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input
            data-ui-id="MEMBER-001-U06"
            type="checkbox"
            checked={keep}
            onChange={(e) => setKeep(e.target.checked)}
            className="m-0 size-[18px] accent-primary"
          />
          로그인 유지
        </label>
        <LinkButton uiId="MEMBER-001-U07" onClick={tbd("비밀번호 찾기")}>
          비밀번호 찾기
        </LinkButton>
      </div>

      <Button
        type="submit"
        variant="primary"
        size="lg"
        data-ui-id="MEMBER-001-U08"
        data-func-id="FN-AUTH-001"
        disabled={loggingIn}
      >
        {loggingIn ? "로그인 중…" : "로그인"}
      </Button>

      <div className="mt-5 mb-[22px] h-px bg-line" />
      <div className="text-center text-sm text-muted">
        계정이 없으신가요?{" "}
        <LinkButton uiId="MEMBER-001-U09" onClick={tbd("회원가입 (가입 방식 [정책 필요])")}>
          회원가입
        </LinkButton>{" "}
        ·{" "}
        <LinkButton uiId="MEMBER-001-U10" onClick={tbd("도입 문의 채널")}>
          도입 문의
        </LinkButton>
      </div>
    </form>
  );
}
