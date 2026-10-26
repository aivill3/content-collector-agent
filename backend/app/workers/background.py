"""API 의 '지금 수집' — 대기 작업을 서버 프로세스 안의 스레드 하나에서 차례로 실행한다.

    route: runner.queue_sources → 커밋 → submit(job_ids)  →  (스레드) runner.run_job

스케줄러·Celery 가 생기기 전까지의 임시 실행기다. 그때는 submit 만 Celery 태스크 등록으로 바꾼다.
- 작업은 한 번에 하나씩 돈다. 동시에 돌면 같은 URL 을 두 작업이 함께 저장하려 할 수 있고
  (seen_urls 는 실행 시작 때 읽는다), SQLite 는 쓰기가 겹치면 잠긴다.
- 실행 중에 서버가 꺼지면 작업이 대기·실행 중으로 남아 그 소스를 다시 수집할 수 없다.
  서버가 시작할 때 recover_interrupted 가 그런 작업을 실패로 끝낸다.
  CLI 로 실행 중인 작업도 함께 실패로 바뀌므로, CLI 수집 도중에는 API 서버를 (다시) 띄우지 않는다.
"""
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlmodel import Session

from app.core.logger import get_logger
from app.db import engine as db
from app.repositories import jobs, workspaces
from app.workers import runner

log = get_logger(__name__)

INTERRUPTED = "서버가 다시 시작되어 작업이 중단되었습니다"

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="collect")


def submit(workspace_id: uuid.UUID, job_ids: list[int]) -> None:
    """대기 작업을 실행 순서에 넣는다. 바로 돌아온다."""
    for job_id in job_ids:
        _executor.submit(_run, workspace_id, job_id)


def _run(workspace_id: uuid.UUID, job_id: int) -> None:
    try:
        with Session(db.engine) as session:
            runner.run_job(session, workspace_id, job_id)
    except Exception:           # run_job 은 수집 실패를 job 에 남긴다. 여기 오는 건 그 밖의 오류다
        log.exception(f"작업 {job_id} 실행 오류")


def recover_interrupted() -> None:
    """서버 시작 시 — 이전 프로세스에서 끝나지 못한 작업을 실패로 끝낸다."""
    with Session(db.engine) as session:
        for ws in workspaces.list_workspace_ids(session):
            ids = jobs.fail_interrupted(session, ws, INTERRUPTED)
            if ids:
                log.warning(f"중단된 작업을 실패로 끝냄: {ids}")
        session.commit()
