import logging
import uuid

from app.core.observability import context

_logger = logging.getLogger("app.events")


def new_event_ref() -> str:
    return uuid.uuid4().hex[:6].upper()


def record_event(
    level: str,
    component: str,
    message: str,
    *,
    code: str | None = None,
    exc: BaseException | None = None,
    event_ref: str | None = None,
    **ctx,
) -> str:
    ref = event_ref or new_event_ref()
    request_id = context.get_request_id()
    if request_id:
        ctx.setdefault("req", request_id)
    label = f"{component} ({code})" if code else component
    extra = " ".join(f"{key}={value}" for key, value in ctx.items() if value)
    text = f"[{ref}] {label}: {message}"
    if extra:
        text += f" | {extra}"
    levelno = getattr(logging, str(level).upper(), logging.INFO)
    if exc is not None:
        _logger.log(levelno, text, exc_info=exc)
    else:
        _logger.log(levelno, text)
    return ref
