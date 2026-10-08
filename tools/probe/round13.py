"""Tour 13 : pagination du portail Oddo (altays)."""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}
B = "https://recrutement.altays-progiciels.com/oddo/fr/offres.html"


def ids(t):
    return re.findall(r"offres/[a-z0-9-]*?-(\d{5,})\.html", t)


for name, kw in {"page=2 simple": {}, "page=2 XHR": {"X-Requested-With": "XMLHttpRequest"},
                 "page=2 XHR+referer": {"X-Requested-With": "XMLHttpRequest", "Referer": "https://recrutement.altays-progiciels.com/oddo/fr/recherche.html"}}.items():
    for page in (1, 2, 3):
        r = requests.get(B, params={"page": page}, headers={**UA, **kw}, timeout=30)
        i = ids(r.text)
        print(name, "page", page, r.status_code, len(r.text), "ids:", len(set(i)), i[:3], "| debut:", re.sub(r"\s+", " ", r.text[:80]))
r = requests.get(B, params={"page": 2}, headers={**UA, "X-Requested-With": "XMLHttpRequest"}, timeout=30)
print("liens page2:", re.findall(r'href="([^"]+)"', r.text)[:6])
r = requests.get("https://recrutement.altays-progiciels.com/oddo/fr/recherche.html", headers=UA, timeout=30)
print("recherche.html: pagination/scripts:", re.findall(r"(?:data-page|page=|nombre|offres\.html[^\"']{0,40})[^\"'<>\s]{0,40}", r.text)[:12])
js = re.findall(r'src="([^"]*job-list[^"]*)"', r.text)
print("js:", js)
if js:
    u = js[0] if js[0].startswith("http") else "https://recrutement.altays-progiciels.com" + js[0]
    t = requests.get(u, headers=UA, timeout=30).text
    print("job-list.js len", len(t), "| page/offres refs:", re.findall(r".{60}offres\.html.{80}", t)[:3], re.findall(r".{50}nombre\.json.{80}", t)[:2])
    print("params:", re.findall(r"[?&]page=|page:\s*\w+|\.page\b.{0,40}", t)[:6])
print("FIN ROUND13")
