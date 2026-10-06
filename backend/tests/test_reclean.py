"""저장된 콘텐츠 다시 정제 — 임시 SQLite, 네트워크 없음."""
from app.db.models import Content, ContentKeywordHit
from app.repositories import contents
from app.repositories.scope import scoped_select
from app.services.collection_service import CollectResult
from app.workers.reclean import reclean_contents
from tests.test_db import article, item, news_source, run

LEAD = " ".join(["국기원은 1일 하반기 승단심사 일정을 발표했다. 심사는 10월부터 전국에서 진행된다."] * 3)
CAPTION = ("[도요하시(일본)=뉴시스] 이영환 기자 = 1일 일본 아이치현 도요하시 체육관에서 금메달을 획득한 "
           "한국 윤규성이 기념촬영을 하고 있다. 2026.10.01. [email protected]")


def save(session, ws, bodies: dict[str, str]) -> dict[str, int]:
    """URL 끝자리 → 원본 본문. 정제 본문은 원본 그대로 저장한다 (예전 규칙이 아무것도 못 지운 상태)."""
    src = news_source(session, ws)
    arts = []
    for key, raw in bodies.items():
        a = article(url=f"https://news.example.com/{key}")
        a.body = a.body_clean = raw
        arts.append(a)
    run(session, ws, src.id, CollectResult(articles=arts, raw={"태권도": [item(a.url) for a in arts]}))
    return {c.url.rsplit("/", 1)[1]: c.id for c in session.exec(scoped_select(Content, ws))}


def test_reclean_updates_only_changed_and_keeps_raw(session, ws_a, ws_b):
    ids = save(session, ws_a, {
        "clean": LEAD,
        "footer": LEAD + "\n◎공감언론 뉴시스 [email protected]",
        "photo": CAPTION,
    })
    other = save(session, ws_b, {"x": CAPTION})

    dry = reclean_contents(session, ws_a, dry_run=True)
    assert dry.checked == 3
    assert {c.content_id for c in dry.changed} == {ids["footer"], ids["photo"]}
    assert contents.get_content(session, ws_a, ids["photo"]).cleaned_body == CAPTION    # dry-run 은 그대로

    result = reclean_contents(session, ws_a)
    assert [c.content_id for c in result.short] == [ids["photo"]]                       # 0자 < 최소 100자
    footer = contents.get_content(session, ws_a, ids["footer"])
    assert "공감언론" not in footer.cleaned_body and footer.body_length == len(footer.cleaned_body)
    assert "공감언론" in footer.raw_body                                                # 원본은 보존
    photo = contents.get_content(session, ws_a, ids["photo"])
    assert photo is not None and photo.cleaned_body == "" and photo.body_length == 0     # 지우지 않는다
    # 다른 워크스페이스는 건드리지 않는다
    assert contents.get_content(session, ws_b, other["x"]).cleaned_body == CAPTION
    # 다시 돌려도 바뀌는 글이 없다
    assert reclean_contents(session, ws_a).changed == []


def test_delete_content_cascades_hits_and_is_scoped(session, ws_a, ws_b):
    ids = save(session, ws_a, {"a": LEAD})
    other = save(session, ws_b, {"b": LEAD})
    assert contents.list_hits(session, ws_a, ids["a"])
    assert contents.delete_content(session, ws_b, ids["a"]) is False        # 남의 워크스페이스 id
    assert contents.delete_content(session, ws_a, ids["a"]) is True
    session.commit()
    assert contents.get_content(session, ws_a, ids["a"]) is None
    assert session.exec(scoped_select(ContentKeywordHit, ws_a)).all() == []  # 키워드 기록도 함께
    assert contents.get_content(session, ws_b, other["b"]) is not None
