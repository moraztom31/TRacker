"""Les pages de detail donnent-elles une date de publication exploitable ? (CA, BNP, Oddo)"""
import re
import sys

sys.path.insert(0, ".")
from tracker.sources import _get  # noqa: E402

TESTS = [
    ("CA offre Asset Allocation", "https://groupecreditagricole.jobs/fr/nos-offres-emploi/579-170466-4-assistante-asset-allocation-hf-reference--2026-115659--/", None,
     [r"Modifi\S{1,8}e le\s*(\d{2}/\d{2}/\d{4})", r'"datePosted"\s*:\s*"([^"]+)"']),
    ("CA offre Werkstudent", "https://groupecreditagricole.jobs/fr/nos-offres-emploi/578-170475-270-werkstudent-hr-mwd-reference--2024-92174--/", None,
     [r"Modifi\S{1,8}e le\s*(\d{2}/\d{2}/\d{4})", r'"datePosted"\s*:\s*"([^"]+)"']),
    ("BNP", "https://group.bnpparibas/emploi-carriere/offre-emploi/stage-assistant-data-analyst-h-f", "chrome124", [r'"datePosted"\s*:\s*"(\d{4}-\d{2}-\d{2})']),
    ("Oddo", "https://recrutement.altays-progiciels.com/oddo/fr/offres/praktikant-mwd-asset-management-bereich-portfolio-management-quantitative-strategies-2887731.html", None,
     [r'"datePosted"\s*:\s*"([^"]+)"', r"Publi\S{1,8}e? le\s*(\d{1,2}/\d{1,2}/\d{4})", r'<time[^>]+datetime="([^"]+)"']),
]
for name, url, imp, regexes in TESTS:
    try:
        t = _get(url, imp).text
        print(f"== {name}: {len(t)} octets")
        for rx in regexes:
            print("   ", rx[:45], "->", re.findall(rx, t)[:3])
        for kw in ("Modifi", "Mis à jour", "Publi", "datePosted", "Date de"):
            for m in list(re.finditer(kw, t))[:2]:
                print(f"    [{kw}]", re.sub(r"\s+", " ", t[max(0, m.start() - 60):m.start() + 90]))
    except Exception as e:
        print("ERR", name, type(e).__name__, str(e)[:100])
print("FIN")
