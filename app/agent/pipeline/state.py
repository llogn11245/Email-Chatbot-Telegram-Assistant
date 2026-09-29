from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[Any]
    context_docs: list[dict]
    trace_id: str
