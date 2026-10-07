"""소스 점검 — 소스 추가·편집 화면의 확인 버튼 (SOURCE-002~005).

라우트는 services/ 의 함수만 부르고, 결과를 스키마로 옮겨 담는다.
네트워크를 기다리는 동기 함수라 def 로 둔다 (FastAPI 가 스레드풀에서 돌린다).
"""
from fastapi import APIRouter, HTTPException

from app.collectors.news import NaverCollectError
from app.schemas.source_check import (
    BoardDetectRequest,
    BoardDetectResult,
    SearchPreview,
    SearchTestRequest,
    UrlCheckRequest,
    UrlCheckResult,
)
from app.services import source_check_service as svc

router = APIRouter(prefix="/source-checks", tags=["소스 점검"])


@router.post("/search", response_model=list[SearchPreview])
def search_test(req: SearchTestRequest):
    try:
        articles = svc.search_preview(req.keyword)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except NaverCollectError as e:
        # 키가 없거나 네이버 호출 실패 — 사용자가 고칠 수 있게 사유를 그대로 전한다
        raise HTTPException(502, str(e))
    return [SearchPreview.of(a) for a in articles]


@router.post("/board", response_model=BoardDetectResult)
def detect_board(req: BoardDetectRequest):
    if not req.url.strip().startswith(("http://", "https://")):
        raise HTTPException(422, "http:// 또는 https:// 로 시작하는 주소를 입력하세요")
    return BoardDetectResult.of(svc.detect_board(req.url))


@router.post("/urls", response_model=list[UrlCheckResult])
def check_urls(req: UrlCheckRequest):
    bad = [u for u in req.urls if u.strip() and not u.strip().startswith(("http://", "https://"))]
    if bad:
        raise HTTPException(422, f"http:// 또는 https:// 로 시작하지 않는 주소: {', '.join(bad[:3])}")
    try:
        checks = svc.check_urls(req.urls, min_len=req.min_len, korean_only=req.korean_only)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return [UrlCheckResult.of(u) for u in checks]
