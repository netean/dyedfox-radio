def parse_icy_title(raw: str) -> tuple[str, str]:
    """Split 'Artist – Title' into (artist, title). Returns ('', raw) if no separator found."""
    for sep in (" – ", " - ", " — "):
        if sep in raw:
            parts = raw.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return "", raw.strip()
