"""소스 1회 실행 — 수집 함수는 가짜로 바꾼다 (네트워크 없음)."""
from datetime import datetime, timezone

import pytest

from app.domain.enums import JobStatus, JobTrigger, SourceType
from app.repositories import contents, jobs, sources
from app.services import collection_service
from app.services.collection_service import CollectResult
from app.workers.runner import run_source_once
from tests.test_db import KST_ISO, article, item, news_source

URL1, URL2 = "https://news.example.com/1", "https://news.example.com/2"


class FakeCollect:
    """collect_keywords 대역. 받은 인자를 기록하고, 이미 저장된 URL 은 실제처럼 뺀다."""

    def __init__(self, urls=(URL1, URL2), failed=()):
        self.urls, self.failed, self.calls = urls, list(failed), []

    def __call__(self, keywords, **kw):
        self.calls.append({"keywords": keywords, **kw})
        fresh = [u for u in self.urls if u not in (kw["exclude_urls"] or set())]
        return CollectResult(
            articles=[article(url=u, kw=keywords[0], rank=i) for i, u in enumerate(fresh, 1)],
            raw={k: [item(u) for u in self.urls] for k in keywords if k not in self.failed},
            stats={"검색": len(self.urls), "신규": len(fresh), "정제 통과": len(fresh)},
            latest_published=KST_ISO if fresh else None,
            failed_keywords=self.failed,
        )


@pytest.fixture
def fake(monkeypatch):
    f = FakeCollect()
    monkeypatch.setattr(collection_service, "collect_keywords", f)
    return f


def test_run_saves_and_updates_source(session, ws_a, fake):
    src = news_source(session, ws_a)
    job = run_source_once(session, ws_a, src.id, JobTrigger.MANUAL)

    assert job.status == JobStatus.SUCCESS and job.collected_count == 2
    assert job.started_at and job.finished_at and job.duration_sec is not None
    assert job.stage_counts == {"검색": 2, "신규": 2, "정제 통과": 2}
    call = fake.calls[0]
    assert call["keywords"] == ["태권도", "국기원"]
    assert (call["count"], call["sort"], call["days"], call["since"]) == (10, "sim", 3, None)
    assert (call["min_len"], call["korean_only"], call["exclude_urls"]) == (100, True, set())

    src = sources.get_source(session, ws_a, src.id)
    assert src.last_status == JobStatus.SUCCESS and src.last_collected_at is not None
    assert src.last_published_at == datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
    assert len(contents.list_contents(session, ws_a)) == 2


def test_rerun_passes_since_and_excludes_saved(session, ws_a, fake):
    src = news_source(session, ws_a)
    run_source_once(session, ws_a, src.id)
    again = run_source_once(session, ws_a, src.id)

    call = fake.calls[1]
    assert call["exclude_urls"] == {URL1, URL2}
    assert call["since"] == datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
    assert again.status == JobStatus.SUCCESS and again.collected_count == 0
    assert len(contents.list_contents(session, ws_a)) == 2


def test_partial_keyword_failure_is_recorded(session, ws_a, monkeypatch):
    monkeypatch.setattr(collection_service, "collect_keywords", FakeCollect(failed=["국기원"]))
    job = run_source_once(session, ws_a, news_source(session, ws_a).id)
    assert job.status == JobStatus.SUCCESS and job.collected_count == 2
    assert job.error_message == "일부 키워드 수집 실패: 국기원"


def test_exception_marks_job_failed(session, ws_a, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("네이버 응답 없음")
    monkeypatch.setattr(collection_service, "collect_keywords", boom)
    src = news_source(session, ws_a)
    job = run_source_once(session, ws_a, src.id, JobTrigger.SCHEDULED)

    assert job.status == JobStatus.FAILED and job.trigger == JobTrigger.SCHEDULED
    assert job.error_message == "RuntimeError: 네이버 응답 없음"
    assert job.finished_at is not None and job.collected_count == 0
    src = sources.get_source(session, ws_a, src.id)
    assert src.last_status == JobStatus.FAILED and src.last_collected_at is not None


def test_save_error_rolls_back_and_fails(session, ws_a, fake, monkeypatch):
    def broken(*a, **kw):
        raise ValueError("저장 실패")
    monkeypatch.setattr(contents, "save_collect_result", broken)
    job = run_source_once(session, ws_a, news_source(session, ws_a).id)
    assert job.status == JobStatus.FAILED and "저장 실패" in job.error_message
    assert contents.list_contents(session, ws_a) == []


def test_news_source_without_keywords_fails(session, ws_a, fake):
    src = news_source(session, ws_a, keywords=())
    job = run_source_once(session, ws_a, src.id)
    assert job.status == JobStatus.FAILED and "키워드" in job.error_message
    assert fake.calls == []


def test_board_and_url_sources_call_their_collectors(session, ws_a, monkeypatch):
    seen = {}
    monkeypatch.setattr(collection_service, "collect_board",
                        lambda cfg, **kw: seen.setdefault("board", (cfg, kw)) and CollectResult())
    monkeypatch.setattr(collection_service, "collect_urls",
                        lambda urls, **kw: seen.setdefault("url", (urls, kw)) and CollectResult())
    board = sources.create_source(session, ws_a, name="게시판", type=SourceType.BOARD, allow_non_korean=True,
                                  config={"list_url": "https://e.com/bbs", "days": 7, "list_pattern": "/v/{n}"})
    url = sources.create_source(session, ws_a, name="글", type=SourceType.URL, config={"urls": [URL1]})
    assert run_source_once(session, ws_a, board.id).status == JobStatus.SUCCESS
    assert run_source_once(session, ws_a, url.id).status == JobStatus.SUCCESS

    cfg, kw = seen["board"]
    assert cfg.list_url == "https://e.com/bbs" and cfg.list_pattern == "/v/{n}"
    assert (kw["days"], kw["min_len"], kw["korean_only"]) == (7, 30, False)
    urls, kw = seen["url"]
    assert urls == [URL1] and "since" not in kw


def test_other_workspace_source_is_not_found(session, ws_a, ws_b, fake):
    src = news_source(session, ws_a)
    with pytest.raises(LookupError):
        run_source_once(session, ws_b, src.id)
    assert jobs.list_jobs(session, ws_a) == [] and fake.calls == []
