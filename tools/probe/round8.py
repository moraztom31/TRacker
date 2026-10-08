"""Tour 8 : UBS avec la bonne valeur de session, et une offre Natixis complete (lieu, contrat)."""
import json
import re

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


print("##### UBS")
try:
    HOME = "https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid=5012"
    s = requests.Session()
    s.headers.update(UA)
    html = s.get(HOME, timeout=40).text
    hidden = {(i.get("id") or i.get("name")): (i.get("value") or "") for i in BeautifulSoup(html, "html.parser").find_all("input", type="hidden")}
    for enc_name in ("CookieValue", "sessionid", "SIDValue"):
        for rft in (True, False):
            body = {"PartnerId": "25008", "SiteId": "5012", "Keyword": "intern", "Location": "", "KeywordCustomSolrFields": "FORMTEXT2,FORMTEXT21,AutoReq,Department,JobTitle",
                    "LocationCustomSolrFields": "FORMTEXT2,FORMTEXT23,Location", "FacetFilterFields": None, "TurnOffHttps": False, "Latitude": 0, "Longitude": 0,
                    "PowerSearchOptions": {"PowerSearchOption": []}, "encryptedsessionvalue": hidden.get(enc_name, "")}
            h = {"Content-Type": "application/json;charset=UTF-8", "Accept": "application/json, text/plain, */*", "X-Requested-With": "XMLHttpRequest",
                 "Referer": HOME, "Origin": "https://jobs.ubs.com"}
            if rft:
                h["RFT"] = hidden.get("rfToken", "")
            rr = s.post("https://jobs.ubs.com/TgNewUI/Search/Ajax/MatchedJobs", headers=h, data=json.dumps(body), timeout=40)
            print(enc_name, "RFT" if rft else "no-RFT", rr.status_code, len(rr.text), sh(rr.text, 120))
            if rr.ok and rr.text.lstrip().startswith("{"):
                j = rr.json()
                jobs = (j.get("Jobs") or {}).get("Job") or []
                print("  cles:", list(j.keys())[:20], "| Jobs cles:", list((j.get("Jobs") or {}).keys()), "| nb:", len(jobs))
                for k, v in j.items():
                    if k != "Jobs" and not isinstance(v, (dict, list)):
                        print("   ", k, "=", sh(v, 80))
                if jobs:
                    q = {x["QuestionName"]: x["Value"] for x in jobs[0].get("Questions", [])}
                    print("  1er job:", sh(q, 700), "| Link:", jobs[0].get("Link"))
                    print("  titres:", [next((x["Value"] for x in jb.get("Questions", []) if x["QuestionName"] == "jobtitle"), "?")[:50] for jb in jobs[:8]])
                raise SystemExit(0) if False else None
                break
        else:
            continue
        break
except Exception as e:
    print("ERR UBS", type(e).__name__, str(e)[:200])

print("\n##### Natixis offre complete")
try:
    BASE = "https://recrutement.natixis.com/app/wp-json"
    rr = requests.get(f"{BASE}/wp/v2/job?per_page=100&page=1&lang=fr", headers=UA, timeout=30)
    print(rr.status_code, "total", rr.headers.get("X-WP-Total"), "pages", rr.headers.get("X-WP-TotalPages"), "len", len(rr.text))
    jobs = rr.json()
    j = jobs[0]
    print("cles:", list(j.keys()))
    print("class_list:", j.get("class_list"))
    for k in ("acf", "meta", "yoast_head_json", "_links"):
        if k in j:
            print(k, sh(json.dumps(j[k], ensure_ascii=False), 700))
    st = [x for x in jobs if re.search(r"tax_contract-(stage|internship)", " ".join(x.get("class_list", [])))]
    print("stage via taxonomie contrat sur la page 1:", len(st), "/", len(jobs))
    import collections
    c = collections.Counter(t for x in jobs for t in x.get("class_list", []) if t.startswith("tax_contract"))
    print("contrats:", c.most_common(12))
    loc = collections.Counter(t for x in jobs for t in x.get("class_list", []) if re.match(r"tax_(city|ville|location|place|geo|region|country|pays|lieu)", t))
    print("lieux:", loc.most_common(12))
    print("toutes taxonomies:", sorted({t.split('-')[0] for x in jobs for t in x.get('class_list', []) if t.startswith('tax_')}))
    print("exemple titres:", [x["title"]["rendered"] for x in jobs[:5]])
except Exception as e:
    print("ERR natixis", type(e).__name__, str(e)[:200])
print("FIN ROUND8")
