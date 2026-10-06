import type { NextConfig } from "next";

// 백엔드(FastAPI) 주소. 브라우저는 같은 주소의 /api/* 를 부르고, Next 가 이 서버로 넘긴다 (CORS 불필요).
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  experimental: {
    // URL 확인은 주소마다 사이트에 접속해 본문을 받는다 (재시도 포함). 기본 30초로는 모자랄 수 있다.
    proxyTimeout: 120_000,
  },
};

export default nextConfig;
