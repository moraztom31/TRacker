"""Detecte la plateforme de recrutement de chaque entreprise et compte les offres 'intern'."""
import re
from concurrent.futures import ThreadPoolExecutor

import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/129.0 Safari/537.36"}
T = 8

NAMES = {
    "Natixis": ["natixis", "natixisim"], "BPCE": ["bpce", "groupebpce"], "HSBC": ["hsbc"], "UBS": ["ubs"],
    "Pictet": ["pictet", "banquepictet"], "Edmond de Rothschild": ["edr", "edmondderothschild", "edmond-de-rothschild"],
    "Oddo BHF": ["oddobhf", "oddo-bhf", "oddo"], "Nomura": ["nomura", "nomuraholdings"], "KKR": ["kkr"],
    "Jefferies": ["jefferies"], "AllianceBernstein": ["alliancebernstein", "ab"], "BNP Paribas": ["bnpparibas", "bnp", "BNPParibas"],
    "BNP Paribas AM": ["bnpparibasam", "bnpparibasassetmanagement"], "Credit Mutuel": ["creditmutuel", "cmcic", "cic"],
    "La Banque Postale": ["labanquepostale", "lbp", "labanquepostaleassetmanagement"], "AXA IM": ["axaim", "axa", "axainvestmentmanagers"],
    "Generali": ["generali", "generaliinvestments"], "Allianz GI": ["allianzgi", "allianz"], "DWS": ["dws"],
    "UBP": ["ubp", "unionbancairepriveeubp"], "Vontobel": ["vontobel"], "Mirova": ["mirova"], "Tikehau": ["tikehau", "tikehaucapital"],
    "Eurazeo": ["eurazeo"], "Carmignac": ["carmignac"], "Lazard": ["lazard"], "Citadel": ["citadel", "citadelsecurities"],
    "Two Sigma": ["twosigma"], "DE Shaw": ["deshaw", "de-shaw"], "Millennium": ["millennium", "mlp"], "Balyasny": ["balyasny", "bamfunds"],
    "Jane Street": ["janestreet"], "Susquehanna": ["sig", "susquehanna"], "Wells Fargo": ["wellsfargo"], "Mizuho": ["mizuho", "mizuhoemea"],
    "SMBC": ["smbc", "smbcgroup"], "Standard Chartered": ["standardchartered", "sc"], "Commerzbank": ["commerzbank"],
    "UniCredit": ["unicredit"], "Intesa Sanpaolo": ["intesasanpaolo", "intesa"], "ABN AMRO": ["abnamro"], "Rabobank": ["rabobank"],
    "KBC": ["kbc"], "Nordea": ["nordea"], "SEB": ["seb"], "Danske": ["danskebank", "danske"], "Vanguard": ["vanguard"],
    "Neuberger Berman": ["nb", "neubergerberman"], "Franklin Templeton": ["franklintempleton", "franklinresources"],
    "Nuveen": ["nuveen"], "Piper Sandler": ["pipersandler"], "William Blair": ["williamblair"], "Moelis": ["moelis"],
    "Centerview": ["centerview"], "Perella Weinberg": ["pwp", "perellaweinberg"], "Guggenheim": ["guggenheim", "guggenheimpartners"],
    "Raymond James": ["raymondjames"], "Stifel": ["stifel"], "RBC": ["rbc"], "BMO": ["bmo"], "Scotiabank": ["scotiabank"],
    "CIBC": ["cibc"], "TD": ["td"], "AQR": ["aqr"], "Winton": ["winton"], "Brevan Howard": ["brevanhoward"], "Virtu": ["virtu"],
    "Five Rings": ["fiverings"], "DRW": ["drw"], "Old Mission": ["oldmission"], "GSA": ["gsacapital"], "Citi": ["citi", "citigroup"],
    "Crédit Agricole": ["creditagricole", "ca-cib", "cacib"], "Amundi": ["amundi"], "Candriam": ["candriam"], "Ostrum": ["ostrum"],
    "Bank of America": ["bofa", "bankofamerica"], "Capital Group": ["capitalgroup"], "Fidelity": ["fidelity"], "Aberdeen": ["aberdeen", "abrdn"],
    "Legal & General": ["lgim", "legalandgeneral"], "M&G": ["mandg", "mng"], "Janus Henderson": ["janushenderson"], "Jupiter": ["jupiter"],
    "Ninety One": ["ninetyone"], "Lombard Odier": ["lombardodier"], "Pictet AM": ["pictetam"], "Syz": ["syz"], "Mediobanca": ["mediobanca"],
    "Banco Sabadell": ["sabadell"], "BBVA": ["bbva"], "CaixaBank": ["caixabank"], "Erste": ["erstegroup", "erste"], "Raiffeisen": ["raiffeisen", "rbinternational"],
    "SocGen Luxembourg": ["societegenerale", "sg"], "Natwest": ["natwest", "rbs"], "Lloyds": ["lloyds", "lloydsbankinggroup"], "Santander": ["santander"],
    "Nasdaq": ["nasdaq"], "LSEG": ["lseg"], "Euronext": ["euronext"], "ICE": ["ice", "theice"], "CME": ["cme", "cmegroup"],
    "S&P Global": ["spglobal"], "Moody's": ["moodys"], "MSCI": ["msci"], "Bloomberg": ["bloomberg"], "Visa": ["visa"], "Mastercard": ["mastercard"],
    "Oliver Wyman": ["oliverwyman"], "McKinsey": ["mckinsey"], "BCG": ["bcg"], "Bain": ["bain"], "Roland Berger": ["rolandberger"],
    "Tradeweb": ["tradeweb"], "MarketAxess": ["marketaxess"], "Stripe": ["stripe"], "Revolut": ["revolut"], "Qonto": ["qonto"], "Ledger": ["ledger"],
}


def get(url, **kw):
    try:
        return requests.get(url, headers=UA, timeout=T, **kw)
    except Exception:
        return None


def greenhouse(s):
    for host in ("boards-api.greenhouse.io", "boards-api.eu.greenhouse.io"):
        r = get(f"https://{host}/v1/boards/{s}/jobs")
        if r is not None and r.ok:
            try:
                jobs = r.json().get("jobs", [])
            except Exception:
                continue
            n = sum(1 for j in jobs if re.search(r"intern|stage|summer|trainee|placement", j.get("title", ""), re.I))
            return f"greenhouse slug={s} region={'eu' if '.eu.' in host else 'us'} total={len(jobs)} intern={n}"


def lever(s):
    r = get(f"https://api.lever.co/v0/postings/{s}?mode=json")
    if r is not None and r.ok:
        try:
            j = r.json()
        except Exception:
            return None
        if isinstance(j, list) and j:
            return f"lever slug={s} total={len(j)}"


def smartrecruiters(s):
    r = get(f"https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=1")
    if r is not None and r.ok:
        try:
            t = r.json().get("totalFound", 0)
        except Exception:
            return None
        if t:
            return f"smartrecruiters id={s} total={t}"


def workable(s):
    r = get(f"https://apply.workable.com/api/v1/widget/accounts/{s}")
    if r is not None and r.ok:
        try:
            j = r.json().get("jobs", [])
        except Exception:
            return None
        if j:
            return f"workable slug={s} total={len(j)}"


def ashby(s):
    r = get(f"https://api.ashbyhq.com/posting-api/job-board/{s}")
    if r is not None and r.ok:
        try:
            j = r.json().get("jobs", [])
        except Exception:
            return None
        if j:
            return f"ashby slug={s} total={len(j)}"


def workday(s):
    for n in (1, 3, 5, 12, 103, 501):
        host = f"{s}.wd{n}.myworkdayjobs.com"
        r = get(f"https://{host}/", allow_redirects=True)
        if r is None or not r.ok:
            continue
        m = re.search(r"myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", r.url)
        site = m.group(1) if m else None
        if not site or site in ("wday", "login"):
            continue
        try:
            q = requests.post(f"https://{host}/wday/cxs/{s}/{site}/jobs", headers={**UA, "Content-Type": "application/json"},
                              json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "intern"}, timeout=T)
            tot = q.json().get("total") if q.ok else f"api{q.status_code}"
        except Exception as e:
            tot = type(e).__name__
        return f"workday host={host} tenant={s} site={site} intern_total={tot}"


def probe(item):
    name, slugs = item
    found = []
    for s in slugs:
        for fn in (greenhouse, lever, smartrecruiters, workable, ashby, workday):
            r = fn(s) if fn is not workday else fn(s.lower())
            if r:
                found.append(r)
    return name, found


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=24) as pool:
        for name, found in pool.map(probe, NAMES.items()):
            for f in found:
                print(f"{name:<22} {f}")
    print("FIN ATS")
