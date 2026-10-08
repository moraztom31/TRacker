import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import notify
from .filters import matches
from .sources import COLLECTORS, publication_date

ROOT = Path(__file__).resolve().parent.parent
JOBS_FILE = ROOT / "data" / "jobs.json"
HEALTH_FILE = ROOT / "data" / "health.json"
SITE_FILE = ROOT / "docs" / "jobs.json"
FAIL_ALERT_AT = 3  # alerte après N échecs consécutifs d'une source
FRESH_DAYS = 3  # une offre publiée il y a plus longtemps n'est pas une nouveauté (liste réordonnée, offre re-listée...)
MAX_DETAIL_CHECKS = 40  # pages d'offres consultées au maximum par passage pour lire la date de publication
FULL_SCAN_MINUTES = 5  # scan complet pendant les 5 premières minutes de chaque heure ; sinon mode rapide


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def dump_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True)
    if not path.exists() or path.read_text(encoding="utf-8") != new:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def source_key(kind, c):
    key = f"{kind}:{c['company']}:" + str(c.get("url") or c.get("slug") or c.get("id") or c.get("host", ""))[-60:]
    if c.get("seed"):  # `seed: 2` dans config.yaml : réinitialise la source en silence (portée élargie, pas d'avalanche d'alertes)
        key += f":seed{c['seed']}"
    return key


def run_source(args):
    (kind, cfg), partial = args
    try:
        # mode rapide : seulement les premières pages (les plus récentes) des gros sites
        run_cfg = {**cfg, "pages": cfg["recent_pages"], "max_pages": cfg["recent_pages"]} if partial else cfg
        return (kind, cfg), COLLECTORS[kind](run_cfg), None
    except Exception as e:  # noqa: BLE001
        return (kind, cfg), None, f"{type(e).__name__}: {e}"


def main(config_path=None, collectors=None):
    cfg = yaml.safe_load((config_path or ROOT / "config.yaml").read_text(encoding="utf-8"))
    tasks = [(kind, c) for kind, lst in (cfg.get("sources") or {}).items() for c in (lst or [])]
    first_run = not JOBS_FILE.exists()
    store = load_json(JOBS_FILE, {})
    health = load_json(HEALTH_FILE, {})
    now_dt = datetime.now(timezone.utc)
    now = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    detail_checks = 0

    # Mode rapide : le but est de ne pas rater les NOUVELLES offres, pas de relire tout un site à chaque passage.
    # Une source n'est lue en partie que si elle a `recent_pages`, a déjà été initialisée, et que ce n'est pas l'heure du scan complet.
    forced = os.getenv("TRACKER_FULL")  # "1" force le scan complet, "0" force le mode rapide (tests)
    full_scan = first_run or forced == "1" or (forced != "0" and datetime.now(timezone.utc).minute < FULL_SCAN_MINUTES)
    partial_flags = [
        bool(not full_scan and c.get("recent_pages") and health.get(source_key(k, c), {}).get("seeded", False)) for k, c in tasks
    ]
    partial_keys = {source_key(k, c) for (k, c), p in zip(tasks, partial_flags) if p}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(run_source, zip(tasks, partial_flags)))

    new, ok_companies, seen_ids, live_keys = [], set(), set(), set()
    known_titles = {(j["company"].lower(), j["title"].strip().lower()) for j in store.values() if j.get("active")}
    for (kind, c), jobs, err in results:
        key = source_key(kind, c)
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
        if key not in partial_keys:  # lecture partielle : on n'a pas tout vu, donc aucune offre n'est marquée « clôturée »
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
                pub = None
                if seeded and detail_checks < MAX_DETAIL_CHECKS and (c.get("detail_date") or c.get("posted_is_publication")):
                    try:
                        detail_checks += 1 if c.get("detail_date") else 0
                        pub = publication_date(c, j)
                    except Exception as e:  # noqa: BLE001
                        print(f"[WARN] date de publication illisible pour {j['url']}: {type(e).__name__}")
                if pub and now_dt - pub > timedelta(days=FRESH_DAYS):
                    # Offre ancienne que le robot n'avait pas encore vue (liste réordonnée pendant le scan, offre re-listée) :
                    # on la garde avec sa vraie date, sans alerte ni badge « Nouveau ».
                    j.update(first_seen=pub.strftime("%Y-%m-%dT%H:%M:%SZ"), active=True)
                    store[j["id"]] = j
                    print(f"[ANCIENNE] {j['company']} : {j['title'][:60]} (publiée le {pub:%d/%m/%Y}), pas d'alerte")
                    continue
                j.update(first_seen=now, active=True)
                store[j["id"]] = j
                if seeded:  # pas d'alerte au tout premier passage d'une source
                    new.append(j)

    # Offres disparues d'une source qui a répondu = clôturées
    for jid, j in store.items():
        if j["company"] in ok_companies and jid not in seen_ids:
            j["active"] = False

    mode = "complet" if full_scan else f"rapide ({len(partial_keys)} sources en lecture partielle)"
    print(f"{len(tasks)} sources, {sum(1 for j in store.values() if j.get('active'))} offres suivies, {len(new)} nouvelles signalées, {time.time() - t0:.1f}s, scan {mode}")

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
