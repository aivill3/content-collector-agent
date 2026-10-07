"""터미널에서 수집을 돌려 보는 진입점. API 없이 수집 로직만 확인할 때 쓴다.

backend/ 폴더에서 실행한다.

  # 키워드 뉴스 수집
  python cli.py keyword 태권도 국기원 --count 30 --days 3

  # 게시판 수집 (자동 탐지)
  python cli.py board "https://example.com/bbs/board.php?bo_table=notice" --page-param page --pages 2

  # 게시판 수집 (수동 설정)
  python cli.py board "https://example.com/bbs/board.php?bo_table=notice" \\
      --item "#bo_list tbody tr" --link "td.td_subject a" --body "#bo_v_con"

  # 글 URL 몇 개의 본문만
  python cli.py url https://site/a/1 https://site/b/2

  # 자동 탐지가 무엇을 잡는지만 확인 (본문은 받지 않음)
  python cli.py detect "https://example.com/bbs/board.php?bo_table=notice"

결과는 data/output/ 에 JSON 과 CSV 로 남는다.
"""
import argparse
import csv
import json
import sys
from datetime import datetime

from app.core import logger
from app.extractors.article import fetch_html
from app.domain.content import Article
from app.services.collection_service import CollectResult, collect_board, collect_keywords, collect_urls
from app.core.config import BASE_DIR, DISPLAY_TZ
from app.collectors.board import BoardConfig, detect_groups, list_posts

OUT_DIR = BASE_DIR / "data" / "output"


def save(result: CollectResult, prefix: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(DISPLAY_TZ).strftime("%Y%m%d_%H%M%S")
    rows = [a.to_dict() for a in result.articles]
    json_path = OUT_DIR / f"{prefix}_{stamp}.json"
    json_path.write_text(json.dumps(
        {"stats": result.stats, "latest_published": result.latest_published, "articles": rows},
        ensure_ascii=False, indent=2,
    ), encoding="utf-8")
    if result.raw:
        (OUT_DIR / f"{prefix}_{stamp}_raw.json").write_text(
            json.dumps(result.raw, ensure_ascii=False, indent=2), encoding="utf-8")
    if rows:
        csv_path = OUT_DIR / f"{prefix}_{stamp}.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:   # 엑셀 한글 깨짐 방지
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"\n저장: {json_path}")


def print_summary(articles: list[Article]) -> None:
    for a in articles[:20]:
        body = (a.body_clean or a.body).replace("\n", " ")
        print(f"- [{a.date or '날짜 불명'}] {a.title[:50]}")
        print(f"    {a.url}")
        if body:
            print(f"    {body[:80]}...")
    if len(articles) > 20:
        print(f"... 외 {len(articles) - 20}건")


def _board_config(args) -> BoardConfig:
    return BoardConfig(
        list_url=args.url,
        item_selector=args.item or "",
        link_selector=args.link or "a[href]",
        title_selector=args.title or "",
        date_selector=args.date or "",
        body_selector=args.body or "",
        page_param=args.page_param or "",
        max_pages=args.pages,
        max_items=args.max_items,
        include_pattern=args.include or "",
        list_pattern=args.pattern or "",
        exclude_notice=args.exclude_notice,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="콘텐츠 수집 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("keyword", help="키워드로 네이버 뉴스 수집")
    k.add_argument("keywords", nargs="+")
    k.add_argument("--count", type=int, default=30, help="키워드당 검색 건수 (최대 1000)")
    k.add_argument("--sort", default="sim", choices=["sim", "date"])
    k.add_argument("--days", type=int, default=3, help="최근 N일 발행분만")
    k.add_argument("--any-language", action="store_true", help="비한국어 기사도 남김")

    u = sub.add_parser("url", help="글 URL 들의 본문 수집")
    u.add_argument("urls", nargs="+")
    u.add_argument("--min-len", type=int, default=30)
    u.add_argument("--any-language", action="store_true")

    for name in ("board", "detect"):
        b = sub.add_parser(name, help="게시판 수집" if name == "board" else "게시판 자동 탐지 결과만 확인")
        b.add_argument("url")
        b.add_argument("--item", help="목록 한 줄 CSS 선택자 (비우면 자동 탐지)")
        b.add_argument("--link", help="줄 안의 글 링크 선택자")
        b.add_argument("--title", help="줄 안의 제목 선택자")
        b.add_argument("--date", help="줄 안의 날짜 선택자")
        b.add_argument("--body", help="글 페이지의 본문 영역 선택자")
        b.add_argument("--page-param", help="페이지 번호 쿼리 이름 (예: page)")
        b.add_argument("--pages", type=int, default=1)
        b.add_argument("--max-items", type=int, default=50)
        b.add_argument("--include", help="글 URL 이 맞아야 하는 정규식")
        b.add_argument("--pattern", help="자동 탐지에서 쓸 후보 묶음 (detect 가 보여 준 URL 모양). 비우면 1순위")
        b.add_argument("--exclude-notice", action="store_true", help="'공지' 줄 제외")
        b.add_argument("--days", type=int, default=None)
        b.add_argument("--min-len", type=int, default=30)
        b.add_argument("--any-language", action="store_true")

    args = p.parse_args(argv)
    logger.setup(to_file=True, prefix=args.cmd)

    if args.cmd == "keyword":
        result = collect_keywords(
            args.keywords, count=args.count, sort=args.sort, days=args.days,
            korean_only=not args.any_language,
        )
        print_summary(result.articles)
        save(result, "keyword")

    elif args.cmd == "board":
        result = collect_board(
            _board_config(args), days=args.days, min_len=args.min_len,
            korean_only=not args.any_language,
        )
        print_summary(result.articles)
        save(result, "board")

    elif args.cmd == "url":
        result = collect_urls(args.urls, min_len=args.min_len, korean_only=not args.any_language)
        print_summary(result.articles)
        save(result, "url")

    elif args.cmd == "detect":
        cfg = _board_config(args)
        if not cfg.item_selector:
            html = fetch_html(cfg.list_url)
            if not html:
                print("목록 페이지를 받지 못했습니다")
                return 1
            print("\n[자동 탐지 후보 묶음] 맨 위 묶음이 게시글 목록으로 채택됩니다")
            for shape, links in detect_groups(html, cfg.list_url)[:5]:
                print(f"\n  {shape}  ({len(links)}건)")
                for url, text in links[:3]:
                    print(f"     {text[:40]}  →  {url}")
        print("\n[채택된 글 목록]")
        print_summary(list_posts(cfg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
