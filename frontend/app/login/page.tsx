import type { Metadata } from "next";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "로그인 · 콘텐츠 수집 Agent" };

// MEMBER-001 로그인
export default function LoginPage() {
  return (
    <main
      data-screen-label="MEMBER-001 로그인"
      data-screen-id="MEMBER-001"
      className="grid min-h-screen grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,620px)_minmax(0,1fr)]"
    >
      <section
        data-ui-id="MEMBER-001-U01"
        className="flex flex-col justify-between gap-5 border-b border-line bg-surface px-5 py-7 md:p-10 lg:gap-10 lg:border-r lg:border-b-0 lg:p-16"
      >
        <div className="text-[17px] font-bold">콘텐츠 수집 Agent</div>
        <div className="flex flex-col gap-3.5">
          <h2 className="m-0 text-2xl leading-[1.45] font-bold text-pretty md:text-[32px]">
            키워드 뉴스와 게시판 글을
            <br />
            한곳에 모아 봅니다
          </h2>
          <p className="m-0 text-muted">[서비스 소개 문구]</p>
          {/* [확인 필요] 서비스 화면 이미지 미정 · [추정] 모바일에서는 이미지 자리 숨김 */}
          <div className="mt-3.5 hidden h-[262px] items-center justify-center rounded-control border border-dashed border-field bg-subtle text-[13px] text-muted md:flex">
            서비스 화면 이미지 자리
          </div>
        </div>
        {/* [확인 필요] 이용약관·개인정보처리방침 링크 대상 */}
        <div className="text-[13px] text-muted">[회사명] · 이용약관 · 개인정보처리방침</div>
      </section>
      <section className="flex items-center justify-center px-6 py-12">
        <LoginForm />
      </section>
    </main>
  );
}
