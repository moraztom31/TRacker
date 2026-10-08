"""Teste les sites bloques (BNP, HSBC...) : statut, entetes, et pistes d'API dans le HTML."""
import re
from concurrent.futures import ThreadPoolExecutor

import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
URLS = [
    "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/stage",
    "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi",
    "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/rss",
    "https://group.bnpparibas/en/careers/all-job-offers",
    "https://group.bnpparibas/api/jobs",
    "https://bwelcome.hr.bnpparibas/fr_FR/externalcareers",
    "https://bwelcome.hr.bnpparibas/",
    "https://careers.bnpparibas.com/",
    "https://recrutement.natixis.com/",
    "https://recrutement.natixis.com/offre-de-emploi/liste-offres.aspx",
    "https://careers.natixis.com/",
    "https://www.groupebpce.com/rejoignez-nous/offres-emploi",
    "https://portal.careers.hsbc.com/careers",
    "https://portal.careers.hsbc.com/api/jobs",
    "https://www.hsbc.com/careers",
    "https://www.ubs.com/global/en/careers/search-jobs.html",
    "https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid=5012",
    "https://www.edmond-de-rothschild.com/fr/carrieres",
    "https://www.pictet.com/careers",
    "https://career5.successfactors.eu/career?company=banquepict",
    "https://oddo-bhf.talent-soft.com/",
    "https://oddo-bhf.talent-soft.com/offre-de-emploi/liste-offres.aspx",
    "https://www.oddo-bhf.com/en/careers",
    "https://www.jobteaser.com/fr/companies/oddobhf/job-offers",
    "https://careers.societegenerale.com/fr/Technical/toutes-les-offres",
    "https://www.nomura.com/careers/early-careers/internship-programs/",
    "https://www.credit-agricole.com/carrieres",
    "https://www.cic.fr/fr/carrieres.html",
    "https://www.labanquepostale.com/carrieres.html",
    "https://careers.axa.com/",
    "https://www.amundi.com/institutional/careers",
]


def probe(u):
    try:
        r = requests.get(u, headers=UA, timeout=12, allow_redirects=True)
    except Exception as e:
        return u, f"ERR {type(e).__name__}: {str(e)[:90]}"
    t = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I)
    srv = r.headers.get("server", "")
    hints = sorted(set(re.findall(r"""["'(]((?:https?:)?//[^"'\s)]*(?:api|json|jobs|search|offers?|rss|feed|taleo|workday|successfactors|talent-?soft|smartrecruiters|oraclecloud|phenom|eightfold|icims|jobvite|avature|beamery)[^"'\s)]*)""", r.text, re.I)))[:8]
    return u, f"{r.status_code} len={len(r.text)} server={srv} final={r.url[:90]} title={(t.group(1).strip()[:70] if t else '-')} hints={hints}"


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=12) as pool:
        for u, res in pool.map(probe, URLS):
            print(u, "->", res)
    print("FIN SITES")
