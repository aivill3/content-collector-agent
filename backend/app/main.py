from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.scrape import router as scrape_router

app = FastAPI(
    title="Smart URL Collector API",
    description="URL 기반 본문/게시판 자동 감지 수집 시스템",
    version="1.0.0",
)

# CORS 설정 (프론트엔드 연동 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """서버 상태 확인용 헬스체크 엔드포인트"""
    return {"status": "ok"}


# API 라우터 등록
app.include_router(scrape_router)