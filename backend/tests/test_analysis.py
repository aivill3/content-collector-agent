"""키워드 분석 — 형태소 지표·관련도 판정·저장·API. 임시 SQLite, 네트워크 없음 (Kiwi 모델은 로컬)."""
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.api.main import app
from app.db.models import Content, ContentAnalysis, ContentKeywordStat, ContentTerm
from app.db.seed import seed
from app.domain.analysis import DEFAULT_SETTINGS
from app.domain.enums import Relevance
from app.repositories import analyses, contents
from app.repositories.scope import scoped_select
from app.repositories.workspaces import DEFAULT_WORKSPACE_ID
from app.services import analysis_service as svc
from app.services.analysis_service import KeywordStat
from app.services.collection_service import CollectResult
from app.workers.analysis import analyze_content, analyze_pending
from tests.test_db import article, item, news_source, run

S = DEFAULT_SETTINGS

MAIN_BODY = ("태권도 대회가 춘천에서 열렸다. 태권도 선수 300명이 참가했다. "
             "국기원은 태권도 품새 심사를 함께 진행했다. 태권도 협회는 내년에도 대회를 연다.")
PASSING_BODY = ("춘천시는 14일 가을 축제 일정을 발표했다. 축제에는 공연과 먹거리 장터가 열린다. "
                "개막식에서는 태권도 시범이 있다. 시는 관광객 10만 명을 예상한다.")


# ── 서비스 (저장 없음) ──────────────────────────────────────

def test_analyze_text_metrics_and_terms():
    t = svc.analyze_text("태권도 대회가 열렸다. 선수들이 WT 규정에 따라 아름다운 품새를 보였다!")
    assert t.sentences == 2
    assert t.tokens > t.nouns > 0 and 0 < t.ttr <= 1
    assert t.unique_tokens <= t.tokens
    terms = {(x.term, x.pos) for x in t.terms}
    assert ("태권도", "NNG") in terms and ("WT", "SL") in terms
    assert ("열리다", "VV") in terms and ("아름답다", "VA") in terms     # 동사·형용사는 기본형
    assert not any(x.pos.startswith(("J", "E", "S")) and x.pos != "SL" for x in t.terms)   # 조사·어미·기호 제외


def test_empty_body():
    t = svc.analyze_text("   ")
    assert (t.tokens, t.sentences, t.ttr, t.terms) == (0, 0, 0.0, [])


def test_keyword_stat_counts_string_and_spacing():
    s = svc.keyword_stat("태권도", "춘천 태권도 대회", "태권도장에서 태권도를 배운다. TAEKWONDO")
    assert (s.mentions, s.title_has) == (2, True)                         # '태권도장'도 언급
    assert s.density == round(2 * 1000 / len("태권도장에서 태권도를 배운다. TAEKWONDO"), 2)
    assert svc.keyword_stat("승단 심사", "", "승단심사와 승단 심사").mentions == 2
    assert svc.keyword_stat("WT", "", "wt 와 Wt").mentions == 2          # 대소문자 무시
    assert svc.keyword_stat("  ", "x", "x").mentions == 0


@pytest.mark.parametrize("mentions, density, title_has, length, expected", [
    (2, 9.9, True, 1000, Relevance.PASSING),      # 한두 번 언급
    (0, 0.0, False, 100, Relevance.PASSING),
    (3, 9.9, True, 1000, Relevance.PARTIAL),      # 최소 언급(4) 미만
    (4, 1.5, True, 1000, Relevance.MAIN),         # 제목 포함 기준 1.5 이상
    (4, 1.4, True, 1000, Relevance.PARTIAL),
    (4, 2.9, False, 1000, Relevance.PARTIAL),     # 제목 미포함 기준 3.0
    (4, 3.0, False, 1000, Relevance.MAIN),
    (4, 0.1, False, 599, Relevance.MAIN),         # 600자 미만은 밀도 검사 건너뜀
])
def test_judge(mentions, density, title_has, length, expected):
    assert svc.judge(KeywordStat("k", mentions, density, title_has), length, S) == expected


def test_judge_require_title_and_best():
    stat = KeywordStat("k", 5, 9.0, False)
    assert svc.judge(stat, 1000, replace(S, require_title=True)) == Relevance.PARTIAL
    assert svc.best_relevance([Relevance.PASSING, Relevance.MAIN, Relevance.PARTIAL]) == Relevance.MAIN
    assert svc.best_relevance([]) is None


def test_top_words_pos_range_denom_and_stopwords():
    terms = [svc.Term("태권도", "NNG", 6), svc.Term("열리다", "VV", 3), svc.Term("WT", "SL", 1), svc.Term("대회", "NNG", 2)]
    vva = svc.top_words(terms, S)                                         # 명사+동사·형용사, 분모 내용어
    assert [w.term for w in vva] == ["태권도", "열리다", "대회"]
    assert vva[0].density == round(6 * 100 / 11, 1)
    noun = svc.top_words(terms, replace(S, pos_range="noun", denom="noun"))
    assert [w.term for w in noun] == ["태권도", "대회"] and noun[0].density == 75.0
    assert [w.term for w in svc.top_words(terms, replace(S, pos_range="foreign", top_n=2))] == ["태권도", "열리다"]
    assert "태권도" not in [w.term for w in svc.top_words(terms, S, stopwords=frozenset({"태권도"}))]


# ── 워커·저장 ──────────────────────────────────────────────

def save(session, ws, bodies: dict[str, tuple[str, str]], kw="태권도") -> dict[str, int]:
    """URL 끝자리 → (제목, 정제 본문). 키워드 kw 로 찾은 글로 저장한다."""
    src = news_source(session, ws)
    arts = []
    for key, (title, body) in bodies.items():
        a = article(url=f"https://news.example.com/{key}", kw=kw)
        a.title, a.body, a.body_clean = title, body, body
        arts.append(a)
    run(session, ws, src.id, CollectResult(articles=arts, raw={kw: [item(a.url) for a in arts]}))
    return {c.url.rsplit("/", 1)[1]: c.id for c in session.exec(scoped_select(Content, ws))}


def test_analyze_pending_saves_and_judges(session, ws_a, ws_b):
    ids = save(session, ws_a, {"main": ("춘천 태권도 대회", MAIN_BODY), "pass": ("가을 축제", PASSING_BODY)})
    other = save(session, ws_b, {"x": ("태권도", MAIN_BODY)})

    summary = analyze_pending(session, ws_a)
    assert summary.analyzed == 2
    main = analyses.get_analysis(session, ws_a, ids["main"])
    assert main.relevance == Relevance.MAIN and main.tokens > 0 and main.settings_version == S.version
    assert main.analyzer.startswith("kiwi ")
    stat = analyses.list_keyword_stats(session, ws_a, ids["main"])[0]
    assert (stat.keyword, stat.mentions, stat.title_has) == ("태권도", 4, True)
    assert analyses.get_analysis(session, ws_a, ids["pass"]).relevance == Relevance.PASSING
    assert analyses.list_terms(session, ws_a, ids["main"])[0].term == "태권도"
    # 다른 워크스페이스는 분석하지 않았고, 이쪽에서 보이지도 않는다
    assert analyses.get_analysis(session, ws_b, other["x"]) is None
    assert analyses.get_analysis(session, ws_b, ids["main"]) is None
    # 다시 돌리면 할 일이 없다
    again = analyze_pending(session, ws_a)
    assert (again.analyzed, again.keyword_stats) == (0, 0)


def test_new_keyword_on_analyzed_content_adds_stat_only(session, ws_a):
    ids = save(session, ws_a, {"a": ("춘천 대회", MAIN_BODY)})
    analyze_pending(session, ws_a)
    before = analyses.get_analysis(session, ws_a, ids["a"]).analyzed_at
    # 다음 수집에서 같은 글이 '국기원'으로도 걸렸다 (이미 저장된 글이라 키워드 기록만 생긴다)
    src_id = contents.get_content(session, ws_a, ids["a"]).source_id
    run(session, ws_a, src_id, CollectResult(raw={"국기원": [item("https://news.example.com/a")]}))
    summary = analyze_pending(session, ws_a)
    assert (summary.analyzed, summary.keyword_stats) == (0, 1)
    stats = {s.keyword: s for s in analyses.list_keyword_stats(session, ws_a, ids["a"])}
    assert set(stats) == {"태권도", "국기원"} and stats["국기원"].mentions == 1
    assert analyses.get_analysis(session, ws_a, ids["a"]).analyzed_at == before


def test_reanalyze_replaces_and_delete_cascades(session, ws_a):
    ids = save(session, ws_a, {"a": ("춘천 태권도 대회", MAIN_BODY)})
    analyze_pending(session, ws_a)
    n_terms = len(analyses.list_terms(session, ws_a, ids["a"]))
    assert analyze_content(session, ws_a, ids["a"]) is True
    session.commit()
    assert len(analyses.list_terms(session, ws_a, ids["a"])) == n_terms     # 덮어쓰기 (중복 없음)
    assert len(session.exec(scoped_select(ContentAnalysis, ws_a)).all()) == 1
    assert analyze_content(session, ws_a, 999999) is False

    contents.delete_content(session, ws_a, ids["a"])
    session.commit()
    for model in (ContentAnalysis, ContentTerm, ContentKeywordStat):
        assert session.exec(scoped_select(model, ws_a)).all() == []


def test_board_content_has_no_relevance(session, ws_a):
    ids = save(session, ws_a, {"a": ("공지", MAIN_BODY)})
    # 키워드 기록 없이 저장된 글 (게시판·URL 수집분과 같다)
    for h in contents.list_hits(session, ws_a, ids["a"]):
        session.delete(h)
    session.commit()
    analyze_pending(session, ws_a)
    a = analyses.get_analysis(session, ws_a, ids["a"])
    assert a.tokens > 0 and a.relevance is None


# ── API ──────────────────────────────────────────────────

@pytest.fixture
def client(session):
    seed(session)
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_detail_list_filter_and_reanalyze(client, session):
    ws = DEFAULT_WORKSPACE_ID
    ids = save(session, ws, {"main": ("춘천 태권도 대회", MAIN_BODY), "pass": ("가을 축제", PASSING_BODY)})

    before = client.get(f"/api/contents/{ids['main']}").json()
    assert before["analysis"] is None and before["relevance"] is None
    assert before["analysisSettings"]["densTitle"] == 1.5 and before["analysisSettings"]["metrics"]["avgLen"] is False

    analyze_pending(session, ws)
    d = client.get(f"/api/contents/{ids['main']}").json()
    a = d["analysis"]
    assert d["relevance"] == a["relevance"] == "main"
    assert set(a["metrics"]) == {"tokens", "unique", "nouns", "sentences", "avgLen", "ttr"}
    assert a["topWords"][0] == {"word": "태권도", "pos": "NNG", "count": 4, "density": a["topWords"][0]["density"]}
    assert len(a["topWords"]) <= S.top_n
    assert a["keywords"] == [{"keyword": "태권도", "mentions": 4, "density": a["keywords"][0]["density"],
                              "titleHas": True, "relevance": "main"}]
    assert a["analyzedAt"].endswith("+09:00")

    lst = client.get("/api/contents").json()
    assert lst["passingMode"] == "dim"
    assert {x["id"]: x["relevance"] for x in lst["items"]} == {ids["main"]: "main", ids["pass"]: "passing"}
    only = client.get("/api/contents", params={"relevance": "passing"}).json()
    assert [x["id"] for x in only["items"]] == [ids["pass"]] and only["total"] == 1

    r = client.post(f"/api/contents/{ids['main']}/reanalyze")
    assert r.status_code == 200 and r.json()["analysis"]["relevance"] == "main"
    assert client.post("/api/contents/999999/reanalyze").status_code == 404


def test_api_hide_passing(client, session, monkeypatch):
    ws = DEFAULT_WORKSPACE_ID
    ids = save(session, ws, {"main": ("춘천 태권도 대회", MAIN_BODY), "pass": ("가을 축제", PASSING_BODY)})
    analyze_pending(session, ws)
    monkeypatch.setattr(analyses, "get_settings", lambda *a, **k: replace(S, passing_mode="hide"))
    lst = client.get("/api/contents").json()
    assert [x["id"] for x in lst["items"]] == [ids["main"]] and lst["passingMode"] == "hide"
    # '스쳐 지나감' 필터를 고르면 숨김과 상관없이 보인다
    assert [x["id"] for x in client.get("/api/contents", params={"relevance": "passing"}).json()["items"]] == [ids["pass"]]
