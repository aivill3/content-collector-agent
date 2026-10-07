"""API 라우트 테스트 — 네트워크 호출은 모두 가짜로 바꾼다. python -m pytest tests"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.collectors.news import SearchResult
from app.domain.content import Article
from app.services import source_check_service as svc
from tests.test_offline import BASE, GNUBOARD_LIKE

client = TestClient(app)

LONG_KO = "춘천에서 열린 국제 태권도 대회가 25일 막을 내렸다. 한국 대표팀은 종합 우승을 차지했다. " * 3


@pytest.fixture
def robots_ok(monkeypatch):
    monkeypatch.setattr(svc, "allowed", lambda url: "blocked" not in url)


def test_health():
    assert client.get("/api/health").json() == {"ok": True}


def test_search_preview_camel_case_and_outlet(monkeypatch):
    monkeypatch.setattr(svc, "search", lambda kw, count, sort: SearchResult(keyword=kw, articles=[
        Article(title="기사", url="https://www.news.example/1", published="2026-09-25T09:07:13+09:00",
                search_keyword=kw)]))
    r = client.post("/api/source-checks/search", json={"keyword": "태권도"})
    assert r.status_code == 200
    assert r.json() == [{"title": "기사", "url": "https://www.news.example/1", "outlet": "news.example",
                         "date": "2026-09-25T09:07:13+09:00", "keyword": "태권도"}]


def test_search_preview_failure_is_not_empty(monkeypatch):
    # 호출 실패를 0건으로 돌려주지 않는다
    monkeypatch.setattr(svc, "search", lambda kw, count, sort: SearchResult(keyword=kw, ok=False))
    r = client.post("/api/source-checks/search", json={"keyword": "태권도"})
    assert r.status_code == 502 and "네이버" in r.json()["detail"]


def test_board_detect_candidates_with_posts(monkeypatch, robots_ok):
    monkeypatch.setattr(svc, "fetch_list_html", lambda url: GNUBOARD_LIKE)
    r = client.post("/api/source-checks/board", json={"url": BASE})
    body = r.json()
    assert r.status_code == 200 and body["robots"] and body["httpOk"]
    top = body["candidates"][0]
    assert "wr_id={n}" in top["pattern"] and top["links"] == 4
    assert top["posts"][1] == {"title": "2026년 하반기 승단심사 일정 안내",
                               "url": "https://example.com/bbs/board.php?bo_table=notice&wr_id=103",
                               "date": top["posts"][1]["date"]}
    assert top["posts"][1]["date"].endswith("-09-25T00:00:00+09:00")


def test_board_detect_robots_blocked_does_not_fetch(monkeypatch, robots_ok):
    def boom(url):
        raise AssertionError("robots 차단인데 목록을 받았다")
    monkeypatch.setattr(svc, "fetch_list_html", boom)
    r = client.post("/api/source-checks/board", json={"url": "https://blocked.example/bbs"})
    assert r.json() == {"robots": False, "httpOk": False, "candidates": []}


def test_board_detect_rejects_non_http():
    assert client.post("/api/source-checks/board", json={"url": "example.com"}).status_code == 422


def test_url_check_results(monkeypatch, robots_ok):
    bodies = {"https://a.example/ok": LONG_KO, "https://a.example/short": "짧은 글",
              # 긴 외국어 줄은 정제가 지우므로(→ short) 짧은 줄로 언어 판정을 확인한다
              "https://a.example/en": "Final match results were out.\n" * 6,
              "https://a.example/fail": ""}

    def fake_extract(article, html=None):
        article.body = bodies[article.url]
        article.title = "제목"
        return article

    monkeypatch.setattr(svc, "extract_body", fake_extract)
    urls = list(bodies) + ["https://blocked.example/1", "https://a.example/ok", " "]
    r = client.post("/api/source-checks/urls", json={"urls": urls, "minLen": 50})
    got = [(x["url"], x["result"]) for x in r.json()]
    assert got == [("https://a.example/ok", "ok"), ("https://a.example/short", "short"),
                   ("https://a.example/en", "foreign"), ("https://a.example/fail", "fail"),
                   ("https://blocked.example/1", "robots")]
    first = r.json()[0]
    assert first["length"] > 50 and first["title"] == "제목" and first["outlet"] == "a.example"
    assert first["excerpt"].startswith("춘천에서")
    # 해외 사이트 수집이면 언어 판정을 건너뛴다
    r = client.post("/api/source-checks/urls", json={"urls": ["https://a.example/en"], "minLen": 50, "koreanOnly": False})
    assert r.json()[0]["result"] == "ok"


def test_url_check_limits():
    assert client.post("/api/source-checks/urls", json={"urls": []}).status_code == 422
    too_many = [f"https://a.example/{i}" for i in range(svc.MAX_CHECK_URLS + 1)]
    assert client.post("/api/source-checks/urls", json={"urls": too_many}).status_code == 422
    assert client.post("/api/source-checks/urls", json={"urls": ["ftp://a"]}).status_code == 422
