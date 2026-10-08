"""UBS : le portail etudiants (siteid=5131, LinkID=15232) contient-il les stages ?"""
import json
import re
import sys

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, ".")
from tracker.sources import UA, brassring  # noqa: E402


def sh(s, n=200):
    return re.sub(r"\s+", " ", str(s))[:n]


for site in (5131, 5012, 5155):
    home = f"https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid={site}"
    s = requests.Session()
    s.headers.update(UA)
    r = s.get(home, timeout=40)
    soup = BeautifulSoup(r.text, "html.parser")
    hidden = {(i.get("id") or i.get("name")): (i.get("value") or "") for i in soup.find_all("input", type="hidden")}
    print(f"\n===== siteid={site} : {r.status_code} {len(r.text)} octets, titre: {sh(soup.title.string if soup.title else '', 80)}")
    h = {"Content-Type": "application/json; charset=UTF-8", "Accept": "*/*", "X-Requested-With": "XMLHttpRequest", "Referer": home, "Origin": "https://jobs.ubs.com",
         "RFT": hidden.get("__RequestVerificationToken", "")}
    for q in ("", "intern", "internship", "stage", "graduate", "analyst"):
        body = {"PartnerId": "25008", "SiteId": str(site), "Keyword": q, "Location": "", "KeywordCustomSolrFields": "FORMTEXT2,FORMTEXT21,AutoReq,Department,JobTitle",
                "LocationCustomSolrFields": "FORMTEXT2,FORMTEXT23,Location", "FacetFilterFields": None, "TurnOffHttps": False, "Latitude": 0, "Longitude": 0,
                "PowerSearchOptions": {"PowerSearchOption": []}, "encryptedsessionvalue": hidden.get("CookieValue", "")}
        rr = s.post("https://jobs.ubs.com/TgNewUI/Search/Ajax/MatchedJobs", headers=h, data=json.dumps(body), timeout=40)
        if not rr.ok or not rr.text.lstrip().startswith("{"):
            print(f"  mot-clé {q!r:<13} -> HTTP {rr.status_code} {sh(rr.text, 80)}")
            continue
        j = rr.json()
        jobs = (j.get("Jobs") or {}).get("Job") or []
        titles = [next((x["Value"] for x in jb.get("Questions", []) if x["QuestionName"] == "jobtitle"), "?")[:45] for jb in jobs[:4]]
        print(f"  mot-clé {q!r:<13} -> JobsCount={j.get('JobsCount')} lus={len(jobs)} ex: {titles}")
        if q == "" and jobs:
            print("     champs de la 1re offre:", sorted({x['QuestionName'] for x in jobs[0].get('Questions', [])}))
            print("     lieu(x):", [next((x['Value'] for x in jb.get('Questions', []) if x['QuestionName'] == 'formtext23'), None) for jb in jobs[:3]])

print("\n===== collecteur réel sur le site 5131")
try:
    jobs = brassring({"company": "UBS", "host": "jobs.ubs.com", "partner": 25008, "site": 5131, "queries": ["", "intern"], "location_fields": ["formtext23"]})
    print(len(jobs), "offres")
    for j in jobs[:8]:
        print("  -", j["title"][:60], "|", j["location"][:50], "|", j["url"][-30:])
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:200])
print("FIN")
