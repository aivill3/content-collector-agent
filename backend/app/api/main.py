"""FastAPI 앱. backend/ 에서 실행한다.

    uvicorn app.api.main:app --reload --port 8000

모든 경로는 /api 아래에 둔다. 프론트엔드(Next.js)는 /api/* 를 이 서버로 넘겨(rewrites)
같은 주소처럼 부르므로 운영에서는 CORS 가 필요 없다. 다만 개발 중 브라우저가 직접 부르는 경우를 위해
http://localhost:3000 만 허용해 둔다.

소스 점검(저장 없음)·콘텐츠 조회·소스 선택지·URL 수집(POST /api/v1/scrape, 저장 없음)이 있다.
DB 를 쓰는 라우터는 api/deps.py 의 get_current_workspace 를 거친다.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import contents, source_checks, sources
from app.api.v1.scrape import router as scrape_router
from app.core import logger

logger.setup(to_file=True, prefix="api")

app = FastAPI(title="content-collector-agent API", version="0.1.0")

# Next.js 개발 서버(http://localhost:3000)에서 직접 부르는 경우만 허용한다
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(source_checks.router, prefix="/api")
app.include_router(contents.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(scrape_router, prefix="/api")  # POST /api/v1/scrape


@app.get("/api/health", tags=["상태"])
def health() -> dict:
    return {"ok": True}
