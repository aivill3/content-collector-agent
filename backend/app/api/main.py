"""FastAPI 앱. backend/ 에서 실행한다.

    uvicorn app.api.main:app --reload --port 8000

모든 경로는 /api 아래에 둔다. 프론트엔드(Next.js)는 /api/* 를 이 서버로 넘겨(rewrites)
같은 주소처럼 부르므로 CORS 설정이 필요 없다.

소스 점검(저장 없음)·콘텐츠 조회·소스 선택지가 있다. DB 를 쓰는 라우터는 api/deps.py 의 get_current_workspace 를 거친다.
"""
from fastapi import FastAPI

from app.api.routes import contents, source_checks, sources
from app.core import logger

logger.setup(to_file=True, prefix="api")

app = FastAPI(title="content-collector-agent API", version="0.1.0")
app.include_router(source_checks.router, prefix="/api")
app.include_router(contents.router, prefix="/api")
app.include_router(sources.router, prefix="/api")


@app.get("/api/health", tags=["상태"])
def health() -> dict:
    return {"ok": True}
