import json
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Document:
    content: str
    metadata: dict = field(default_factory=dict)
    score: float | None = None


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 5) -> list[Document]: ...


class NullRetriever:
    """Mặc định: không truy xuất gì. Chỗ để cắm VectorRetriever sau này."""

    def retrieve(self, query: str, top_k: int = 5) -> list[Document]:
        return []


def get_features(settings: dict) -> dict:
    raw = (settings or {}).get("features") or "{}"
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def get_retriever(settings: dict) -> Retriever:
    features = get_features(settings)
    if not features.get("rag_enabled"):
        return NullRetriever()
    # Seam: khi làm RAG, trả về VectorRetriever(features) ở đây.
    return NullRetriever()
