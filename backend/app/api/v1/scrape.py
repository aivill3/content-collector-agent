from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.scrape import (
    ScrapeRequest,
    ScrapeResponse,
    ScrapeResultResponse,
    ArticleResponse,
)
from app.services.url_service import UrlCollectorService

router = APIRouter(prefix="/v1/scrape", tags=["Scrape"])


def get_url_service() -> UrlCollectorService:
    """UrlCollectorService 의존성 주입 함수"""
    return UrlCollectorService()


@router.post(
    "",
    response_model=ScrapeResponse,
    status_code=status.HTTP_200_OK,
    summary="URL 본문/게시판 자동 감지 수집 API",
    description="입력된 URL의 형태(단일글/게시판)를 자동 감지하고, 3단계 Fallback 엔진을 거쳐 정제된 본문을 반환합니다."
)
async def scrape_urls(
    request: ScrapeRequest,
    service: UrlCollectorService = Depends(get_url_service)
):
    try:
        results = await service.collect_with_details(
            target=request.urls,
            max_items_per_board=request.max_items_per_board
        )

        formatted_results = []
        total_articles = 0

        for res in results:
            articles_resp = [
                ArticleResponse(
                    url=art.url,
                    title=art.title,
                    body=art.body,
                    body_clean=art.body_clean,
                    published=art.published,
                    board_url=art.board_url
                )
                for art in res.articles
            ]
            total_articles += len(articles_resp)

            formatted_results.append(
                ScrapeResultResponse(
                    target_url=res.target_url,
                    page_type=res.page_type,
                    tier_used=res.tier_used,
                    articles=articles_resp,
                    error_message=res.error_message
                )
            )

        return ScrapeResponse(
            total_requested=len(request.urls),
            total_articles=total_articles,
            results=formatted_results
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"수집 처리 중 내부 오류가 발생했습니다: {str(e)}"
        )