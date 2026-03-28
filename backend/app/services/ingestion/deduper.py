from app.models.source_content import SourceContent


def dedupe_items(items: list[SourceContent]) -> list[SourceContent]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[SourceContent] = []
    for item in items:
        key = (item.source, item.platform_id, item.content_type)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
