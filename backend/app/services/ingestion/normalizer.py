from app.models.source_content import SourceContent


def normalize_items(items: list[SourceContent]) -> list[SourceContent]:
    """Single extension point for future cross-source normalization."""
    return items
