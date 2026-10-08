"""Tour 7 : UBS (BrassRing) sans navigateur, et lieu des offres Natixis via l'API WordPress."""
import json
import re

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


print("##### UBS sans navigateur")
try:
    HOME = "https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid=5012"
    s = requests.Session()
    s.headers.update(UA)
    r = s.get(HOME, timeout=40)
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    hidden = {(i.get("id") or i.get("name")): (i.get("value") or "") for i in soup.find_all("input", type="hidden")}
    print("cookies:", list(s.cookies.keys()))
    print("hidden:", {k: len(v) for k, v in hidden.items()})
    enc = None
    for k, v in hidden.items():
        if "_slp_rhc_" in v or v.startswith("^"):
            print("candidat enc:", k, sh(v, 120))
            enc = enc or v
    m = re.findall(r"\^[A-Za-z0-9+/=_]{60,}", html.replace("&#x2F;", "/").replace("&#47;", "/"))
    print("regex ^...:", len(m), sh(m[0], 100) if m else None)
    enc = enc or (m[0] if m else "")
    for k in ("SIDValue", "rfToken", "TokenResponse", "CookieValue"):
        print(k, "=", sh(hidden.get(k, ""), 140))
    body = {"PartnerId": "25008", "SiteId": "5012", "Keyword": "intern", "Location": "", "KeywordCustomSolrFields": "FORMTEXT2,FORMTEXT21,AutoReq,Department,JobTitle",
            "LocationCustomSolrFields": "FORMTEXT2,FORMTEXT23,Location", "FacetFilterFields": None, "TurnOffHttps": False, "Latitude": 0, "Longitude": 0,
            "PowerSearchOptions": {"PowerSearchOption": []}, "encryptedsessionvalue": enc}
    base_h = {"Content-Type": "application/json;charset=UTF-8", "Accept": "application/json, text/plain, */*", "X-Requested-With": "XMLHttpRequest", "Referer": HOME, "Origin": "https://jobs.ubs.com"}
    variants = {"sans RFT": base_h, "avec RFT": {**base_h, "RFT": hidden.get("rfToken", "")}}
    for name, h in variants.items():
        rr = s.post("https://jobs.ubs.com/TgNewUI/Search/Ajax/MatchedJobs", headers=h, data=json.dumps(body), timeout=40)
        print(name, rr.status_code, len(rr.text), sh(rr.text, 160))
        if rr.ok and rr.text.startswith("{"):
            j = rr.json()
            jobs = (j.get("Jobs") or {}).get("Job") or []
            print("  cles:", list(j.keys())[:15], "Jobs cles:", list((j.get("Jobs") or {}).keys()), "nb:", len(jobs))
            for k in list(j.keys()):
                if re.search(r"count|total|page|more", k, re.I):
                    print("   ", k, "=", sh(j[k], 80))
            if jobs:
                q = {x["QuestionName"]: x["Value"] for x in jobs[0].get("Questions", [])}
                print("  1er job:", sh(q, 500), "| Link:", jobs[0].get("Link"))
            break
except Exception as e:
    print("ERR UBS", type(e).__name__, str(e)[:200])

print("\n##### Natixis WordPress")
try:
    BASE = "https://recrutement.natixis.com/app/wp-json"
    types = requests.get(f"{BASE}/wp/v2/types", headers=UA, timeout=20).json()
    print("types:", {k: v.get("rest_base") for k, v in types.items()})
    for k, v in types.items():
        if re.search(r"job|offre|emploi|offer", k, re.I):
            u = f"{BASE}/wp/v2/{v.get('rest_base')}?per_page=3"
            rr = requests.get(u, headers=UA, timeout=20)
            print(k, rr.status_code, len(rr.text), sh(rr.text, 900))
    for u in [f"{BASE}/bpce/v1/jobs/20526?lang=fr", f"{BASE}/bpce/v1/job/20526?lang=fr", f"{BASE}/bpce/v1/pages/?lang=fr&_uid=job-20526-4599efdf257aa&id=20526",
              f"{BASE}/bpce/v1/pages/?lang=fr&id=20526", f"{BASE}/bpce/v1/pages/?_uid=job-20526-4599efdf257aa", f"{BASE}/bpce/v1/pages/?lang=fr&uid=job-20526-4599efdf257aa"]:
        rr = requests.get(u, headers={**UA, "Referer": "https://recrutement.natixis.com/job/stage-6-mois-developpeur-it-risques-de-marche-f-h"}, timeout=20)
        print(rr.status_code, u[len(BASE):], len(rr.text), sh(rr.text, 400))
    ns = requests.get(f"{BASE}/", headers=UA, timeout=20).json()
    print("namespaces:", ns.get("namespaces"))
    routes = [r for r in ns.get("routes", {}) if "bpce" in r]
    print("routes bpce:", routes[:40])
except Exception as e:
    print("ERR natixis", type(e).__name__, str(e)[:200])
print("FIN ROUND7")
