import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import notify
from .filters import matches
from .sources import COLLECTORS

ROOT = Path(__file__).resolve().parent.parent
JOBS_FILE = ROOT / "data" / "jobs.json"
HEALTH_FILE = ROOT / "data" / "health.json"
SITE_FILE = ROOT / "docs" / "jobs.json"
FAIL_ALERT_AT = 3  # alerte après N échecs consécutifs d'une source


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def dump_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True)
    if not path.exists() or path.read_text(encoding="utf-8") != new:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def run_source(item):
    kind, cfg = item
    try:
        return item, COLLECTORS[kind](cfg), None
    except Exception as e:  # noqa: BLE001
        return item, None, f"{type(e).__name__}: {e}"


def main(config_path=None, collectors=None):
    cfg = yaml.safe_load((config_path or ROOT / "config.yaml").read_text(encoding="utf-8"))
    tasks = [(kind, c) for kind, lst in (cfg.get("sources") or {}).items() for c in (lst or [])]
    first_run = not JOBS_FILE.exists()
    store = load_json(JOBS_FILE, {})
    health = load_json(HEALTH_FILE, {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(run_source, tasks))

    new, ok_companies, seen_ids, live_keys = [], set(), set(), set()
    known_titles = {(j["company"].lower(), j["title"].strip().lower()) for j in store.values() if j.get("active")}
    for (kind, c), jobs, err in results:
        key = f"{kind}:{c['company']}:" + str(c.get("url") or c.get("slug") or c.get("id") or c.get("host", ""))[-60:]
        live_keys.add(key)
        if err:
            n = health.get(key, {}).get("fails", 0) + 1
            health[key] = {**health.get(key, {}), "fails": n, "last_error": err[:200]}
            print(f"[KO] {key} ({n}) {err}")
            if n == FAIL_ALERT_AT:
                notify.send(f"⚠️ Source en panne : <b>{key}</b>\n{err[:200]}")
            continue
        seeded = health.get(key, {}).get("seeded", False)
        health[key] = {"fails": 0, "last_error": "", "seeded": True}
        ok_companies.add(c["company"])
        kept = sum(1 for j in jobs if matches(j, cfg["filters"]))
        print(f"[OK] {c['company']:<28} {len(jobs):>4} offres lues, {kept:>3} gardées par les filtres")
        for j in jobs:
            if not matches(j, cfg["filters"]):
                continue
            seen_ids.add(j["id"])
            if j["id"] in store:
                store[j["id"]]["active"] = True
            elif (j["company"].lower(), j["title"].strip().lower()) in known_titles:
                continue  # même offre déjà suivie via une autre source
            else:
                known_titles.add((j["company"].lower(), j["title"].strip().lower()))
                j.update(first_seen=now, active=True)
                store[j["id"]] = j
                if seeded:  # pas d'alerte au tout premier passage d'une source
                    new.append(j)

    # Offres disparues d'une source qui a répondu = clôturées
    for jid, j in store.items():
        if j["company"] in ok_companies and jid not in seen_ids:
            j["active"] = False

    print(f"{len(tasks)} sources, {sum(1 for j in store.values() if j.get('active'))} offres suivies, {len(new)} nouvelles signalées, {time.time() - t0:.1f}s")

    if new:
        notify.new_jobs(sorted(new, key=lambda j: j["company"]), cfg.get("telegram", {}).get("max_detailed", 10))
    if first_run:
        print("Premier passage : base initialisée sans alertes.")

    health = {k: v for k, v in health.items() if k in live_keys}  # oublie les sources retirées de config.yaml
    changed = dump_json(JOBS_FILE, store)
    dump_json(HEALTH_FILE, health)
    if changed or not SITE_FILE.exists():
        dump_json(SITE_FILE, {"generated_at": now, "jobs": sorted(store.values(), key=lambda j: j["first_seen"], reverse=True)})


if __name__ == "__main__":
    main()
