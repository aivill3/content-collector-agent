"""수집 작업 (JOB-001) — 이력 조회와 지금 수집. 모든 라우트가 get_current_workspace 를 거친다.

POST 는 '지금 수집'(FN-COL-001) — 대기 작업만 만들어 커밋하고 바로 답한다.
실행은 workers/background 가 서버 안 스레드에서 차례로 한다. 진행은 GET 으로 확인한다.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api.deps import get_current_workspace, get_session, not_found
from app.core.timeutil import days_to_utc_range, recent_days
from app.db.models import Workspace
from app.repositories import jobs as repo
from app.repositories import sources
from app.schemas.collect import CollectRequest, CollectResponse
from app.schemas.jobs import JobListItem, JobListParams
from app.workers import background, runner

router = APIRouter(prefix="/jobs", tags=["수집 작업"])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[JobListItem])
def list_jobs(params: Annotated[JobListParams, Query()], ws: WorkspaceDep, session: SessionDep):
    """최근 작업부터 limit 건."""
    queued_range = days_to_utc_range(*recent_days(params.days)) if params.days else None
    rows = repo.list_jobs(session, ws.id, source_id=params.source_id, status=params.status,
                          queued_range=queued_range, limit=params.limit)
    by_id = {s.id: s for s in sources.list_sources(session, ws.id)}
    return [JobListItem.of(j, by_id.get(j.source_id)) for j in rows]


@router.post("", response_model=CollectResponse, status_code=status.HTTP_202_ACCEPTED)
def collect_now(body: CollectRequest, ws: WorkspaceDep, session: SessionDep):
    """소스를 지금 수집한다. sourceIds 가 없으면 사용 중인 소스 전부. 이미 대기·실행 중인 소스는 건너뛴다."""
    try:
        result = runner.queue_sources(session, ws.id, body.source_ids)
    except LookupError:
        raise not_found("소스")
    session.commit()
    job_ids = [j.id for j in result.jobs]
    background.submit(ws.id, job_ids)
    return CollectResponse(job_ids=job_ids, queued=len(job_ids), skipped=len(result.skipped))
