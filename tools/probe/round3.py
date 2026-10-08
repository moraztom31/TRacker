"""Tour 3 : formats exacts (HSBC Eightfold, AXA Jibe, BNP via TLS navigateur, Oddo, Natixis, Pictet, sites Workday)."""
import json
import re

import requests
from curl_cffi import requests as cr

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


def section(t):
    print(f"\n##### {t}")


def keys(o, d=0):
    return list(o.keys())[:40] if isinstance(o, dict) else type(o).__name__


section("HSBC eightfold")
for u in ["https://portal.careers.hsbc.com/api/apply/v2/jobs?domain=hsbc.com&query=intern&start=0&num=10&sort_by=relevance",
          "https://portal.careers.hsbc.com/api/pcsx/search?domain=hsbc.com&query=intern&start=0&num=10&sort_by=relevance",
          "https://portal.careers.hsbc.com/api/apply/v2/jobs?domain=hsbc.com&location=France&query=stage&start=0&num=10"]:
    try:
        r = requests.get(u, headers=UA, timeout=20)
        j = r.json()
        print(r.status_code, u[:110], "keys", keys(j))
        pos = j.get("positions") or (j.get("data") or {}).get("positions") or []
        print("  count", len(pos), "total", j.get("count"), (j.get("data") or {}).get("count"))
        if pos:
            print("  pos keys", keys(pos[0]))
            print("  sample", sh({k: pos[0].get(k) for k in ("id", "name", "location", "locations", "canonicalPositionUrl", "display_job_id", "t_create", "department")}, 600))
    except Exception as e:
        print("ERR", u[:100], type(e).__name__, str(e)[:100])

section("AXA jibe")
try:
    r = requests.get("https://careers.axa.com/api/jobs?limit=3&keywords=intern&page=1", headers=UA, timeout=20)
    j = r.json()
    print(r.status_code, "keys", keys(j), "total", j.get("totalCount"), j.get("count"))
    d = j["jobs"][0]["data"]
    print("data keys", keys(d))
    print(sh({k: d.get(k) for k in ("slug", "req_id", "title", "city", "state", "country", "location_name", "full_location", "short_location", "locations", "apply_url", "canonical_url", "create_date", "posted_date")}, 700))
    print("meta", sh({k: v for k, v in j["jobs"][0].items() if k != "data"}, 300))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:150])

section("BNP via curl_cffi")
try:
    r = cr.get("https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/stage", impersonate="chrome124", timeout=30)
    t = r.text
    print(r.status_code, len(t))
    links = re.findall(r'<a[^>]+href="([^"]+)"', t)
    offres = [l for l in dict.fromkeys(links) if re.search(r"offre|job|emploi", l, re.I)]
    print("liens offres:", len(offres))
    for l in offres[:25]:
        print("  ", l[:140])
    pag = [l for l in dict.fromkeys(links) if re.search(r"page=|[?&]p=|/page/", l)]
    print("pagination:", pag[:8])
    m = re.search(r'<a[^>]+href="([^"]*toutes-offres-emploi/[^"]*(?:stage|job|offre)[^"]*[0-9]{4,}[^"]*)"', t)
    if m:
        i = t.index(m.group(0))
        print("HTML carte:", sh(t[max(0, i - 200):i + 700], 900))
    print("total annonce:", re.findall(r"(\d[\d\s]*)\s*(?:offres?|résultats?)", t)[:5])
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:150])
try:
    r = cr.get("https://group.bnpparibas/rss", impersonate="chrome124", timeout=30)
    feeds = [l for l in dict.fromkeys(re.findall(r'href="([^"]+)"', r.text)) if re.search(r"rss|feed|xml|flux", l, re.I)]
    print("RSS page liens:", feeds[:15])
except Exception as e:
    print("ERR rss", type(e).__name__, str(e)[:100])

section("Oddo altays")
for u in ["https://recrutement.altays-progiciels.com/oddo/en/offres", "https://recrutement.altays-progiciels.com/oddo/fr/offres",
          "https://recrutement.altays-progiciels.com/oddo/en/offres/nombre.json?page=1"]:
    try:
        r = requests.get(u, headers=UA, timeout=20)
        t = r.text
        print(r.status_code, u, len(t), sh(t[:150]))
        links = [l for l in dict.fromkeys(re.findall(r'href="([^"]+)"', t)) if re.search(r"offre", l, re.I)]
        print("  liens:", len(links), links[:12])
        print("  pagination:", [l for l in dict.fromkeys(re.findall(r'href="([^"]+)"', t)) if re.search(r"page=", l)][:5])
        m = re.search(r'<a[^>]+href="([^"]*offres/[^"]*[0-9]+[^"]*)"', t)
        if m:
            i = t.index(m.group(0))
            print("  carte:", sh(t[max(0, i - 150):i + 500], 650))
    except Exception as e:
        print("ERR", u, type(e).__name__, str(e)[:100])

section("Natixis")
try:
    r = requests.get("https://recrutement.natixis.com/app/wp-json/bpce/v1/routes/?lang=fr", headers=UA, timeout=20)
    routes = r.json()
    for x in routes:
        p = x.get("path", "") + " | " + x.get("component", "")
        if re.search(r"offre|job|emploi|search|recherche", p, re.I):
            print("  route", sh(p, 160), x.get("_uid"))
except Exception as e:
    print("ERR routes", type(e).__name__, str(e)[:100])
for u in ["https://recrutement.natixis.com/app/wp-json/bpce/v1/jobs/?lang=fr&per_page=5",
          "https://recrutement.natixis.com/app/wp-json/bpce/v1/jobs?lang=fr",
          "https://recrutement.natixis.com/app/wp-json/bpce/v2/jobs/?lang=fr",
          "https://recrutement.natixis.com/app/wp-json/bpce/v1/jobs/search/?lang=fr",
          "https://recrutement.natixis.com/app/wp-json/wp/v2/types"]:
    try:
        r = requests.get(u, headers=UA, timeout=20)
        print(r.status_code, u[-70:], len(r.text), sh(r.text, 220))
    except Exception as e:
        print("ERR", u[-60:], type(e).__name__)

section("Pictet SF")
try:
    r = requests.get("https://career5.successfactors.eu/career?company=banquepict&career_ns=job_listing_summary&navBarLevel=JOB_SEARCH", headers=UA, timeout=25)
    t = r.text
    ids = re.findall(r"career_job_req_id=(\d+)", t)
    print(r.status_code, len(t), "req ids:", len(set(ids)), sorted(set(ids))[:5])
    ls = [l for l in dict.fromkeys(re.findall(r'href="([^"]+)"', t)) if re.search(r"job", l, re.I)]
    print("liens:", ls[:10])
    m = re.search(r'<a[^>]+href="([^"]*career_job_req_id[^"]*)"', t)
    if m:
        i = t.index(m.group(0))
        print("carte:", sh(t[max(0, i - 200):i + 600], 800))
    print("jobs inline:", re.findall(r'"(?:jobTitle|title)"\s*:\s*"([^"]{5,80})"', t)[:6])
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:100])

section("Workday sites (navigateur)")
try:
    from playwright.sync_api import sync_playwright
    CAND = [("kkr", 1), ("jefferies", 1), ("nomura", 3), ("alliancebernstein", 1), ("wellsfargo", 1), ("rbc", 3), ("td", 3), ("scotiabank", 3),
            ("franklintempleton", 5), ("moodys", 5), ("nasdaq", 1), ("natwestgroup", 3), ("sc", 3), ("abnamro", 3), ("generali", 3), ("dws", 3),
            ("unicredit", 3), ("ubp", 3), ("mizuho", 5), ("smbc", 1), ("bnpparibas", 3), ("natixis", 3), ("hsbc", 3), ("ubs", 3), ("citi", 5),
            ("nuveen", 5), ("moelis", 1), ("pwp", 5), ("wf", 1), ("allianzgi", 3), ("amundi", 3), ("axa", 3), ("commerzbank", 3), ("mandg", 3),
            ("lgim", 3), ("janushenderson", 5), ("capgroup", 5), ("jupiter", 3), ("schroders", 3), ("hl", 1), ("lazard", 5), ("centerview", 1)]
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        for t, n in CAND:
            host = f"{t}.wd{n}.myworkdayjobs.com"
            ctx = b.new_context(user_agent=UA["User-Agent"])
            pg = ctx.new_page()
            api = []
            pg.on("request", lambda rq, api=api: api.append(rq.url) if "/wday/cxs/" in rq.url else None)
            try:
                pg.goto(f"https://{host}/", wait_until="domcontentloaded", timeout=15000)
                pg.wait_for_timeout(2500)
                u = pg.url
                m = re.search(r"/wday/cxs/([^/]+)/([^/]+)/", " ".join(api))
                print(f"  {host} -> {u[:110]} api={m.groups() if m else None}")
            except Exception as e:
                print(f"  {host} ERR {type(e).__name__}")
            ctx.close()
        b.close()
except Exception as e:
    print("ERR playwright", type(e).__name__, str(e)[:100])
print("FIN ROUND3")
