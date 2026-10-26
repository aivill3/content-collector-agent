"""수집 작업 API — 임시 SQLite 를 의존성 교체로 붙인다 (네트워크 없음)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.api.main import app
from app.core.timeutil import day_start_utc, display_today
from app.db import engine as db
from app.db.models import CollectionJob
from app.db.seed import seed
from app.domain.enums import JobStatus, SourceType
from app.repositories import jobs, sources
from app.repositories.workspaces import DEFAULT_WORKSPACE_ID
from app.services import collection_service
from app.services.collection_service import CollectResult
from app.workers import background, runner
from tests.test_db import article, news_source, run

WS = DEFAULT_WORKSPACE_ID
STATS = {"검색": 60, "중복 제거 후": 60, "기간 필터 후": 54, "신규": 54, "본문 확보": 53, "정제 통과": 53}


@pytest.fixture
def client(session):
    seed(session)
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def failed(session, ws, source_id, message="robots.txt 가 막았습니다") -> CollectionJob:
    job = jobs.create_job(session, ws, source_id, "scheduled")
    jobs.mark_running(session, ws, job.id)
    jobs.fail_job(session, ws, job.id, message)
    session.commit()
    return job


def test_lists_newest_first_with_stages(client, session):
    src = news_source(session, WS)
    ok, _ = run(session, WS, src.id, CollectResult(articles=[article()], stats=STATS))
    bad = failed(session, WS, src.id)

    body = client.get("/api/jobs").json()
    assert [j["id"] for j in body] == [bad.id, ok.id]
    first, second = body[1], body[0]
    assert (first["sourceName"], first["sourceType"], first["trigger"], first["status"]) == \
        ("뉴스", "news_keyword", "manual", "success")
    assert first["collectedCount"] == 1 and first["stageCounts"] == STATS
    assert first["queuedAt"].endswith("+09:00") and first["durationSec"] is not None
    assert (second["status"], second["trigger"], second["errorMessage"]) == ("failed", "scheduled", "robots.txt 가 막았습니다")
    assert second["stageCounts"] == {}


def test_filters_by_source_status_and_days(client, session):
    news = news_source(session, WS)
    board = sources.create_source(session, WS, name="게시판", type=SourceType.BOARD,
                                  config={"listUrl": "https://board.example.com/list"})
    ok, _ = run(session, WS, news.id, CollectResult(articles=[article()]))
    bad = failed(session, WS, board.id)
    old = failed(session, WS, board.id)
    old.queued_at = day_start_utc(display_today() - timedelta(days=10))
    session.add(old)
    session.commit()

    ids = lambda **q: [j["id"] for j in client.get("/api/jobs", params=q).json()]
    assert ids(sourceId=board.id) == [old.id, bad.id]
    assert ids(status="failed") == [old.id, bad.id]
    assert ids(status="success") == [ok.id]
    assert ids(days=7) == [bad.id, ok.id]
    assert ids(days=7, sourceId=board.id, status="failed") == [bad.id]
    assert ids(limit=1) == [old.id]
    assert client.get("/api/jobs", params={"status": "fail"}).status_code == 422


def test_other_workspace_jobs_are_hidden(client, session, ws_b):
    src = news_source(session, ws_b)
    run(session, ws_b, src.id, CollectResult(articles=[article()]))
    assert client.get("/api/jobs").json() == []
    assert client.get("/api/jobs", params={"sourceId": src.id}).json() == []


@pytest.fixture
def submitted(monkeypatch):
    """background.submit 대역 — 실행하지 않고 받은 작업만 기록한다."""
    calls = []
    monkeypatch.setattr(background, "submit", lambda ws, ids: calls.append((ws, list(ids))))
    return calls


def test_collect_now_queues_and_submits(client, session, submitted):
    a, b = news_source(session, WS), news_source(session, WS)
    session.commit()
    res = client.post("/api/jobs", json={"sourceIds": [a.id]})
    assert res.status_code == 202
    body = res.json()
    assert (body["queued"], body["skipped"]) == (1, 0) and submitted == [(WS, body["jobIds"])]
    assert [j["status"] for j in client.get("/api/jobs").json()] == ["queued"]

    # 전체 — a 는 이미 대기 중이라 건너뛴다
    body = client.post("/api/jobs", json={}).json()
    assert (body["queued"], body["skipped"]) == (1, 1)
    assert jobs.get_job(session, WS, body["jobIds"][0]).source_id == b.id


def test_collect_now_unknown_source_is_404(client, session, submitted, ws_b):
    other = news_source(session, ws_b)
    session.commit()
    assert client.post("/api/jobs", json={"sourceIds": [other.id]}).status_code == 404
    assert client.post("/api/jobs", json={"sourceIds": [999]}).status_code == 404
    assert submitted == [] and client.get("/api/jobs").json() == []


def test_background_runs_job_and_recovers_interrupted(session, monkeypatch):
    seed(session)
    monkeypatch.setattr(db, "engine", session.get_bind())
    monkeypatch.setattr(collection_service, "collect_keywords",
                        lambda keywords, **kw: CollectResult(articles=[article()], stats={"검색": 1}))
    src = news_source(session, WS)
    queued = runner.queue_sources(session, WS, [src.id]).jobs[0]
    session.commit()
    background._run(WS, queued.id)                   # submit 이 스레드에서 부르는 함수
    session.expire_all()
    assert jobs.get_job(session, WS, queued.id).status == JobStatus.SUCCESS

    stuck = runner.queue_sources(session, WS, [src.id]).jobs[0]
    session.commit()
    background.recover_interrupted()
    session.expire_all()
    job = jobs.get_job(session, WS, stuck.id)
    assert job.status == JobStatus.FAILED and job.error_message == background.INTERRUPTED
