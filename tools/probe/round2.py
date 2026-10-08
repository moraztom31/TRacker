"""Tour 2 : noms de site Workday, API Eightfold/Jibe, Oracle, SuccessFactors, BNP avec empreinte TLS navigateur."""
import json
import re
from concurrent.futures import ThreadPoolExecutor

import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
      "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
T = 10


def wd_sites(t):
    c = [t, t.capitalize(), t.upper(), "External", "external", "Careers", "careers", "Careers_External", f"{t}_careers",
         f"{t}careers", f"{t}Careers", f"{t.upper()}_Careers", f"{t}_external", f"{t}_External", f"{t}External", "ExternalCareerSite",
         "External_Career_Site", "Global", "jobs", "Jobs", "Campus", "Students", "Early_Careers", "EarlyCareers", "Search",
         f"{t}_jobs", f"{t.upper()}Careers", f"{t}-careers", f"{t}_Careers", f"External_{t}", f"{t.capitalize()}Careers",
         f"{t.capitalize()}_Careers", f"{t.capitalize()}External", "External_Careers", "ExternalSite", "Professional", "Campus_Careers"]
    return list(dict.fromkeys(c))


def wd_api(host, tenant, site):
    try:
        q = requests.post(f"https://{host}/wday/cxs/{tenant}/{site}/jobs", headers={**UA, "Content-Type": "application/json"},
                          json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "intern"}, timeout=T)
        if q.ok:
            return q.json().get("total")
    except Exception:
        pass
    return None


def wd_brute(args):
    tenant, wds = args
    for n in wds:
        host = f"{tenant}.wd{n}.myworkdayjobs.com"
        try:
            r = requests.get(f"https://{host}/", headers=UA, timeout=T, allow_redirects=False)
        except Exception:
            continue
        loc = r.headers.get("location", "")
        hint = ""
        m = re.search(r"myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", loc)
        sites = ([m.group(1)] if m else []) + wd_sites(tenant)
        for s in dict.fromkeys(sites):
            tot = wd_api(host, tenant, s)
            if tot is not None:
                return f"WORKDAY host={host} tenant={tenant} site={s} intern_total={tot}"
        if r.status_code in (200, 301, 302):
            hint = f"(host existe wd{n} status={r.status_code} loc={loc[:60]} mais aucun site trouve)"
            return f"workday? {tenant} {hint}"
    return None


KNOWN = [("kkr", [1]), ("jefferies", [1]), ("nomura", [3]), ("alliancebernstein", [1])]
GUESS = ("wellsfargo vanguard nb neubergerberman franklintempleton nuveen moelis rbc bmo td scotiabank cibc mastercard spgi msci moodys "
         "lseg nasdaq lbg natwestgroup natwest sc unicredit abnamro rabobank vontobel ubp generali dws mizuho smbc mlp bamfunds citadel "
         "twosigma commerzbank bbva intesasanpaolo kbc nordea seb danskebank erstegroup raiffeisen mediobanca caixabank sabadell lgim "
         "mandg janushenderson jupiter ninetyone abrdn aberdeen capitalgroup bnpparibas natixis amundi allianzgi creditsuisse ubs hsbc "
         "evercore lazard moelis pwp piper pipersandler guggenheim raymondjames stifel williamblair cowen tdcowen rbccm "
         "bnymellon northerntrust citizens usbank pnc truist jpmorgan ms morganstanley ey pwc deloitte kpmg "
         "ice theice cme cmegroup tradeweb marketaxess virtu optiver susquehanna sig fiverings oldmission drw "
         "ardian eurazeo tikehau carmignac mirova candriam ostrum axa axaim cic creditmutuel groupama bnpparibascardif").split()

API_TESTS = [
    ("HSBC eightfold", "GET", "https://portal.careers.hsbc.com/api/apply/v2/jobs?domain=hsbc.com&start=0&num=10&query=intern", None),
    ("AXA jibe", "GET", "https://careers.axa.com/api/jobs?limit=5&keywords=intern", None),
    ("BNP bwelcome", "GET", "https://bwelcome.hr.bnpparibas/fr_FR/externalcareers/SearchJobs", None),
    ("BNP bwelcome2", "GET", "https://bwelcome.hr.bnpparibas/fr_FR/externalcareers/SearchJobs/?jobRecordsPerPage=100&jobSort=relevancy", None),
    ("BNP rss", "GET", "https://group.bnpparibas/rss", None),
    ("Pictet SF", "GET", "https://career5.successfactors.eu/career?company=banquepict&career_ns=job_listing_summary&navBarLevel=JOB_SEARCH", None),
    ("EdR oracle", "GET", "https://evht.fa.ocs.oraclecloud.eu/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_2001,limit=5,keyword=stage", None),
    ("Oddo jobs", "GET", "https://www.oddo-bhf.com/discover-our-jobs/", None),
    ("Oddo wp-json", "GET", "https://www.oddo-bhf.com/wp-json/", None),
    ("SocGen taleo", "GET", "https://socgen.taleo.net/careersection/sgcareers/jobsearch.ftl?lang=fr", None),
    ("Nomura careers", "GET", "https://www.nomura.com/careers/early-careers/internship-programs/", None),
    ("Mizuho", "GET", "https://www.mizuhogroup.com/careers", None),
]


def api(t):
    name, method, url, body = t
    try:
        r = requests.request(method, url, headers=UA, timeout=T, json=body)
        txt = r.text
        links = sorted(set(re.findall(r"""href=["']([^"']*(?:job|career|offre|SearchJobs|req_id|opp)[^"']*)["']""", txt, re.I)))[:6]
        return f"{name}: {r.status_code} len={len(txt)} ct={r.headers.get('content-type','')[:30]} body={re.sub(r'\\s+',' ',txt[:260])!r} links={links}"
    except Exception as e:
        return f"{name}: ERR {type(e).__name__} {str(e)[:80]}"


def cffi():
    out = []
    try:
        from curl_cffi import requests as cr
    except Exception as e:
        return [f"curl_cffi indisponible {e}"]
    for u in ["https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/stage", "https://group.bnpparibas/en/careers/jobs",
              "https://group.bnpparibas/rss", "https://www.ubs.com/global/en/careers/search-jobs.html",
              "https://www.jobteaser.com/fr/companies/oddobhf/job-offers"]:
        for imp in ("chrome124", "safari17_0"):
            try:
                r = cr.get(u, impersonate=imp, timeout=20)
                t = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I)
                out.append(f"CFFI {imp} {u} -> {r.status_code} len={len(r.text)} title={(t.group(1).strip()[:60] if t else '-')}")
            except Exception as e:
                out.append(f"CFFI {imp} {u} -> ERR {type(e).__name__} {str(e)[:70]}")
    return out


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=16) as pool:
        for r in pool.map(wd_brute, KNOWN):
            print("KNOWN", r)
        for r in pool.map(api, API_TESTS):
            print(r)
    for line in cffi():
        print(line)
    wds = [1, 3, 5, 12, 103, 501]
    with ThreadPoolExecutor(max_workers=24) as pool:
        for r in pool.map(wd_brute, [(g, wds) for g in dict.fromkeys(GUESS)]):
            if r:
                print(r)
    print("FIN ROUND2")
