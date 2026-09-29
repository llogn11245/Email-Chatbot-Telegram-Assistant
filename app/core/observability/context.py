import contextvars
import uuid

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
_component: contextvars.ContextVar[str] = contextvars.ContextVar("component", default="app")


def new_request_id() -> str:
    return uuid.uuid4().hex[:8]


def set_request_id(value: str | None = None) -> str:
    rid = value or new_request_id()
    _request_id.set(rid)
    return rid


def get_request_id() -> str:
    return _request_id.get()


def set_component(value: str) -> None:
    _component.set(value)


def get_component() -> str:
    return _component.get()
