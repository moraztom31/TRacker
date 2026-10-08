"""Scan reel apres avoir retire quelques offres de la base : elles doivent etre reconnues comme anciennes."""
import json
import subprocess
import sys

sys.path.insert(0, ".")
store = json.load(open("data/jobs.json"))
removed = {}
for company, n in (("Crédit Agricole / Amundi", 3), ("BNP Paribas", 3), ("Oddo BHF", 3), ("Groupe BPCE", 3), ("Natixis", 2)):
    ids = [k for k, v in store.items() if v["company"] == company and v.get("active")][:n]
    for k in ids:
        removed[k] = (company, store[k]["title"][:60])
        del store[k]
json.dump(store, open("data/jobs.json", "w"), ensure_ascii=False)
print("offres retirées de la base :", len(removed))
for k, (c, t) in removed.items():
    print("  -", c, "|", t)
import os
env = {**os.environ, "TRACKER_FULL": "1"}
out = subprocess.run([sys.executable, "-m", "tracker.main"], env=env, capture_output=True, text=True).stdout
for line in out.splitlines():
    if line.startswith(("[ANCIENNE]", "[WARN]", "[KO]")) or "sources," in line:
        print(line[:200])
