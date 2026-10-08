"""UBS portail etudiants (5131) : combien d'offres couvre-t-on avec plusieurs mots-cles ?"""
import sys

import yaml

sys.path.insert(0, ".")
from tracker.filters import matches  # noqa: E402
from tracker.sources import brassring  # noqa: E402

cfgf = yaml.safe_load(open("config.yaml", encoding="utf-8"))["filters"]
QS = ["", "intern", "internship", "graduate", "analyst", "stage", "trainee", "program", "associate", "summer", "wealth", "investment", "risk", "technology", "operations", "2027"]
base = {"company": "UBS", "host": "jobs.ubs.com", "partner": 25008, "site": 5131, "location_fields": ["formtext23"]}
seen = set()
for i in range(1, len(QS) + 1):
    jobs = brassring({**base, "queries": QS[:i]})
    print(f"{i:>2} mots-clés ({QS[i-1]!r:<14}) -> {len(jobs)} offres uniques")
jobs = brassring({**base, "queries": QS})
kept = [j for j in jobs if matches(j, cfgf)]
print("\nofffres gardées par le filtre contrat (stage/intern):", len(kept), "sur", len(jobs))
for j in kept[:12]:
    print("  -", j["title"][:70], "|", j["location"][:40])
print("exclues (ex.):", [j["title"][:50] for j in jobs if not matches(j, cfgf)][:5])
