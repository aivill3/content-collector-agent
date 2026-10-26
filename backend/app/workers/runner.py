"""소스 1회 실행 — 수집(services)과 저장(repositories)을 묶는 유일한 곳.

    queue_sources: job 생성(queued, 커밋은 부르는 쪽)
    run_job:       running (커밋) → 유형별 collect_* → save_collect_result (success, 커밋)
                                          │                  └ 키워드 분석 (workers/analysis, 커밋)
                                          └ 예외 → 롤백 → fail_job (failed, 커밋)

CLI(app/cli.py)는 run_source_once(대기 작업 생성 + 바로 실행)를, API 의 '지금 수집'은
queue_sources 로 대기 작업을 만들고 workers/background 가 run_job 을 부른다.
나중의 스케줄러·Celery 도 같은 두 함수를 쓴다. 수집 서비스는 여전히 저장하지 않는다 (CLAUDE.md 설계 원칙).

- exclude_urls 는 워크스페이스에 이미 저장된 URL(seen_urls)로 채운다.
- 소스의 last_published_at 이 있으면 since 로 넘긴다. 조회 기간(days)보다 수집이 오래 멈췄을 때
  그 공백까지 창을 넓힌다 (filter_recent 는 둘 중 이른 쪽을 쓴다).
- 수집 중 어떤 예외가 나도 job 은 failed 로 남고 소스 상태가 갱신된다. 예외는 다시 던지지 않는다.
- 저장이 끝나면 분석 안 된 글을 분석한다. 분석이 실패해도 job 은 success 로 둔다 (저장은 끝났다) —
  남은 글은 다음 실행이나 `python -m app.cli analyze-contents` 가 분석한다.
"""
import uuid
from dataclasses import dataclass, field

from sqlmodel import Session

from app.core.logger import get_logger
from app.db.models import CollectionJob, Source
from app.domain.enums import JobStatus, JobTrigger, SourceType
from app.repositories import contents, jobs, sources
from app.schemas.source_config import BoardSourceConfig, NewsKeywordConfig, UrlSourceConfig
from app.services import collection_service
from app.services.collection_service import CollectResult
from app.workers import analysis

log = get_logger(__name__)


def _collect(session: Session, workspace_id: uuid.UUID, source: Source) -> CollectResult:
    """소스 유형에 맞는 수집 함수를 부른다. 저장은 하지 않는다."""
    cfg = sources.source_config(source)
    common = dict(
        exclude_urls=contents.seen_urls(session, workspace_id),
        min_len=source.min_body_length,
        korean_only=not source.allow_non_korean,
    )
    if source.type == SourceType.NEWS_KEYWORD:
        assert isinstance(cfg, NewsKeywordConfig)
        keywords = [k.keyword for k in sources.list_keywords(session, workspace_id, source.id)]
        if not keywords:
            raise ValueError("검색 키워드가 없는 뉴스 소스입니다")
        return collection_service.collect_keywords(
            keywords, count=cfg.count, sort=cfg.sort, days=cfg.days, since=source.last_published_at, **common)
    if source.type == SourceType.BOARD:
        assert isinstance(cfg, BoardSourceConfig)
        return collection_service.collect_board(
            cfg.to_board_config(), days=cfg.days, since=source.last_published_at, **common)
    if source.type == SourceType.URL:
        assert isinstance(cfg, UrlSourceConfig)
        return collection_service.collect_urls(cfg.urls, **common)
    raise ValueError(f"알 수 없는 소스 유형: {source.type}")


@dataclass
class QueueResult:
    jobs: list[CollectionJob] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)   # 이미 대기·실행 중이라 건너뛴 소스 id


def queue_sources(
    session: Session,
    workspace_id: uuid.UUID,
    source_ids: list[int] | None = None,
    trigger: JobTrigger = JobTrigger.MANUAL,
) -> QueueResult:
    """소스마다 대기(queued) 작업을 만든다. 실행은 run_job 이 한다. 커밋은 부르는 쪽이.

    source_ids 가 None 이면 사용 중인 소스 전부. 이미 대기·실행 중인 작업이 있는 소스는 건너뛴다.
    없는 소스(다른 워크스페이스 것 포함)가 하나라도 있으면 아무것도 만들지 않고 LookupError.
    """
    if source_ids is None:
        targets = sources.list_sources(session, workspace_id, active_only=True)
    else:
        targets = []
        for source_id in dict.fromkeys(source_ids):     # 순서 유지, 중복 제거
            source = sources.get_source(session, workspace_id, source_id)
            if source is None:
                raise LookupError(f"소스 {source_id} 가 없습니다")
            targets.append(source)
    busy = jobs.active_source_ids(session, workspace_id)
    result = QueueResult()
    for source in targets:
        if source.id in busy:
            result.skipped.append(source.id)
        else:
            result.jobs.append(jobs.create_job(session, workspace_id, source.id, trigger))
    return result


def run_job(session: Session, workspace_id: uuid.UUID, job_id: int) -> CollectionJob:
    """대기 작업 하나를 실행해 저장하고 끝난 job 을 돌려준다 (status 로 성공·실패 확인).

    작업이 없거나 다른 워크스페이스 것이면 LookupError. 대기 상태가 아니면(이미 실행했다) 그대로 돌려준다.
    """
    job = jobs.get_job(session, workspace_id, job_id)
    if job is None:
        raise LookupError(f"작업 {job_id} 가 없습니다")
    if job.status != JobStatus.QUEUED:
        log.warning(f"대기 상태가 아닌 작업은 실행하지 않습니다: 작업 {job_id} ({job.status})")
        return job
    source = sources.get_source(session, workspace_id, job.source_id)
    if not source.is_active:
        log.warning(f"비활성 소스를 실행합니다: {source.name} ({source.id})")

    jobs.mark_running(session, workspace_id, job_id)
    session.commit()            # 수집 중에도 '실행 중'이 보이고, 아래 롤백에도 job 이 남는다
    log.info(f"수집 시작: {source.name} (소스 {source.id}, 작업 {job_id})")

    try:
        result = _collect(session, workspace_id, source)
        saved = contents.save_collect_result(session, workspace_id, job_id, result)
        session.commit()
        log.info(f"수집 완료: 작업 {job_id} — 신규 {saved.new_contents}건, 키워드 기록 {saved.new_hits}건")
    except Exception as e:      # 어떤 실패든 job 에 남긴다
        session.rollback()
        message = f"{type(e).__name__}: {e}"
        log.exception(f"수집 실패: 작업 {job_id} — {message}")
        jobs.fail_job(session, workspace_id, job_id, message)
        session.commit()
    else:
        try:
            analysis.analyze_pending(session, workspace_id)
        except Exception:
            session.rollback()
            log.exception(f"키워드 분석 실패: 작업 {job_id} — 수집 결과는 저장됐다")

    job = jobs.get_job(session, workspace_id, job_id)
    session.refresh(job)
    return job


def run_source_once(
    session: Session,
    workspace_id: uuid.UUID,
    source_id: int,
    trigger: JobTrigger = JobTrigger.MANUAL,
) -> CollectionJob:
    """소스를 바로 한 번 수집한다 (CLI). 대기 작업을 만들어 커밋하고 run_job 으로 실행한다.

    소스가 없거나 다른 워크스페이스 것이면 LookupError (job 을 만들 수 없다).
    대기·실행 중인 작업이 있어도 실행한다 — 건너뛰기는 queue_sources(API)의 일이다.
    """
    if sources.get_source(session, workspace_id, source_id) is None:
        raise LookupError(f"소스 {source_id} 가 없습니다")
    job = jobs.create_job(session, workspace_id, source_id, trigger)
    session.commit()
    return run_job(session, workspace_id, job.id)
