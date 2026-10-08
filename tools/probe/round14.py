"""Tour 14 : les listes sont-elles triees de la plus recente a la plus ancienne ? (CA, BNP, Oddo, BPCE)"""
import re

import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cr

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}


def dates(t):
    out = re.findall(r'"datePosted"\s*:\s*"([^"]+)"', t)
    out += re.findall(r'(?:Publi[ée]e?|Mise? en ligne|Date de publication|Posted)[^<\d]{0,30}(\d{1,2}[/.\- ]\d{1,2}[/.\- ]\d{2,4}|\d{4}-\d\d-\d\d)', t, re.I)
    out += re.findall(r'<time[^>]+datetime="([^"]+)"', t)
    return out[:3]


def get(u, impersonate=None):
    return (cr.get(u, impersonate="chrome124", timeout=30) if impersonate else requests.get(u, headers=UA, timeout=30)).text


print("##### Credit Agricole")
for page in (1, 15, 35):
    u = "https://groupecreditagricole.jobs/fr/nos-offres/" + ("" if page == 1 else f"page/{page}/")
    sp = BeautifulSoup(get(u), "html.parser")
    links = [a["href"] for a in sp.find_all("a", href=True) if "/nos-offres-emploi/" in a["href"]]
    d = dates(get(links[0])) if links else None
    print("page", page, len(links), links[0][-70:] if links else None, "dates:", d)
print("##### BNP")
for page in (1, 12, 27):
    u = "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/stage" + ("" if page == 1 else f"?page={page}")
    t = get(u, True)
    links = re.findall(r'href="(/emploi-carriere/offre-emploi/[^"]+)"', t)
    d = dates(get("https://group.bnpparibas" + links[0], True)) if links else None
    print("page", page, len(links), links[0][-60:] if links else None, "dates:", d)
print("##### Oddo")
for page in (1, 10, 24):
    t = get("https://recrutement.altays-progiciels.com/oddo/fr/offres.html?page=%d" % page)
    links = re.findall(r'href="(/oddo/fr/offres/[^"?]+)', t)
    d = dates(get("https://recrutement.altays-progiciels.com" + links[0])) if links else None
    print("page", page, len(links), links[0][-60:] if links else None, "dates:", d)
print("##### BPCE (dates de l'API)")
for page in (1, 8, 15):
    r = requests.get("https://recrutement.bpce.fr/app/wp-json/wp/v2/job", params={"per_page": 100, "page": page}, headers=UA, timeout=30)
    j = r.json()
    print("page", page, j[0]["date"], "...", j[-1]["date"])
print("FIN ROUND14")
