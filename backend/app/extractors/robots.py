"""robots.txt 확인 — 게시판·글 URL 수집이 함께 쓴다. (collectors/board.py 에서 이동)

RESPECT_ROBOTS=true(기본)면 robots.txt 가 막은 경로는 받지 않는다.
사이트마다 robots.txt 를 한 번만 받아 프로세스 안에서 재사용한다.
"""
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

from app.core.config import REQUEST_TIMEOUT, RESPECT_ROBOTS

_robots_cache: dict[str, RobotFileParser | None] = {}


def allowed(url: str) -> bool:
    """robots.txt 가 이 URL 을 허용하는가. robots.txt 를 못 읽으면 허용으로 본다."""
    if not RESPECT_ROBOTS:
        return True
    parts = urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _robots_cache:
        rp: RobotFileParser | None = RobotFileParser()
        try:
            resp = requests.get(f"{root}/robots.txt", timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp = None   # 없음(404 등) = 제한 없음
        except requests.RequestException:
            rp = None
        _robots_cache[root] = rp
    rp = _robots_cache[root]
    return True if rp is None else rp.can_fetch("*", url)
