"""콘텐츠 조회 API — 임시 SQLite 를 의존성 교체로 붙인다 (네트워크 없음)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api.deps import get_session
from app.api.main import app
from app.db.models import Content
from app.core.timeutil import day_start_utc, display_today
from app.db.seed import seed
from app.repositories.workspaces import DEFAULT_WORKSPACE_ID
from app.services.collection_service import CollectResult
from tests.test_db import article, item, news_source, run


def utc(*a) -> datetime:
    return datetime(*a, tzinfo=timezone.utc)


@pytest.fixture
def client(session):
    seed(session)
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def add_contents(session, ws, specs: dict[str, dict], *, source_name="뉴스") -> dict[str, int]:
    """URL 끝자리 → {collected_at, published, kw, title}. 만든 콘텐츠의 id 를 돌려준다."""
    src = news_source(session, ws)
    src.name = source_name
    arts, raw = [], {}
    for key, spec in specs.items():
        a = article(url=f"https://news.example.com/{key}", kw=spec.get("kw", "태권도"))
        a.title = spec.get("title", key)
        a.published = spec.get("published", "")
        arts.append(a)
        raw.setdefault(a.search_keyword, []).append(item(a.url))
    run(session, ws, src.id, CollectResult(articles=arts, raw=raw))
    ids = {}
    for c in session.exec(select(Content).where(Content.workspace_id == ws)):
        key = c.url.rsplit("/", 1)[1]
        if key in specs:
            c.collected_at = specs[key]["collected_at"]
            session.add(c)
            ids[key] = c.id
    session.commit()
    return ids


def keys(body) -> list[str]:
    return [x["url"].rsplit("/", 1)[1] for x in body["items"]]


def test_pagination_and_default_sort(client, session):
    add_contents(session, DEFAULT_WORKSPACE_ID, {f"c{i}": {"collected_at": utc(2026, 9, 20, i)} for i in range(5)})
    first = client.get("/api/contents", params={"size": 2}).json()
    assert (first["total"], first["page"], first["size"], first["pageCount"]) == (5, 1, 2, 3)
    assert keys(first) == ["c4", "c3"]                        # 기본: 수집일 최신순
    last = client.get("/api/contents", params={"size": 2, "page": 3}).json()
    assert keys(last) == ["c0"]
    beyond = client.get("/api/contents", params={"size": 2, "page": 9}).json()
    assert beyond["items"] == [] and beyond["total"] == 5
    asc = client.get("/api/contents", params={"size": 2, "order": "asc"}).json()
    assert keys(asc) == ["c0", "c1"]


def test_list_item_shape_has_no_body(client, session):
    add_contents(session, DEFAULT_WORKSPACE_ID, {
        "a": {"collected_at": utc(2026, 9, 30, 5, 20), "published": "2026-09-30T08:00:00+09:00", "title": "태권도 대회"}},
        source_name="태권도 뉴스")
    x = client.get("/api/contents").json()["items"][0]
    assert set(x) == {"id", "title", "url", "publisher", "summary", "excerpt", "collectionPath", "sourceId",
                      "sourceName", "publishedAt", "collectedAt", "keywords", "bodyLength"}
    assert x["summary"] == "요약" and x["excerpt"] == "정제 본문"
    assert x["sourceName"] == "태권도 뉴스" and x["keywords"] == ["태권도"] and x["collectionPath"] == "naver"
    assert x["collectedAt"] == "2026-09-30T14:20:00+09:00"     # DISPLAY_TZ ISO
    assert x["publishedAt"] == "2026-09-30T08:00:00+09:00"


def test_period_filter_uses_kst_day_boundaries(client, session):
    add_contents(session, DEFAULT_WORKSPACE_ID, {
        "prev_2359": {"collected_at": utc(2026, 9, 29, 14, 59, 59)},   # KST 09-29 23:59:59
        "kst_0000": {"collected_at": utc(2026, 9, 29, 15, 0)},          # KST 09-30 00:00 (UTC 로는 29일)
        "kst_0859": {"collected_at": utc(2026, 9, 29, 23, 59, 59)},     # KST 09-30 08:59:59 (UTC 로는 29일)
        "kst_2359": {"collected_at": utc(2026, 9, 30, 14, 59, 59)},     # KST 09-30 23:59:59
        "next_0000": {"collected_at": utc(2026, 9, 30, 15, 0)},         # KST 10-01 00:00
    })
    day = client.get("/api/contents", params={"from": "2026-09-30", "to": "2026-09-30"}).json()
    assert sorted(keys(day)) == ["kst_0000", "kst_0859", "kst_2359"] and day["total"] == 3
    since = client.get("/api/contents", params={"from": "2026-09-30"}).json()
    assert since["total"] == 4                                  # 한쪽만 줘도 된다
    until = client.get("/api/contents", params={"to": "2026-09-29"}).json()
    assert keys(until) == ["prev_2359"]
    assert client.get("/api/contents", params={"from": "2026-09-30", "to": "2026-09-29"}).status_code == 422


def test_recent_days_filter_uses_display_today(client, session):
    today = day_start_utc(display_today())          # 표시 시간대 오늘 00:00 (UTC)
    add_contents(session, DEFAULT_WORKSPACE_ID, {
        "today": {"collected_at": today + timedelta(minutes=1)},
        "d6": {"collected_at": today - timedelta(days=6) + timedelta(minutes=1)},      # 7일 범위의 첫날
        "d7": {"collected_at": today - timedelta(days=6) - timedelta(minutes=1)},      # 그 전날 23:59
    })
    assert keys(client.get("/api/contents", params={"days": 1}).json()) == ["today"]
    assert sorted(keys(client.get("/api/contents", params={"days": 7}).json())) == ["d6", "today"]
    assert client.get("/api/contents", params={"days": 0}).status_code == 422
    assert client.get("/api/contents", params={"days": 7, "from": "2026-09-01"}).status_code == 422


def test_filters_search_and_published_sort(client, session):
    ids = add_contents(session, DEFAULT_WORKSPACE_ID, {
        "old": {"collected_at": utc(2026, 9, 30, 1), "published": "2026-09-01T09:00:00+09:00", "title": "국기원 소식"},
        "new": {"collected_at": utc(2026, 9, 30, 2), "published": "2026-09-29T09:00:00+09:00", "title": "태권도 100% 우승"},
        "none": {"collected_at": utc(2026, 9, 30, 3), "title": "발행일 모름"},
    })
    by_pub = client.get("/api/contents", params={"sort": "published_at"}).json()
    assert keys(by_pub) == ["new", "old", "none"]                # 발행일 모름은 맨 뒤
    by_pub_asc = client.get("/api/contents", params={"sort": "published_at", "order": "asc"}).json()
    assert keys(by_pub_asc) == ["old", "new", "none"]
    assert keys(client.get("/api/contents", params={"q": "100%"}).json()) == ["new"]     # % 는 글자 그대로
    assert keys(client.get("/api/contents", params={"q": "국기원"}).json()) == ["old"]
    pub_day = client.get("/api/contents", params={"from": "2026-09-29", "dateField": "published_at"}).json()
    assert keys(pub_day) == ["new"]
    src_id = client.get(f"/api/contents/{ids['old']}").json()["sourceId"]
    assert client.get("/api/contents", params={"sourceId": src_id}).json()["total"] == 3
    assert client.get("/api/contents", params={"sourceId": src_id + 99}).json()["total"] == 0
    assert client.get("/api/contents", params={"collectionPath": "board"}).json()["total"] == 0
    assert client.get("/api/contents", params={"size": 101}).status_code == 422


def test_detail_and_other_workspace_is_404(client, session, ws_b):
    mine = add_contents(session, DEFAULT_WORKSPACE_ID, {"mine": {"collected_at": utc(2026, 9, 30, 1)}})
    theirs = add_contents(session, ws_b, {"theirs": {"collected_at": utc(2026, 9, 30, 1)}})

    d = client.get(f"/api/contents/{mine['mine']}").json()
    assert d["cleanedBody"] == "정제 본문" and d["rawBody"] == "원본 본문" and d["summary"] == "요약"
    assert d["excerpt"] == "정제 본문"
    assert [(h["keyword"], h["rank"]) for h in d["hits"]] == [("태권도", 1)]
    assert d["hits"][0]["foundAt"].endswith("+09:00")

    other = client.get(f"/api/contents/{theirs['theirs']}")
    missing = client.get("/api/contents/999999")
    assert other.status_code == missing.status_code == 404
    assert other.json() == missing.json()                       # 존재 여부를 드러내지 않는다
    # 목록에도 나오지 않는다
    assert keys(client.get("/api/contents").json()) == ["mine"]


def test_source_options_are_workspace_scoped(client, session, ws_b):
    add_contents(session, DEFAULT_WORKSPACE_ID, {"a": {"collected_at": utc(2026, 9, 30, 1)}}, source_name="내 소스")
    add_contents(session, ws_b, {"b": {"collected_at": utc(2026, 9, 30, 1)}}, source_name="남의 소스")
    opts = client.get("/api/sources/options").json()
    assert [(o["name"], o["type"]) for o in opts] == [("내 소스", "news_keyword")]
    assert isinstance(opts[0]["id"], int)


def test_excerpt_is_head_of_cleaned_body(client, session):
    ids = add_contents(session, DEFAULT_WORKSPACE_ID, {"a": {"collected_at": utc(2026, 9, 30, 1)}})
    c = session.get(Content, ids["a"])
    c.cleaned_body = "첫 문단입니다.\n\n둘째   문단" + "가" * 300
    session.add(c)
    session.commit()
    x = client.get("/api/contents").json()["items"][0]
    assert x["excerpt"].startswith("첫 문단입니다. 둘째 문단가")     # 줄바꿈·연속 공백은 한 칸
    assert len(x["excerpt"]) <= 120
