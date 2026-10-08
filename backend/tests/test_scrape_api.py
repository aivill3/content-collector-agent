import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.v1.scrape import get_url_service
from app.domain.url_collector import PageType, FetchTier, ScrapeResult
from app.domain.content import Article

client = TestClient(app)


@pytest.fixture
def mock_article_result():
    """단일 기사 수집 성공 결과 Mock 데이터"""
    return [
        ScrapeResult(
            target_url="https://example.com/news/123",
            page_type=PageType.ARTICLE,
            tier_used=FetchTier.HTTPX,
            articles=[
                Article(
                    url="https://example.com/news/123",
                    title="테스트 기사 제목",
                    body="본문 원본 데이터입니다.",
                    body_clean="정제된 본문 데이터입니다.",
                    published="2026-10-07T09:00:00",
                    board_url="",
                    source="website",
                )
            ],
            error_message=None,
        )
    ]


@pytest.fixture
def mock_board_result():
    """게시판 목록 수집 성공 결과 Mock 데이터"""
    return [
        ScrapeResult(
            target_url="https://example.com/board/list",
            page_type=PageType.BOARD,
            tier_used=FetchTier.PLAYWRIGHT,
            articles=[
                Article(
                    url="https://example.com/board/1",
                    title="게시글 1",
                    body="게시글 1 원본",
                    body_clean="게시글 1 정제본",
                    published="2026-10-07T08:00:00",
                    board_url="https://example.com/board/list",
                    source="website",
                ),
                Article(
                    url="https://example.com/board/2",
                    title="게시글 2",
                    body="게시글 2 원본",
                    body_clean="게시글 2 정제본",
                    published="2026-10-07T08:30:00",
                    board_url="https://example.com/board/list",
                    source="website",
                ),
            ],
            error_message=None,
        )
    ]


def test_scrape_single_article_success(mock_article_result):
    """단일 URL 수집 정상 처리 (HTTP 200 OK) 검증"""
    mock_service = AsyncMock()
    mock_service.collect_with_details.return_value = mock_article_result

    app.dependency_overrides[get_url_service] = lambda: mock_service

    try:
        response = client.post(
            "/api/v1/scrape",
            json={"urls": ["https://example.com/news/123"]}
        )

        assert response.status_code == 200
        data = response.json()

        # JSON 은 camelCase, Enum 값은 소문자
        assert data["totalRequested"] == 1
        assert data["totalArticles"] == 1
        assert len(data["results"]) == 1
        assert "total_requested" not in data

        result = data["results"][0]
        assert result["targetUrl"] == "https://example.com/news/123"
        assert result["pageType"] == PageType.ARTICLE.value == "article"
        assert result["tierUsed"] == FetchTier.HTTPX.value == "httpx"
        assert result["errorMessage"] is None
        assert len(result["articles"]) == 1
        assert result["articles"][0]["title"] == "테스트 기사 제목"
        assert result["articles"][0]["bodyClean"] == "정제된 본문 데이터입니다."
        assert result["articles"][0]["published"] == "2026-10-07T09:00:00"

    finally:
        app.dependency_overrides.clear()


def test_scrape_board_success(mock_board_result):
    """게시판 URL 감지 및 하위 글 수집 정상 처리 검증"""
    mock_service = AsyncMock()
    mock_service.collect_with_details.return_value = mock_board_result

    app.dependency_overrides[get_url_service] = lambda: mock_service

    try:
        response = client.post(
            "/api/v1/scrape",
            json={
                "urls": ["https://example.com/board/list"],
                "maxItemsPerBoard": 5
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["totalRequested"] == 1
        assert data["totalArticles"] == 2

        # 요청의 camelCase 필드가 서비스에 그대로 전달된다
        mock_service.collect_with_details.assert_awaited_once_with(
            target=["https://example.com/board/list"],
            max_items_per_board=5,
        )

        result = data["results"][0]
        assert result["pageType"] == PageType.BOARD.value == "board"
        assert result["tierUsed"] == FetchTier.PLAYWRIGHT.value == "playwright"
        assert len(result["articles"]) == 2
        assert result["articles"][0]["boardUrl"] == "https://example.com/board/list"

    finally:
        app.dependency_overrides.clear()


def test_scrape_validation_error_empty_urls():
    """urls가 빈 배열일 때 유효성 검증 실패 (HTTP 422)"""
    response = client.post(
        "/api/v1/scrape",
        json={"urls": []}
    )

    assert response.status_code == 422


def test_scrape_internal_server_error():
    """서비스 계층 예외 발생 시 internal server error (HTTP 500) 응답 검증"""
    mock_service = AsyncMock()
    mock_service.collect_with_details.side_effect = Exception("수집 중 알 수 없는 에러")

    app.dependency_overrides[get_url_service] = lambda: mock_service

    try:
        response = client.post(
            "/api/v1/scrape",
            json={"urls": ["https://example.com/error"]}
        )

        assert response.status_code == 500
        assert "수집 처리 중 내부 오류가 발생했습니다" in response.json()["detail"]

    finally:
        app.dependency_overrides.clear()