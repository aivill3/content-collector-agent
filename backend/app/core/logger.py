"""로깅. 콘솔 출력 + (선택) 파일 출력. 타임스탬프는 DISPLAY_TZ 기준.

taekwonw-agent 의 core/logger.py 를 줄였다. 실행 단계별 로그 파일 이름 추론은
CLI 전용 기능이라 뺐다. API 서버로 옮기면 서버 쪽 로깅 설정을 따르면 된다.

    from app.core.logger import get_logger
    log = get_logger(__name__)
"""
import logging
from datetime import datetime
from pathlib import Path

from app.core.config import BASE_DIR, DISPLAY_TZ

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# trafilatura 는 파싱 못 하는 HTML 에 자체 ERROR 를 찍는다. 해당 글은
# fetcher 가 조용히 버리므로 로그만 더럽힌다.
_NOISY_LOGGERS = {
    "trafilatura": logging.CRITICAL,
    "urllib3": logging.WARNING,
}

_configured = False


class DisplayTZFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=DISPLAY_TZ)
        return dt.strftime(datefmt or _DATEFMT)


def setup(to_file: bool = False, prefix: str = "collect") -> Path | None:
    """루트 로거 설정. 프로세스 시작 시 1회."""
    global _configured
    if _configured:
        return None
    formatter = DisplayTZFormatter(_FORMAT, datefmt=_DATEFMT)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    path = None
    if to_file:
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        path = log_dir / f"{prefix}_{datetime.now(DISPLAY_TZ):%Y%m%d_%H%M%S}.log"
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in handlers:
        h.setFormatter(formatter)
        root.addHandler(h)
    for name, level in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(level)
    _configured = True
    return path


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
