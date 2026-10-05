import re


def _has_any(text, words):
    return any(str(w).lower() in text for w in words)


def _has_word(text, words):
    """Mot entier : 'paris' ne matche pas 'paribas'."""
    return any(re.search(r"(?<!\w)" + re.escape(str(w).lower()) + r"(?!\w)", text) for w in words)


def matches(job, f):
    title = job["title"].lower()
    ctx = (job.get("location") or "").lower()
    full = f"{title} {ctx}"
    if not job.get("internship_source") and not _has_any(full, f["contract_keywords"]):
        return False
    if f.get("topic_keywords") and not _has_any(full, f["topic_keywords"]):
        return False
    if _has_any(title, f.get("exclude_keywords", [])):
        return False
    locs = f.get("locations") or []
    if locs and ctx and not _has_word(ctx, locs):
        return False
    return True
