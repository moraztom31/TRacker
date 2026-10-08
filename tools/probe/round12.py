"""Tour 12 : couverture reelle du site carriere Credit Agricole (filiales dont Amundi) et pagination UBS."""
import collections
import json
import re
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}
BASE = "https://groupecreditagricole.jobs/fr/nos-offres/"


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


def url(n):
    return BASE if n == 1 else f"{BASE}page/{n}/"


print("##### Credit Agricole : page 1")
r = requests.get(BASE, headers=UA, timeout=30)
t = r.text
soup = BeautifulSoup(t, "html.parser")
print(r.status_code, len(t), "title:", sh(soup.title.string if soup.title else "", 100))
print("compteurs:", re.findall(r"(\d[\d\s.,]*)\s*(?:offres?|résultats?|postes?)", t)[:8])
pages = [int(x) for x in re.findall(r"/nos-offres/page/(\d+)/", t)]
print("pagination: pages max vues", max(pages) if pages else None, sorted(set(pages))[:15])
cards = [a for a in soup.find_all("a", href=True) if "/nos-offres-emploi/" in a["href"]]
print("cartes page 1:", len(cards))
if cards:
    print("carte 1 HTML:", sh(cards[0].parent.parent if cards[0].parent else cards[0], 900))
    print("exemples:", [sh(a.get_text(" ", strip=True), 130) for a in cards[:4]])
print("selects/inputs filtres:", [(x.get("name"), [o.get("value") for o in x.find_all("option")][:12]) for x in soup.find_all("select")][:6])
print("inputs:", [(i.get("name"), i.get("type"), (i.get("value") or "")[:20]) for i in soup.find_all("input")][:15])
print("liens avec ?:", [a["href"][:110] for a in soup.find_all("a", href=True) if "?" in a["href"] and "nos-offres" in a["href"]][:10])

print("\n##### Credit Agricole : exploration des pages")


def fetch(n):
    try:
        rr = requests.get(url(n), headers=UA, timeout=30)
        if rr.status_code != 200:
            return n, rr.status_code, []
        sp = BeautifulSoup(rr.text, "html.parser")
        out = []
        for a in sp.find_all("a", href=True):
            if "/nos-offres-emploi/" in a["href"]:
                out.append((a["href"], sh(a.get_text(" ", strip=True), 200)))
        return n, 200, out
    except Exception as e:
        return n, type(e).__name__, []


with ThreadPoolExecutor(max_workers=8) as pool:
    res = list(pool.map(fetch, range(1, 81)))
nonempty = [(n, st, o) for n, st, o in res if o]
print("pages avec offres:", len(nonempty), "| derniere page non vide:", nonempty[-1][0] if nonempty else None)
print("statuts des pages vides:", collections.Counter((st) for n, st, o in res if not o))
allo = {}
for n, st, o in nonempty:
    for h, txt in o:
        allo.setdefault(h, txt)
print("offres uniques:", len(allo))
ents = ["Amundi", "CACIB", "Crédit Agricole CIB", "CA CIB", "LCL", "Indosuez", "CACEIS", "Assurances", "Crédit Agricole S.A.", "Crédit Agricole Consumer", "Leasing", "Immobilier", "Payment", "Caisse Régionale", "Caisse régionale"]
cnt = {e: sum(1 for x in allo.values() if e.lower() in x.lower()) for e in ents}
print("filiales dans le texte des cartes:", {k: v for k, v in cnt.items() if v})
st = [x for x in allo.values() if re.search(r"\b(stage|stagiaire|intern|internship|alternan|apprenti)", x, re.I)]
print("offres stage/alternance dans le texte:", len(st))
for x in list(allo.values())[:6]:
    print("  -", x)
for x in st[:8]:
    print("  stage:", x)
