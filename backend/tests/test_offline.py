"""네트워크 없이 돌리는 테스트. python -m pytest tests"""
from datetime import datetime

from app.extractors.cleaner import clean_all, clean_content
from app.processors.date_filter import filter_recent
from app.domain.content import Article
from app.processors.deduplication import canonical_url, dedupe
from app.core.config import KST
from app.collectors.board import BoardConfig, _posts_auto, _posts_manual, detect_groups, parse_board_date

from bs4 import BeautifulSoup

BASE = "https://example.com/bbs/board.php?bo_table=notice"

GNUBOARD_LIKE = """
<html><body>
<header><nav>
  <a href="/bbs/board.php?bo_table=notice">공지사항</a>
  <a href="/bbs/board.php?bo_table=free">자유게시판</a>
  <a href="/page/1">회사소개</a><a href="/page/2">오시는 길</a><a href="/page/3">연혁</a>
</nav></header>
<table id="bo_list"><tbody>
  <tr><td>공지</td><td class="td_subject"><a href="/bbs/board.php?bo_table=notice&wr_id=1">홈페이지 이용 안내</a></td><td>2025.01.02</td></tr>
  <tr><td>103</td><td class="td_subject"><a href="/bbs/board.php?bo_table=notice&wr_id=103">2026년 하반기 승단심사 일정 안내</a>
      <a href="/bbs/board.php?bo_table=notice&wr_id=103#c">3</a></td><td>09-25</td></tr>
  <tr><td>102</td><td class="td_subject"><a href="/bbs/board.php?bo_table=notice&wr_id=102">추석 연휴 휴관 안내</a></td><td>2026-09-20</td></tr>
  <tr><td>101</td><td class="td_subject"><a href="/bbs/board.php?bo_table=notice&wr_id=101">9월 정기 대회 결과 발표</a></td><td>26.09.10</td></tr>
</tbody></table>
<div class="pg"><a href="?bo_table=notice&page=1">1</a><a href="?bo_table=notice&page=2">2</a><a href="?bo_table=notice&page=3">3</a></div>
<footer><a href="/policy/1">개인정보처리방침</a></footer>
</body></html>
"""

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=KST)


def test_parse_board_date():
    assert parse_board_date("2026.09.20", NOW).startswith("2026-09-20")
    assert parse_board_date("26-09-10", NOW).startswith("2026-09-10")
    assert parse_board_date("09-25", NOW).startswith("2026-09-25")
    assert parse_board_date("14:32", NOW).startswith("2026-09-26T14:32")
    assert parse_board_date("3시간 전", NOW).startswith("2026-09-26T09:00")
    assert parse_board_date("12-30", datetime(2027, 1, 3, tzinfo=KST)).startswith("2026-12-30")
    assert parse_board_date("조회 152", NOW) == ""


def test_auto_detect_picks_post_links_not_menu_or_paging():
    shape, links = detect_groups(GNUBOARD_LIKE, BASE)[0]
    assert "wr_id={n}" in shape
    assert len(links) == 4
    # 제목 링크와 댓글수 링크가 같은 글이면 하나로 합치고 긴 텍스트를 제목으로
    titles = [t for _, t in links]
    assert "2026년 하반기 승단심사 일정 안내" in titles and "3" not in titles


def test_auto_posts_with_dates_and_notice_filter():
    posts = _posts_auto(GNUBOARD_LIKE, BASE, BoardConfig(list_url=BASE, exclude_notice=True))
    assert [p.title for p in posts][0] == "2026년 하반기 승단심사 일정 안내"
    assert len(posts) == 3
    assert posts[1].published.startswith("2026-09-20")


def test_manual_selectors():
    cfg = BoardConfig(list_url=BASE, item_selector="#bo_list tbody tr",
                      link_selector="td.td_subject a", date_selector="td:last-child")
    posts = _posts_manual(BeautifulSoup(GNUBOARD_LIKE, "lxml"), BASE, cfg)
    assert len(posts) == 4
    assert posts[3].url == "https://example.com/bbs/board.php?bo_table=notice&wr_id=101"
    assert posts[3].published.startswith("2026-09-10")


def test_canonical_and_dedupe_keep_board_ids():
    a = "https://Example.com/view.php?no=12&utm_source=x"
    b = "https://example.com/view.php?no=12/"
    assert canonical_url(a) == canonical_url("https://example.com/view.php?no=12")
    items = [Article(title="문의", url="https://e.com/v?no=1"), Article(title="문의", url="https://e.com/v?no=2")]
    assert len(dedupe(items, by_title=False)) == 2
    assert len(dedupe(items)) == 1


def test_filter_recent_keeps_unknown_dates():
    arts = [Article(published="2026-01-01T00:00:00+09:00"), Article(published="")]
    assert len(filter_recent(arts, days=3)) == 1


def test_cleaner_removes_boilerplate():
    body = ("국기원은 25일 하반기 승단심사 일정을 발표했다. 심사는 10월부터 전국에서 진행된다.\n"
            "홍길동 기자 hong@example.com\n무단전재 및 재배포 금지")
    out = clean_content(body)
    assert "무단전재" not in out and "@" not in out and "승단심사" in out
    short = Article(title="t", body="짧은 글")
    assert clean_all([short], min_len=100) == []
    assert len(clean_all([Article(title="t", body="짧은 공지 글입니다. 확인 바랍니다.")], min_len=10)) == 1


def test_naver_search_parses_and_pages(monkeypatch):
    from app.collectors import news as naver_news
    monkeypatch.setattr(naver_news, "NAVER_CLIENT_ID", "id")
    monkeypatch.setattr(naver_news, "NAVER_CLIENT_SECRET", "secret")
    calls = []

    def fake(query, display, start, sort):
        calls.append((display, start))
        n = min(display, 150 - (start - 1))
        return [{"title": f"<b>{query}</b> 기사 {start + i}", "originallink": f"https://news.example/{start + i}",
                 "link": "", "description": "요약 &quot;인용&quot;", "pubDate": "Fri, 25 Sep 2026 09:07:13 +0900"}
                for i in range(n)]

    monkeypatch.setattr(naver_news, "_request", fake)
    r = naver_news.search("태권도", count=150)
    assert calls == [(100, 1), (50, 101)]
    assert len(r.articles) == 150 and r.articles[0].title == "태권도 기사 1"
    assert r.articles[0].summary == '요약 "인용"'
    assert r.articles[0].published == "2026-09-25T09:07:13+09:00"


def test_extract_body_from_html():
    from app.extractors.article import extract_body
    html = "<html><head><title>대회 결과</title></head><body><article>" + \
        "<p>" + "춘천에서 열린 국제 태권도 대회가 25일 막을 내렸다. 한국 대표팀은 종합 우승을 차지했다. " * 6 + "</p>" + \
        "</article></body></html>"
    a = extract_body(Article(url="https://x.example/1"), html=html)
    assert "종합 우승" in a.body


def test_collectors_share_interface():
    from app.collectors.base import Collector
    from app.collectors.board import BoardCollector
    from app.collectors.news import NewsCollector
    from app.collectors.website import WebsiteCollector
    assert all(issubclass(c, Collector) for c in (BoardCollector, NewsCollector, WebsiteCollector))
    posts = WebsiteCollector(["https://a.example/1", "https://a.example/1/", " ", "https://a.example/2"]).collect()
    assert [p.search_rank for p in posts] == [1, 2] and posts[0].source == "website"


def test_news_collector_keeps_raw(monkeypatch):
    from app.collectors import news
    from app.collectors.news import NewsCollector, SearchResult
    monkeypatch.setattr(news, "search_many", lambda kws, count, sort: [
        SearchResult(keyword=k, articles=[Article(title=k, url=f"https://n.example/{k}")], raw=[{"k": k}]) for k in kws])
    c = NewsCollector(["가", "나"])
    assert [a.title for a in c.collect()] == ["가", "나"]
    assert c.raw == {"가": [{"k": "가"}], "나": [{"k": "나"}]}
