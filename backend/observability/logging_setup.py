import logging
import logging.handlers
import re
import sys

from backend import config

_RETENTION = max(1, config.LOG_RETENTION_DAYS)

_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{8,}"), "sk-***"),
    (re.compile(r"ya29\.[A-Za-z0-9._\-]+"), "ya29.***"),
    (
        re.compile(
            r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|"
            r"password|client[_-]?secret)\s*[=:]\s*)(\S+)"
        ),
        r"\1***",
    ),
]


def mask_secrets(text: str) -> str:
    if not text:
        return text
    out = text
    for pattern, replacement in _PATTERNS:
        out = pattern.sub(replacement, out)
    return out


class SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return mask_secrets(super().format(record))


_configured = False


def setup_logging(level: str | None = None) -> None:
    global _configured
    if _configured:
        return
    log_dir = config.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, (level or config.LOG_LEVEL).upper(), logging.INFO))
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = SafeFormatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    root.addHandler(console)

    app_file = logging.handlers.TimedRotatingFileHandler(
        str(log_dir / "app.log"), when="midnight", backupCount=_RETENTION, encoding="utf-8"
    )
    app_file.setFormatter(formatter)
    root.addHandler(app_file)

    error_file = logging.handlers.TimedRotatingFileHandler(
        str(log_dir / "error.log"), when="midnight", backupCount=_RETENTION, encoding="utf-8"
    )
    error_file.setLevel(logging.WARNING)
    error_file.setFormatter(formatter)
    root.addHandler(error_file)

    for noisy in ("httpx", "httpcore", "httpcore2", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
