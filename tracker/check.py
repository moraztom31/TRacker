"""Teste les sources AVANT de les laisser tourner.
python -m tracker.check config "HSBC"          -> teste l'entrée de config.yaml
python -m tracker.check greenhouse <slug>
python -m tracker.check lever <slug>
python -m tracker.check smartrecruiters <id>
python -m tracker.check workday <host> <tenant> <site>"""
import sys
from pathlib import Path

import yaml

from .sources import COLLECTORS


def show(kind, cfg):
    jobs = COLLECTORS[kind](cfg)
    print(f"[{kind}] {cfg['company']} : {len(jobs)} offres")
    for j in jobs[:10]:
        print("  -", j["title"], "|", j["location"], "|", j["url"])


def main():
    a = sys.argv[1:]
    if len(a) >= 1 and a[0] == "config":
        a = a + [""] if len(a) == 1 else a
        cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
        hits = [(k, c) for k, lst in cfg["sources"].items() for c in (lst or []) if a[1].lower() in c["company"].lower()]
        if not hits:
            print("Aucune entrée trouvée pour", a[1])
        for k, c in hits:
            try:
                show(k, c)
            except Exception as e:  # noqa: BLE001
                print(f"[{k}] {c['company']} : ERREUR {type(e).__name__}: {str(e)[:150]}")
        return
    if len(a) < 2 or a[0] not in COLLECTORS:
        print(__doc__)
        return
    kind, cfg = a[0], {"company": a[1]}
    if kind in ("greenhouse", "lever"):
        cfg["slug"] = a[1]
    elif kind == "smartrecruiters":
        cfg["id"] = a[1]
    elif kind == "workday":
        cfg.update(host=a[1], tenant=a[2], site=a[3], queries=["stage", "intern"])
    else:
        print("Pour generic_json/generic_html, utilise : check config <entreprise>")
        return
    show(kind, cfg)


if __name__ == "__main__":
    main()
