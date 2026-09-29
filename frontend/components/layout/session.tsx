"use client";

import { createContext, useContext } from "react";
import type { User } from "@/lib/types";

export const SessionContext = createContext<User | null>(null);

/** 로그인한 사용자. (app) 레이아웃 안에서만 값이 있다. */
export function useSession(): User {
  const user = useContext(SessionContext);
  if (!user) throw new Error("useSession 은 (app) 레이아웃 안에서만 쓸 수 있습니다");
  return user;
}
