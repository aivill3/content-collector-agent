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


def test_cleaner_removes_title_and_subtitles():
    body = ("양궁 대표팀은 2일 일본 아이치현 오카자키 중앙종합공원 다목적광장에서 열릴 대회 양궁 리커브 남자 단체전에 출전한다.\n"
            "유도 대표팀도 같은 날 금메달에 도전한다.")
    # 제목 그대로 + 부제 3줄 (실측 뉴시스)
    title = "한국 금맥 캐기 계속…효자 종목 양궁·유도·태권도 출격[오늘의AG]"
    head = title + "\n양궁, 김제덕·강채영 필두로 금메달 싹쓸이 조준\n'파리 올림픽 銀' 유도 김민종, 첫 AG 정상 도전\n세대교체 이룬 태권도, 종주국 자존심 걸고 출격\n"
    assert clean_content(head + body, title) == body
    # 검색 API 제목이 '...' 로 잘린 경우 (실측 Mookas) — 본문 쪽은 전체 제목
    cut = "국기원 사범교육, 유럽 현장으로… 32개국 124명 독일서 ‘국제사범’ ..."
    full = "국기원 사범교육, 유럽 현장으로… 32개국 124명 독일서 ‘국제사범’ 연수 성료\nWTA, 독일체육대학교서 제126기 유럽 국제태권도사범 자격교육 실시\n"
    assert clean_content(full + body, cut) == body
    # 제목 뒤의 짧은 '문장'은 부제가 아니라 본문이다
    assert clean_content(title + "\n공로패는 이날 원장이 직접 전달했다.\n" + body, title).startswith("공로패는")
    # 제목 줄이 없으면 아무것도 지우지 않는다 (짧은 첫 줄이 있어도)
    assert clean_content("세대교체 이룬 태권도\n" + body, title).startswith("세대교체")
    assert clean_content(head + body) == clean_content(head + body, "")    # 제목을 안 주면 그대로


def test_cleaner_newsis_style_prefix():
    # 사진 기사: 대괄호 프리픽스 + 날짜 + 가려진 이메일 → 캡션 줄 전체 삭제 (실측 2026-10-01 뉴시스)
    caption = ("[도요하시(일본)=뉴시스] 이영환 기자 = 1일 오후(현지 시간) 일본 아이치현 도요하시 체육관에서 열린 "
               "2026 아이치·나고야 아시안게임 태권도 남자 개인 품새 메달 시상식에서 금메달을 획득한 한국 윤규성이 "
               "기념촬영을 하고 있다. 2026.10.01. [email protected]")
    assert clean_content(caption) == ""
    assert clean_content(caption.replace("[email protected]", "photo@newsis.com")) == ""
    assert clean_all([Article(title="t", body=caption)], min_len=100) == []
    # 기사 리드: 프리픽스만 벗기고 본문은 남긴다
    lead = "[서울=뉴시스] 김철수 기자 = 국기원은 1일 하반기 승단심사 일정을 발표했다. 문의는 [email protected] 로 하면 된다."
    out = clean_content(lead)
    assert out.startswith("국기원은") and "뉴시스" not in out and "email" not in out
    # 사진 캡션 (기자 이름 없음, '재판매 및 DB 금지' 꼬리) — 줄째 삭제. 태그 없는 문단은 꼬리만 뗀다
    photo = "[서울=뉴시스] 금메달을 딴 곽민주. (사진=세계태권도연맹 제공) *재판매 및 DB 금지"
    assert clean_content(lead + "\n" + photo) == out
    assert clean_content("국기원은 1일 일정을 발표했다. *재판매 및 DB 금지") == "국기원은 1일 일정을 발표했다."
    # Google 선호 출처 안내 줄 (톱스타뉴스). 'Google에서' 로 시작하는 본문 문장은 남긴다
    google = "\nGoogle 선호 출처로 추가하면 더 자주 보여요.\nGoogle에서 톱스타뉴스 자주 보기\nGoogle에서 톱스타뉴스를 선택해 주세요."
    assert clean_content(lead + google) == out
    assert clean_content("Google에서 태권도 영상이 인기다.") == "Google에서 태권도 영상이 인기다."
    # 연합뉴스 요약 박스 — 안내 문구와 그 위 요약 줄
    box = "국기원, 승단심사 일정 발표\n10월부터 전국 진행\n전체 내용을 이해하기 위해서는 기사 본문과 함께 읽어야 합니다.\n"
    assert clean_content(box + lead) == out
    # 줄 맨 앞 소괄호 바이라인. 본문 속 괄호는 남긴다
    assert clean_content("(톱스타뉴스 김수아 기자) 정하은(25·용인특례시청)이 금메달을 땄다.") == "정하은(25·용인특례시청)이 금메달을 땄다."
    # 사진 캡션·출처 표기
    # (실측 뉴스1 포토 기사: 부제·캡션·표기·관련기사가 한 줄로 붙어 온다 → 전부 빠져 제외된다)
    caption = "대한민국 정하은이 1일 일본 도요하시 체육관에서 열린 태권도 여자 개인 품새 결승전에서 금메달을 확정 짓자 세리머니를 하고 있다."
    photo_only = ("압도적 기량으로 우승…한국 28번째 金" + caption + " 2026.10.1 ⓒ 뉴스1 안은나 기자" + caption
                  + " ⓒ 뉴스1 안은나 기자관련 키워드2026아시안게임태권도관련 기사'페이커'부터 양궁 단체전 연속 우승까지")
    assert clean_content(photo_only) == ""
    assert clean_all([Article(title="t", body=photo_only)], min_len=100) == []
    # 본문 문단에 캡션이 붙은 경우 — 캡션 문장만 빠지고 본문은 남는다
    para = "정하은은 1일 품새 결승에서 평균 9.310점을 받아 아시아 정상에 올랐다. " * 4
    assert clean_content(para + caption + " ⓒ 뉴스1 안은나 기자\n" + lead) == para.strip() + "\n" + out
    # 매체 꼬리말 줄
    body = lead + "\n◎공감언론 뉴시스 [email protected]\n◎공감언론 뉴시스가 독자 여러분의 소중한 제보를 기다립니다."
    assert clean_content(body) == out


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


def test_auto_posts_follow_saved_pattern():
    # 2순위 묶음을 채택해 저장했으면 1순위가 아니라 그 묶음을 따른다
    html = GNUBOARD_LIKE.replace("</tbody></table>", "</tbody></table>" + "".join(
        f'<a href="/gallery/{i}">사진 게시글 {i}</a>' for i in range(1, 3)))
    groups = detect_groups(html, BASE)
    second = next(s for s, _ in groups if "gallery" in s)
    posts = _posts_auto(html, BASE, BoardConfig(list_url=BASE, list_pattern=second))
    assert [p.title for p in posts] == ["사진 게시글 1", "사진 게시글 2"]
    # 채택한 묶음이 사라지면 1순위로 바꿔 모으지 않고 0건
    assert _posts_auto(GNUBOARD_LIKE, BASE, BoardConfig(list_url=BASE, list_pattern=second)) == []
