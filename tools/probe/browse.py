"""Navigateur headless : repere les requetes JSON (liste d'offres) des sites 100 % JavaScript."""
import re
import sys

from playwright.sync_api import sync_playwright

TARGETS = {
    "BNP": "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/stage",
    "BNP-bwelcome": "https://bwelcome.hr.bnpparibas/fr_FR/externalcareers",
    "Natixis": "https://recrutement.natixis.com/",
    "UBS": "https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid=5012",
    "UBS-students": "https://www.ubs.com/global/en/careers/students-and-graduates.html",
    "HSBC": "https://portal.careers.hsbc.com/careers?query=intern&start=0&sort_by=relevance",
    "Oddo": "https://www.oddo-bhf.com/discover-our-jobs/",
    "Pictet": "https://career5.successfactors.eu/career?company=banquepict",
    "Nomura": "https://www.nomura.com/careers/early-careers/internship-programs/",
    "Citadel": "https://www.citadel.com/careers/open-opportunities/students/",
    "DEShaw": "https://www.deshaw.com/careers/choose-your-path",
}
only = sys.argv[1:]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    for name, url in TARGETS.items():
        if only and name not in only:
            continue
        ctx = b.new_context(locale="fr-FR", viewport={"width": 1366, "height": 900},
                            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36")
        pg = ctx.new_page()
        seen = []

        def on_resp(r, seen=seen):
            ct = r.headers.get("content-type", "")
            if ("json" in ct or "xml" in ct) and r.request.resource_type in ("xhr", "fetch"):
                try:
                    body = r.text()
                except Exception:
                    body = ""
                seen.append((r.request.method, r.url, r.status, len(body), re.sub(r"\s+", " ", body[:200])))

        pg.on("response", on_resp)
        try:
            resp = pg.goto(url, wait_until="domcontentloaded", timeout=30000)
            pg.wait_for_timeout(9000)
            title = pg.title()
            status = resp.status if resp else "?"
        except Exception as e:
            title, status = f"ERR {type(e).__name__} {str(e)[:60]}", "?"
        print(f"=== {name} status={status} title={title[:70]!r} xhr_json={len(seen)}")
        scored = sorted(seen, key=lambda x: (not re.search(r"job|search|offer|position|requisition|vacanc|opportun|career", x[1], re.I), -x[3]))
        for m, u, s, n, snip in scored[:8]:
            print(f"  {m} {s} {n}b {u[:170]}\n     {snip[:170]}")
        ctx.close()
    b.close()
print("FIN BROWSE")
