"""Tour 5 : structure exacte de la page BNP (via TLS navigateur) et du site UBS."""
import collections
import hashlib
import re

import requests
from curl_cffi import requests as cr

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


print("##### BNP structure")
try:
    pages = {}
    for page in (1, 2):
        u = "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/stage" + (f"?page={page}" if page > 1 else "")
        pages[page] = cr.get(u, impersonate="chrome124", timeout=30).text
    t = pages[1]
    main = t[t.index("<main"):] if "<main" in t else t
    print("page1 vs page2 main identiques:", hashlib.md5(main.encode()).hexdigest() == hashlib.md5((pages[2][pages[2].index('<main'):] if '<main' in pages[2] else pages[2]).encode()).hexdigest())
    cls = collections.Counter(c for m in re.findall(r'class="([^"]+)"', main) for c in m.split() if re.search(r"offer|offre|job|card|result|item|list|teaser", c, re.I))
    print("classes:", cls.most_common(25))
    print("H/F ou F/H dans le texte:", len(re.findall(r"[HF]\s*/\s*[FH]", main)))
    i = re.search(r"[HF]\s*/\s*[FH]", main)
    if i:
        print("CONTEXTE H/F:", sh(main[max(0, i.start() - 900):i.start() + 900], 1900))
    api = sorted(set(re.findall(r"""["'](/(?:api|jobs|emploi-carriere/api|offres)[^"'\s]{3,120})["']""", t)))[:15]
    print("chemins api:", api)
    print("scripts:", [s for s in re.findall(r'<script[^>]+src="([^"]+)"', t) if re.search(r"job|offre|search|app|main", s, re.I)][:8])
    print("vie/graduate liens:", [l for l in dict.fromkeys(re.findall(r'href="([^"]+)"', t)) if re.search(r"/(vie|alternance|graduate)", l)][:6])
    anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', main, re.S)
    deep = [(h, sh(re.sub(r"<[^>]+>", " ", x), 90)) for h, x in anchors if h.count("/") >= 3 and not re.search(r"toutes-offres-emploi/(cdi|cdd|stage|vie|alternance|job-etudiant|graduate|zero|controle)", h)]
    print("ancres profondes (main):", len(deep))
    for h, x in deep[:25]:
        print("  ", h[:120], "|", x)
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:200])

print("\n##### UBS structure")
try:
    r = requests.get("https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid=5012", headers=UA, timeout=30)
    t = r.text
    print(r.status_code, len(t), "contient titre job connu:", "Corporate Actions Processing" in t)
    for kw in ("Intern in Corporate Actions", "encryptedSessionValue", "EncryptedSessionValue", "ProcessSortAndShowMoreJobs", "MatchedJobs", "jobid=352331"):
        for m in list(re.finditer(re.escape(kw), t))[:1]:
            print(f"[{kw}]", sh(t[max(0, m.start() - 300):m.start() + 500], 800))
    ss = re.findall(r"siteid=(\d+)", t)
    print("siteids:", collections.Counter(ss).most_common(6))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:150])
print("FIN ROUND5")
