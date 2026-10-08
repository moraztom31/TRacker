import re
import unicodedata


def _norm(text):
    """Minuscules sans accents : 'GENÈVE' et 'geneve' deviennent identiques."""
    text = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _has_any(text, words):
    return any(_norm(w) in text for w in words)


def _has_word(text, words):
    """Mot entier : 'paris' ne matche pas 'paribas'."""
    return any(re.search(r"(?<!\w)" + re.escape(_norm(w)) + r"(?!\w)", text) for w in words)


def _has_contract(text, words):
    """Mot entier, pluriel accepté : 'intern' ne matche plus 'internal' ni 'international'.
    Un mot terminé par '*' est un préfixe ('praktik*' -> praktikum, praktikant)."""
    for w in words:
        w = _norm(w)
        if w.endswith("*"):
            pat = r"(?<!\w)" + re.escape(w[:-1])
        else:
            pat = r"(?<!\w)" + re.escape(w) + r"(?:s|es)?(?!\w)"
        if re.search(pat, text):
            return True
    return False


def matches(job, f):
    title = _norm(job["title"])
    ctx = _norm(job.get("location") or "")
    full = f"{title} {ctx}"
    if not job.get("internship_source") and not _has_contract(full, f["contract_keywords"]):
        return False
    if f.get("topic_keywords") and not _has_any(full, f["topic_keywords"]):
        return False
    if _has_any(title, f.get("exclude_keywords", [])):
        return False
    locs = f.get("locations") or []
    if locs and ctx and not _has_word(ctx, locs):
        return False
    return True
