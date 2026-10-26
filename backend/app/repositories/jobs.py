"""수집 작업(collection_jobs) 기록.

    create_job → mark_running → (수집) → contents.save_collect_result  (성공, 작업 마무리까지)
                                       └→ fail_job                     (수집 자체가 실패)

이 순서로 부르는 실행 함수는 워커 단계에서 만든다.
"""
import uuid
from datetime import datetime

from sqlmodel import Session, col

from app.db.models import CollectionJob, Source
from app.db.types import utcnow
from app.domain.enums import JobStatus, JobTrigger
from app.repositories.scope import get_scoped, scoped_select
from app.repositories.sources import get_source


def create_job(session: Session, workspace_id: uuid.UUID, source_id: int, trigger: JobTrigger) -> CollectionJob:
    if get_source(session, workspace_id, source_id) is None:
        raise LookupError(f"소스 {source_id} 가 없습니다")
    job = CollectionJob(workspace_id=workspace_id, source_id=source_id, trigger=JobTrigger(trigger))
    session.add(job)
    session.flush()
    return job


def get_job(session: Session, workspace_id: uuid.UUID, job_id: int) -> CollectionJob | None:
    return get_scoped(session, CollectionJob, workspace_id, job_id)


def list_jobs(session: Session, workspace_id: uuid.UUID, *, source_id: int | None = None,
              status: JobStatus | None = None, queued_range: tuple[datetime, datetime] | None = None,
              limit: int = 50) -> list[CollectionJob]:
    """최근 작업부터. queued_range 는 UTC [start, end) — timeutil.days_to_utc_range 로 만든다."""
    stmt = scoped_select(CollectionJob, workspace_id)
    if source_id is not None:
        stmt = stmt.where(CollectionJob.source_id == source_id)
    if status is not None:
        stmt = stmt.where(CollectionJob.status == JobStatus(status))
    if queued_range is not None:
        start, end = queued_range
        stmt = stmt.where(col(CollectionJob.queued_at) >= start, col(CollectionJob.queued_at) < end)
    return list(session.exec(stmt.order_by(col(CollectionJob.id).desc()).limit(limit)))


ACTIVE = (JobStatus.QUEUED, JobStatus.RUNNING)


def active_source_ids(session: Session, workspace_id: uuid.UUID) -> set[int]:
    """대기·실행 중인 작업이 있는 소스."""
    stmt = scoped_select(CollectionJob, workspace_id).where(col(CollectionJob.status).in_(ACTIVE))
    return {j.source_id for j in session.exec(stmt)}


def fail_interrupted(session: Session, workspace_id: uuid.UUID, message: str) -> list[int]:
    """대기·실행 중으로 남은 작업을 실패로 끝낸다 (서버가 실행 도중 멈춘 경우). 끝낸 작업 id."""
    stmt = scoped_select(CollectionJob, workspace_id).where(col(CollectionJob.status).in_(ACTIVE))
    ids = [j.id for j in session.exec(stmt)]
    for job_id in ids:
        fail_job(session, workspace_id, job_id, message)
    return ids


def _require(session: Session, workspace_id: uuid.UUID, job_id: int) -> CollectionJob:
    job = get_job(session, workspace_id, job_id)
    if job is None:
        raise LookupError(f"작업 {job_id} 가 없습니다")
    return job


def mark_running(session: Session, workspace_id: uuid.UUID, job_id: int) -> CollectionJob:
    job = _require(session, workspace_id, job_id)
    job.status = JobStatus.RUNNING
    job.started_at = utcnow()
    session.add(job)
    session.flush()
    return job


def finish_job(
    session: Session,
    workspace_id: uuid.UUID,
    job_id: int,
    *,
    status: JobStatus,
    collected_count: int = 0,
    stage_counts: dict | None = None,
    error_message: str | None = None,
) -> CollectionJob:
    """작업을 끝내고 소스의 최근 실행 상태도 갱신한다."""
    job = _require(session, workspace_id, job_id)
    now = utcnow()
    job.status = JobStatus(status)
    job.finished_at = now
    job.duration_sec = (now - (job.started_at or job.queued_at)).total_seconds()
    job.collected_count = collected_count
    if stage_counts is not None:
        job.stage_counts = dict(stage_counts)
    job.error_message = error_message or None
    session.add(job)

    source = get_scoped(session, Source, workspace_id, job.source_id)
    source.last_collected_at = now
    source.last_status = job.status
    session.add(source)
    session.flush()
    return job


def fail_job(session: Session, workspace_id: uuid.UUID, job_id: int, error_message: str) -> CollectionJob:
    """수집이 예외로 끝났을 때. 받은 결과가 없으므로 저장할 콘텐츠도 없다."""
    return finish_job(session, workspace_id, job_id, status=JobStatus.FAILED, error_message=error_message)
