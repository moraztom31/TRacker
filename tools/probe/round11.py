"""Tour 11 : champs d'une offre UBS (BrassRing) avec les bons en-tetes."""
import json
import re

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}
HOME = "https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid=5012"


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


s = requests.Session()
s.headers.update(UA)
html = s.get(HOME, timeout=40).text
hidden = {(i.get("id") or i.get("name")): (i.get("value") or "") for i in BeautifulSoup(html, "html.parser").find_all("input", type="hidden")}
h = {"Content-Type": "application/json; charset=UTF-8", "Accept": "*/*", "X-Requested-With": "XMLHttpRequest", "Referer": HOME, "Origin": "https://jobs.ubs.com",
     "RFT": hidden.get("__RequestVerificationToken", "")}
for q in ("intern", "stage", "graduate"):
    body = {"PartnerId": "25008", "SiteId": "5012", "Keyword": q, "Location": "", "KeywordCustomSolrFields": "FORMTEXT2,FORMTEXT21,AutoReq,Department,JobTitle",
            "LocationCustomSolrFields": "FORMTEXT2,FORMTEXT23,Location", "FacetFilterFields": None, "TurnOffHttps": False, "Latitude": 0, "Longitude": 0,
            "PowerSearchOptions": {"PowerSearchOption": []}, "encryptedsessionvalue": hidden.get("CookieValue", "")}
    r = s.post("https://jobs.ubs.com/TgNewUI/Search/Ajax/MatchedJobs", headers=h, data=json.dumps(body), timeout=40)
    print(q, r.status_code, len(r.text), sh(r.text, 100))
    if r.ok and r.text.lstrip().startswith("{"):
        j = r.json()
        jobs = (j.get("Jobs") or {}).get("Job") or []
        print("  cles:", list(j.keys())[:20], "| Jobs cles:", list((j.get("Jobs") or {}).keys()), "| nb:", len(jobs))
        for k, v in j.items():
            if k != "Jobs" and not isinstance(v, (dict, list)):
                print("    ", k, "=", sh(v, 80))
        if jobs and q == "intern":
            print("  cles job:", list(jobs[0].keys()))
            for x in jobs[0].get("Questions", []):
                print("    ", x.get("QuestionName"), "=", sh(x.get("Value"), 80))
            print("  Link:", jobs[0].get("Link"))
            print("  titres:", [next((x["Value"] for x in jb.get("Questions", []) if x["QuestionName"] == "jobtitle"), "?")[:55] for jb in jobs[:10]])
print("FIN ROUND11")
