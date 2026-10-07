"""DB 계층 테스트 — 임시 SQLite 파일에서 돈다. 네트워크 없음. python -m pytest tests"""
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import select

from app.api.deps import get_current_workspace
from app.db.models import Content, ContentKeywordHit, JobApiResponse, Workspace
from app.db.seed import seed
from app.domain.content import Article
from app.domain.enums import JobStatus, JobTrigger, SourceType
from app.repositories import contents, jobs, sources
from app.repositories.scope import scoped_select
from app.repositories.workspaces import DEFAULT_WORKSPACE_ID
from app.services.collection_service import CollectResult

URL = "https://news.example.com/article/1"
KST_ISO = "2026-09-25T09:00:00+09:00"


def news_source(session, ws, keywords=("태권도", "국기원")):
    return sources.create_source(session, ws, name="뉴스", type=SourceType.NEWS_KEYWORD,
                                 config={"count": 10}, keywords=keywords)


def article(url=URL, kw="태권도", rank=1) -> Article:
    return Article(title="춘천 태권도 대회", url=url, source="naver", press="예시일보", published=KST_ISO,
                   summary="요약", search_keyword=kw, search_rank=rank, body="원본 본문", body_clean="정제 본문")


def item(url: str) -> dict:
    """네이버 API items 한 건 (originallink 가 언론사 원문)."""
    return {"title": "<b>태권도</b>", "originallink": url, "link": "https://n.news.naver.com/x", "pubDate": ""}


def run(session, ws, source_id, result: CollectResult):
    """워커가 할 일을 흉내 낸다: 작업 생성 → 실행 중 → 저장 → 커밋."""
    job = jobs.create_job(session, ws, source_id, JobTrigger.MANUAL)
    jobs.mark_running(session, ws, job.id)
    summary = contents.save_collect_result(session, ws, job.id, result)
    session.commit()
    return job, summary


def count(session, model, ws=None) -> int:
    stmt = select(model) if ws is None else scoped_select(model, ws)
    return len(session.exec(stmt).all())


# ── 1. 워크스페이스 격리 ──────────────────────────────────

def test_workspace_a_data_is_invisible_to_b(session, ws_a, ws_b):
    src = news_source(session, ws_a)
    job, _ = run(session, ws_a, src.id, CollectResult(articles=[article()], stats={"검색": 1}))
    content = contents.list_contents(session, ws_a)[0]

    assert sources.list_sources(session, ws_b) == []
    assert sources.get_source(session, ws_b, src.id) is None
    assert sources.list_keywords(session, ws_b, src.id) == []
    assert sources.update_source(session, ws_b, src.id, name="바꿈") is None
    assert jobs.get_job(session, ws_b, job.id) is None and jobs.list_jobs(session, ws_b) == []
    assert contents.list_contents(session, ws_b) == []
    assert contents.get_content(session, ws_b, content.id) is None
    assert contents.list_hits(session, ws_b, content.id) == []
    assert contents.seen_urls(session, ws_b) == set()
    # 다른 워크스페이스의 소스·작업을 대상으로 쓰기도 못 한다 (없는 것과 같은 오류)
    with pytest.raises(LookupError):
        sources.add_keywords(session, ws_b, src.id, ["침투"])
    with pytest.raises(LookupError):
        jobs.create_job(session, ws_b, src.id, JobTrigger.MANUAL)
    with pytest.raises(LookupError):
        contents.save_collect_result(session, ws_b, job.id, CollectResult())
    # A 에서는 그대로 보인다
    assert [s.id for s in sources.list_sources(session, ws_a)] == [src.id]
    assert contents.seen_urls(session, ws_a) == {URL}


def test_scoped_select_rejects_unscoped_model(ws_a):
    with pytest.raises(TypeError):
        scoped_select(Workspace, ws_a)
    with pytest.raises(TypeError):
        scoped_select(Content, None)


# ── 2. 같은 워크스페이스: URL 은 한 번, 키워드 기록만 추가 ─────────

def test_same_url_saved_once_and_new_keyword_adds_hit(session, ws_a):
    src = news_source(session, ws_a, keywords=("태권도", "국기원", "태권도 대회"))
    # 1회차: 두 키워드에 같은 기사. dedupe() 가 국기원 쪽을 버려 articles 에는 하나뿐이다.
    first = CollectResult(
        articles=[article(kw="태권도", rank=1)],
        raw={"태권도": [item(URL)], "국기원": [item("https://other.example/9"), item(URL)]},
        stats={"검색": 3, "정제 통과": 1},
    )
    job1, s1 = run(session, ws_a, src.id, first)
    assert (s1.new_contents, s1.new_hits) == (1, 2)
    content = contents.list_contents(session, ws_a)[0]
    hits = {(h.keyword, h.rank, h.job_id) for h in contents.list_hits(session, ws_a, content.id)}
    assert hits == {("태권도", 1, job1.id), ("국기원", 2, job1.id)}
    assert content.first_job_id == job1.id

    # 2회차: 이미 저장된 글은 exclude_urls 로 빠져 articles 가 비어 있다.
    # 추적 파라미터가 붙은 같은 기사가 새 키워드로 걸렸다 → 콘텐츠는 그대로, 기록만 추가
    assert URL in contents.seen_urls(session, ws_a)
    second = CollectResult(raw={"태권도 대회": [item(URL + "?utm_source=naver")], "태권도": [item(URL)]})
    job2, s2 = run(session, ws_a, src.id, second)
    assert (s2.new_contents, s2.new_hits) == (0, 1)
    assert count(session, Content, ws_a) == 1
    hit = contents.list_hits(session, ws_a, content.id)[-1]
    kw_id = {k.keyword: k.id for k in sources.list_keywords(session, ws_a, src.id)}["태권도 대회"]
    assert (hit.keyword, hit.job_id, hit.source_keyword_id) == ("태권도 대회", job2.id, kw_id)

    # 3회차: 같은 결과를 다시 저장해도 늘어나는 것은 없다
    _, s3 = run(session, ws_a, src.id, first)
    assert (s3.new_contents, s3.known_contents, s3.new_hits) == (0, 1, 0)
    assert count(session, ContentKeywordHit, ws_a) == 3


def test_removed_keyword_keeps_hit_text(session, ws_a):
    src = news_source(session, ws_a)
    run(session, ws_a, src.id, CollectResult(articles=[article(kw="국기원")]))
    assert sources.remove_keyword(session, ws_a, src.id, " 국기원 ")
    session.commit()
    hit = session.exec(select(ContentKeywordHit)).one()
    session.refresh(hit)
    assert (hit.keyword, hit.source_keyword_id) == ("국기원", None)   # ON DELETE SET NULL


# ── 3. 다른 워크스페이스: 같은 URL 도 각각 저장 ──────────────────

def test_same_url_in_other_workspace_is_saved_separately(session, ws_a, ws_b):
    for ws in (ws_a, ws_b):
        src = news_source(session, ws)
        _, s = run(session, ws, src.id, CollectResult(articles=[article()], raw={"태권도": [item(URL)]}))
        assert (s.new_contents, s.new_hits) == (1, 1)
    assert count(session, Content) == 2
    a, b = contents.list_contents(session, ws_a)[0], contents.list_contents(session, ws_b)[0]
    assert a.url_hash == b.url_hash and a.id != b.id


# ── 저장 내용 ────────────────────────────────────────────

def test_saved_fields_job_and_source_state(session, ws_a):
    src = news_source(session, ws_a)
    result = CollectResult(
        articles=[article(), article(url="https://news.example.com/2", rank=2)],
        stats={"검색": 20, "중복 제거 후": 15, "기간 필터 후": 10, "신규": 8, "본문 확보": 5, "정제 통과": 2},
        raw={"태권도": [item(URL)], "국기원": []},
        latest_published=KST_ISO,
        failed_keywords=["국기원"],
    )
    job, _ = run(session, ws_a, src.id, result)
    session.refresh(job)
    assert job.status == JobStatus.SUCCESS and job.collected_count == 2
    assert job.stage_counts == result.stats
    assert job.error_message == "일부 키워드 수집 실패: 국기원"   # 실패해도 나머지는 저장
    assert job.duration_sec is not None and job.finished_at.tzinfo is not None
    assert count(session, JobApiResponse, ws_a) == 2

    c = contents.get_content(session, ws_a, contents.list_contents(session, ws_a)[-1].id)
    assert (c.publisher, c.raw_body, c.cleaned_body, c.body_length) == ("예시일보", "원본 본문", "정제 본문", 5)
    assert c.collection_path == "naver" and c.normalized_url == URL and len(c.url_hash) == 64
    # KST 로 받은 발행 시각이 UTC aware 로 저장·조회된다
    assert c.published_at == datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
    assert c.published_at.tzinfo == timezone.utc

    src = sources.get_source(session, ws_a, src.id)
    assert src.last_status == JobStatus.SUCCESS and src.last_collected_at is not None
    assert src.last_published_at == datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)


def test_unknown_published_is_null_and_failed_job(session, ws_a):
    src = sources.create_source(session, ws_a, name="글", type=SourceType.URL, config={"urls": [URL]})
    a = article()
    a.published, a.source, a.search_keyword = "어제쯤", "website", ""
    run(session, ws_a, src.id, CollectResult(articles=[a]))
    assert contents.list_contents(session, ws_a)[0].published_at is None
    assert count(session, ContentKeywordHit) == 0          # 키워드 수집이 아니면 기록 없음

    job = jobs.create_job(session, ws_a, src.id, JobTrigger.SCHEDULED)
    jobs.fail_job(session, ws_a, job.id, "네이버 호출 실패")
    assert jobs.get_job(session, ws_a, job.id).status == JobStatus.FAILED
    assert sources.get_source(session, ws_a, src.id).last_status == JobStatus.FAILED


def test_naive_datetime_is_rejected(session, ws_a):
    src = news_source(session, ws_a)
    src.next_run_at = datetime(2026, 9, 30, 9, 0)
    session.add(src)
    with pytest.raises(Exception, match="시간대"):
        session.flush()


# ── 소스 설정 검증 ────────────────────────────────────────

def test_source_config_validation_and_defaults(session, ws_a):
    news = news_source(session, ws_a, keywords=["  태권도   대회 ", "태권도 대회", " "])
    assert [k.keyword for k in sources.list_keywords(session, ws_a, news.id)] == ["태권도 대회"]
    assert news.min_body_length == 100 and news.config == {"count": 10, "sort": "sim", "days": 3}

    board = sources.create_source(session, ws_a, name="게시판", type=SourceType.BOARD, config={
        "list_url": "https://example.com/bbs?bo_table=n", "list_pattern": "/bbs?bo_table=n&wr_id={n}"})
    assert board.min_body_length == 30
    cfg = sources.source_config(board).to_board_config()
    assert cfg.list_pattern == "/bbs?bo_table=n&wr_id={n}" and cfg.max_items == 50

    bad = [
        (SourceType.NEWS_KEYWORD, {"count": 1001}),
        (SourceType.NEWS_KEYWORD, {"sort": "popular"}),
        (SourceType.NEWS_KEYWORD, {"cnt": 10}),                           # 오타 키
        (SourceType.BOARD, {"list_url": "example.com"}),
        (SourceType.BOARD, {"list_url": "https://e.com", "include_pattern": "("}),
        (SourceType.URL, {"urls": [" "]}),
    ]
    for type_, config in bad:
        with pytest.raises(ValidationError):
            sources.create_source(session, ws_a, name="x", type=type_, config=config)
    with pytest.raises(ValueError):
        sources.create_source(session, ws_a, name="x", type=SourceType.URL, config={"urls": [URL]},
                              schedule_time="25:00")
    with pytest.raises(ValueError):
        sources.add_keywords(session, ws_a, board.id, ["태권도"])      # 게시판에는 검색어 없음
    with pytest.raises(ValueError):
        sources.update_source(session, ws_a, board.id, type=SourceType.URL)


# ── 기본 워크스페이스 · API 의존성 ─────────────────────────

def test_seed_and_current_workspace(session):
    with pytest.raises(HTTPException) as e:
        get_current_workspace(session)
    assert e.value.status_code == 503
    seed(session)
    seed(session)                                          # 여러 번 실행해도 하나
    assert count(session, Workspace) == 1
    assert get_current_workspace(session).id == DEFAULT_WORKSPACE_ID
