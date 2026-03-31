from typing import Any

from app.core.config import settings


class ChromaClientService:
    """Thin wrapper placeholder around ChromaDB persistence/retrieval."""

    def __init__(self) -> None:
        self.persist_dir = settings.chroma_persist_dir

    def upsert_documents(self, docs: list[dict[str, Any]]) -> None:
        _ = docs
        return None

    def query(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        _ = text, limit
        return []
