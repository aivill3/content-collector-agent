"""DB 를 쓰는 CLI. 모두 기본 워크스페이스가 대상이다. backend/ 에서 실행한다.

    alembic upgrade head && python -m app.db.seed      # 처음 한 번

    python -m app.cli add-news-source --name 태권도뉴스 --keyword 태권도 --keyword 국기원 --count 30 --days 3
    python -m app.cli run-source 1
    python -m app.cli list-contents --limit 20
    python -m app.cli reclean-contents --dry-run    # 정제 규칙을 고친 뒤 저장된 글에 다시 적용
    python -m app.cli delete-content 6

DB 없이 수집만 확인하고 파일로 남기려면 backend/cli.py 를 쓴다.
"""
import argparse
import sys

from sqlmodel import Session

from app.core import logger
from app.core.timeutil import to_display
from app.db.engine import engine
from app.domain.enums import JobStatus, JobTrigger, SourceType
from app.repositories import contents, sources
from app.repositories.workspaces import DEFAULT_WORKSPACE_ID, get_workspace
from app.workers.reclean import reclean_contents
from app.workers.runner import run_source_once


def _fmt(dt) -> str:
    return to_display(dt).strftime("%Y-%m-%d %H:%M") if dt else "날짜 불명"


def _workspace(session: Session):
    ws = get_workspace(session, DEFAULT_WORKSPACE_ID)
    if ws is None:
        sys.exit("기본 워크스페이스가 없습니다 — alembic upgrade head 후 python -m app.db.seed 를 실행하세요")
    return ws


def add_news_source(session: Session, args) -> int:
    ws = _workspace(session)
    src = sources.create_source(
        session, ws.id, name=args.name, type=SourceType.NEWS_KEYWORD,
        config={"count": args.count, "sort": args.sort, "days": args.days}, keywords=args.keyword,
    )
    session.commit()
    kws = [k.keyword for k in sources.list_keywords(session, ws.id, src.id)]
    print(f"소스 {src.id} 등록: {src.name} — 키워드 {', '.join(kws)} · 키워드당 {args.count}건 · 최근 {args.days}일")
    return 0


def run_source(session: Session, args) -> int:
    ws = _workspace(session)
    try:
        job = run_source_once(session, ws.id, args.source_id, JobTrigger.MANUAL)
    except LookupError as e:
        print(e)
        return 1
    print(f"\n작업 {job.id}: {job.status} ({job.duration_sec or 0:.1f}초)")
    for stage, n in job.stage_counts.items():
        print(f"  {stage:<10} {n}")
    print(f"  신규 저장   {job.collected_count}")
    if job.error_message:
        print(f"  오류: {job.error_message}")
    return 0 if job.status == JobStatus.SUCCESS else 1


def list_contents(session: Session, args) -> int:
    ws = _workspace(session)
    rows, total = contents.search_contents(session, ws.id, contents.ContentQuery(), size=args.limit)
    keywords = contents.keywords_for(session, ws.id, [c.id for c in rows])
    print(f"콘텐츠 {total}건 중 최근 수집 {len(rows)}건 (시각: DISPLAY_TZ)\n")
    for c in rows:
        print(f"[{c.id}] {c.title[:60]}")
        kw = f" · 키워드 {', '.join(keywords[c.id])}" if keywords[c.id] else ""
        print(f"     {c.publisher or '-'} · 발행 {_fmt(c.published_at)} · 수집 {_fmt(c.collected_at)}"
              f" · {c.body_length}자{kw}")
    return 0


def reclean(session: Session, args) -> int:
    ws = _workspace(session)
    result = reclean_contents(session, ws.id, dry_run=args.dry_run)
    verb = "바뀔" if args.dry_run else "바뀐"
    note = " (적용 안 함 — --dry-run)" if args.dry_run else ""
    print(f"콘텐츠 {result.checked}건 중 {verb} 글 {len(result.changed)}건{note}\n")
    for c in result.changed:
        mark = f"  ← 최소 {c.min_length}자 미만" if c.after < c.min_length else ""
        print(f"[{c.content_id}] {c.title[:50]}  {c.before}자 → {c.after}자{mark}")
    if result.short:
        print(f"\n최소 길이 미만 {len(result.short)}건은 지우지 않았습니다 (수집 때라면 저장되지 않았을 글).")
    return 0


def delete_content(session: Session, args) -> int:
    ws = _workspace(session)
    c = contents.get_content(session, ws.id, args.content_id)
    if c is None:
        print(f"콘텐츠 {args.content_id} 가 없습니다")
        return 1
    title = c.title
    contents.delete_content(session, ws.id, args.content_id)
    session.commit()
    print(f"콘텐츠 {args.content_id} 삭제: {title}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.cli", description="콘텐츠 수집 (DB)")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add-news-source", help="뉴스 키워드 소스 등록")
    a.add_argument("--name", required=True)
    a.add_argument("--keyword", action="append", required=True, help="여러 번 줄 수 있다")
    a.add_argument("--count", type=int, default=30, help="키워드당 검색 건수 (1~1000)")
    a.add_argument("--sort", default="sim", choices=["sim", "date"])
    a.add_argument("--days", type=int, default=3, help="최근 N일 발행분")

    r = sub.add_parser("run-source", help="소스를 한 번 수집해 DB 에 저장")
    r.add_argument("source_id", type=int)

    ls = sub.add_parser("list-contents", help="최근 수집한 콘텐츠")
    ls.add_argument("--limit", type=int, default=20)

    rc = sub.add_parser("reclean-contents", help="저장된 글을 지금의 정제 규칙으로 다시 정제")
    rc.add_argument("--dry-run", action="store_true", help="바꾸지 않고 바뀔 글만 보여 준다")

    d = sub.add_parser("delete-content", help="콘텐츠 하나 삭제 (키워드 기록도 함께)")
    d.add_argument("content_id", type=int)

    args = p.parse_args(argv)
    logger.setup(to_file=True, prefix=args.cmd)
    handler = {"add-news-source": add_news_source, "run-source": run_source, "list-contents": list_contents,
               "reclean-contents": reclean, "delete-content": delete_content}
    with Session(engine) as session:
        return handler[args.cmd](session, args)


if __name__ == "__main__":
    sys.exit(main())
