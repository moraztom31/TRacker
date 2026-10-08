"""Un collecteur par plateforme ATS. Chaque collecteur renvoie une liste de dicts :
{id, company, title, location, url, posted}"""
import re
import warnings

import requests
from bs4 import XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}
TIMEOUT = 15


def _get(url, impersonate=None, **kw):
    """impersonate="chrome124" : requête avec l'empreinte TLS d'un vrai navigateur (curl_cffi).
    Nécessaire pour les sites protégés par Akamai (BNP Paribas, UBS), qui rejettent python-requests."""
    if impersonate:
        from curl_cffi import requests as cffi_requests

        r = cffi_requests.get(url, impersonate=impersonate, timeout=TIMEOUT * 2, **kw)
    else:
        r = requests.get(url, headers=UA, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def greenhouse(cfg):
    host = "boards-api.eu.greenhouse.io" if cfg.get("region") == "eu" else "boards-api.greenhouse.io"
    data = _get(f"https://{host}/v1/boards/{cfg['slug']}/jobs").json()
    return [
        {
            "id": f"gh:{cfg['slug']}:{j['id']}",
            "company": cfg["company"],
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "posted": j.get("updated_at", ""),
        }
        for j in data.get("jobs", [])
    ]


def lever(cfg):
    data = _get(f"https://api.lever.co/v0/postings/{cfg['slug']}", params={"mode": "json"}).json()
    return [
        {
            "id": f"lv:{cfg['slug']}:{j['id']}",
            "company": cfg["company"],
            "title": j.get("text", ""),
            "location": (j.get("categories") or {}).get("location", "") or "",
            "url": j.get("hostedUrl", ""),
            "posted": str(j.get("createdAt", "")),
        }
        for j in data
    ]


def smartrecruiters(cfg):
    out, offset = [], 0
    while offset < 500:  # garde-fou
        data = _get(
            f"https://api.smartrecruiters.com/v1/companies/{cfg['id']}/postings",
            params={"limit": 100, "offset": offset},
        ).json()
        content = data.get("content", [])
        for j in content:
            loc = j.get("location") or {}
            out.append(
                {
                    "id": f"sr:{cfg['id']}:{j['id']}",
                    "company": cfg["company"],
                    "title": j.get("name", ""),
                    "location": ", ".join(x for x in [loc.get("city"), (loc.get("country") or "").upper()] if x),
                    "url": f"https://jobs.smartrecruiters.com/{cfg['id']}/{j['id']}",
                    "posted": j.get("releasedDate", ""),
                }
            )
        offset += 100
        if offset >= data.get("totalFound", 0) or not content:
            break
    return out


def workday(cfg):
    """API JSON publique de Workday (myworkdayjobs.com)."""
    base = f"https://{cfg['host']}/wday/cxs/{cfg['tenant']}/{cfg['site']}/jobs"
    seen, out = set(), []
    for q in cfg.get("queries", ["internship", "intern", "stage", "Paris"]):
        for page in range(int(cfg.get("max_pages", 2))):
            r = requests.post(
                base,
                headers={**UA, "Content-Type": "application/json", "Accept": "application/json"},
                json={"appliedFacets": {}, "limit": 20, "offset": page * 20, "searchText": q},
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            posts = r.json().get("jobPostings", [])
            for j in posts:
                path = j.get("externalPath", "")
                if not path or path in seen:
                    continue
                seen.add(path)
                out.append(
                    {
                        "id": f"wd:{cfg['tenant']}:{path}",
                        "company": cfg["company"],
                        "title": j.get("title", ""),
                        "location": j.get("locationsText", ""),
                        "url": f"https://{cfg['host']}/{cfg['site']}{path}",
                        "posted": j.get("postedOn", ""),
                    }
                )
            if len(posts) < 20:
                break
    return out


def oracle_hcm(cfg):
    """API publique Oracle Recruiting Cloud (JP Morgan, Goldman Sachs, Schroders...)."""
    api = f"https://{cfg['host']}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    seen, out = set(), []
    for q in cfg.get("queries", ["intern", "stage"]):
        finder = (
            f"findReqs;siteNumber={cfg['site']},facetsList=LOCATIONS%7CTITLE%7CPOSTING_DATES,"
            f"limit=50,offset=0,keyword={q},sortBy=POSTING_DATES_DESC"
        )
        r = requests.get(
            api,
            params={"onlyData": "true", "expand": "requisitionList.secondaryLocations", "finder": finder},
            headers={**UA, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        items = r.json().get("items") or [{}]
        for j in items[0].get("requisitionList", []) or []:
            rid = str(j.get("Id", ""))
            if not rid or rid in seen:
                continue
            seen.add(rid)
            locs = [j.get("PrimaryLocation") or ""] + [
                x.get("Name", "") for x in (j.get("secondaryLocations") or []) if isinstance(x, dict)
            ]
            out.append(
                {
                    "id": f"or:{cfg['host']}:{rid}",
                    "company": cfg["company"],
                    "title": j.get("Title", ""),
                    "location": " · ".join(x for x in locs if x),
                    "url": f"https://{cfg['host']}/hcmUI/CandidateExperience/en/sites/{cfg['site']}/job/{rid}",
                    "posted": (j.get("PostedDate") or "")[:10],
                }
            )
    return out


def oleeo_feed(cfg):
    """Flux Atom des portails Oleeo / tal.net (Bank of America, Lazard...)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_get(cfg["url"]).text, "html.parser")
    out = []
    for e in soup.find_all("entry"):
        link = e.find("link", attrs={"rel": "alternate"}) or e.find("link")
        href = (link.get("href") if link else "") or ""
        title = e.find("title").get_text(strip=True) if e.find("title") else ""
        content = e.find("content") or e.find("summary")
        text = BeautifulSoup(content.get_text(), "html.parser").get_text(" · ", strip=True) if content else ""
        if not href or not title:
            continue
        out.append(
            {
                "id": f"ol:{href}",
                "company": cfg["company"],
                "title": title,
                "location": text[:220],
                "url": href,
                "posted": e.find("updated").get_text(strip=True)[:10] if e.find("updated") else "",
            }
        )
    return out


def _dig(obj, path):
    if not path:
        return None
    for part in [x for x in (path or "").split(".") if x]:
        obj = obj.get(part) if isinstance(obj, dict) else None
        if obj is None:
            return None
    return obj


def generic_json(cfg):
    """Portail maison qui renvoie du JSON (endpoint trouvé dans l'onglet Réseau du navigateur)."""
    method = cfg.get("method", "GET").upper()
    kw = {"headers": {**UA, **cfg.get("headers", {})}, "timeout": TIMEOUT}
    if method == "POST":
        r = requests.post(cfg["url"], json=cfg.get("body"), **kw)
    else:
        r = requests.get(cfg["url"], params=cfg.get("params"), **kw)
    r.raise_for_status()
    items = _dig(r.json(), cfg.get("items_path", "")) if cfg.get("items_path") else r.json()
    f = cfg["fields"]
    out = []
    for j in items or []:
        jid, url = _dig(j, f.get("id", "")), _dig(j, f.get("url", "")) or ""
        out.append(
            {
                "id": f"gj:{cfg['company']}:{jid or url}",
                "company": cfg["company"],
                "title": str(_dig(j, f.get("title", "")) or ""),
                "location": str(_dig(j, f.get("location", "")) or ""),
                "url": cfg.get("url_prefix", "") + str(url),
                "posted": str(_dig(j, f.get("posted", "")) or ""),
            }
        )
    return out


def generic_html(cfg):
    """Page carrière en HTML simple : sélecteurs CSS dans config.yaml."""
    from urllib.parse import urljoin

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_get(cfg["url"]).text, "html.parser")
    out = []
    for el in soup.select(cfg["item"]):
        a = el.select_one(cfg.get("link", "a")) or el
        href = urljoin(cfg["url"], a.get("href", ""))
        t = el.select_one(cfg["title"]) if cfg.get("title") else a
        loc = el.select_one(cfg["location"]) if cfg.get("location") else None
        out.append(
            {
                "id": f"gh:{cfg['company']}:{href}",
                "company": cfg["company"],
                "title": t.get_text(" ", strip=True) if t else "",
                "location": loc.get_text(" ", strip=True) if loc else "",
                "url": href,
                "posted": "",
            }
        )
    return out


def _container(a, link_contains):
    """Remonte jusqu'au bloc qui contient UNE seule offre (la 'carte')."""
    node = a
    for _ in range(4):
        parent = node.parent
        if parent is None:
            break
        hrefs = {x["href"] for x in parent.find_all("a", href=True) if link_contains in x["href"]}
        if len(hrefs) > 1:
            break
        node = parent
    return node


def _stable_id(cfg, href):
    """Identifiant stable : certains sites (Oleeo) mettent un code de session dans l'URL."""
    if cfg.get("id_regex"):
        m = re.search(cfg["id_regex"], href)
        if m:
            return f"hl:{cfg['company']}:{m.group(1)}"
    return f"hl:{href}"


def html_links(cfg):
    """Liste d'offres rendue côté serveur (BNP, SG, Crédit Agricole, Barclays, Citi...).
    Repère les liens dont l'URL contient `link_contains`. Titre = premier bloc de texte
    du lien qui n'est pas un simple type de contrat ; tout le reste de la carte
    (lieu, contrat, entité, métier) va dans `location` et sert aux filtres."""
    from urllib.parse import urljoin

    from bs4 import BeautifulSoup

    labels = {"stage", "cdi", "cdd", "vie", "v.i.e", "alternance", "job étudiant", "internship", "nouveau", "new"}
    seen, out = set(), []
    for page in range(1, int(cfg.get("pages", 1)) + 1):
        if page == 1:
            url = cfg["url"]
        elif cfg.get("page_url"):
            url = cfg["page_url"].format(page=page)
        else:
            url = f"{cfg['url']}{'&' if '?' in cfg['url'] else '?'}{cfg.get('page_param', 'page')}={page}"
        soup = BeautifulSoup(_get(url, cfg.get("impersonate")).text, "html.parser")
        found = 0
        for a in soup.find_all("a", href=True):
            if cfg["link_contains"] not in a["href"]:
                continue
            if cfg.get("link_regex") and not re.search(cfg["link_regex"], a["href"]):
                continue
            href = urljoin(url, a["href"]).split("#")[0]
            if href in seen:
                continue
            seen.add(href)
            found += 1
            parts = list(a.stripped_strings)
            title = next((x for x in parts if x.lower().strip(" -–:") not in labels), "")
            if not title:
                continue
            card = _container(a, cfg["link_contains"])
            segs = list(card.stripped_strings) if card is not a else parts
            rest = []
            for x in segs:
                x = x.strip(" ·")
                if x and x != title and x not in rest:
                    rest.append(x)
            location = " · ".join(rest)
            out.append(
                {
                    "id": _stable_id(cfg, href),
                    "company": cfg["company"],
                    "title": title,
                    "location": re.sub(r"(\s*·\s*)+", " · ", location)[:220],
                    "url": href,
                    "posted": "",
                    "internship_source": bool(cfg.get("all_internships")),
                }
            )
        if not found:
            break
    return out


def workable(cfg):
    """API publique Workable (widget)."""
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{cfg['slug']}").json()
    out = []
    for j in data.get("jobs", []) or []:
        code = j.get("shortcode") or j.get("id") or ""
        loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
        out.append(
            {
                "id": f"wk:{cfg['slug']}:{code}",
                "company": cfg["company"],
                "title": j.get("title", ""),
                "location": loc,
                "url": j.get("url") or f"https://apply.workable.com/{cfg['slug']}/j/{code}/",
                "posted": j.get("published_on", ""),
            }
        )
    return out


def rss(cfg):
    """Flux RSS ou Atom d'offres (BNP Paribas, Talentsoft...)."""
    import xml.etree.ElementTree as ET

    from bs4 import BeautifulSoup

    def local(tag):
        return tag.rsplit("}", 1)[-1].lower()

    def child(el, *names):
        for c in el:
            if local(c.tag) in names:
                return c
        return None

    root = ET.fromstring(_get(cfg["url"], cfg.get("impersonate")).content)
    out = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        t_el, l_el = child(el, "title"), child(el, "link")
        title = (t_el.text or "").strip() if t_el is not None else ""
        link = ""
        if l_el is not None:
            link = (l_el.get("href") or l_el.text or "").strip()
        g_el = child(el, "guid", "id")
        d_el = child(el, "description", "summary", "content")
        p_el = child(el, "pubdate", "updated", "published")
        desc = BeautifulSoup(d_el.text or "", "html.parser").get_text(" · ", strip=True) if d_el is not None else ""
        if not title or not link:
            continue
        out.append(
            {
                "id": f"rss:{cfg['company']}:{(g_el.text or '').strip() if g_el is not None and g_el.text else link}",
                "company": cfg["company"],
                "title": title,
                "location": desc[:220],
                "url": link,
                "posted": (p_el.text or "").strip()[:25] if p_el is not None else "",
            }
        )
    return out


def eightfold(cfg):
    """API publique Eightfold (HSBC...) : /api/apply/v2/jobs, 10 offres par page."""
    seen, out = set(), []
    for q in cfg.get("queries", ["intern", "stage"]):
        start = 0
        for _ in range(int(cfg.get("max_pages", 8))):
            data = _get(
                f"https://{cfg['host']}/api/apply/v2/jobs",
                params={"domain": cfg["domain"], "query": q, "start": start, "num": 10, "sort_by": "relevance"},
            ).json()
            pos = data.get("positions") or []
            for j in pos:
                jid = str(j.get("id", ""))
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                out.append(
                    {
                        "id": f"ef:{cfg['host']}:{jid}",
                        "company": cfg["company"],
                        "title": j.get("name", ""),
                        "location": " · ".join(j.get("locations") or [j.get("location") or ""]),
                        "url": j.get("canonicalPositionUrl") or f"https://{cfg['host']}/careers/job/{jid}",
                        "posted": str(j.get("t_create", "")),
                    }
                )
            start += len(pos)
            if not pos or start >= int(data.get("count") or 0):
                break
    return out


def jibe(cfg):
    """API publique Jibe / iCIMS (AXA...) : /api/jobs?keywords=...&page=N."""
    seen, out = set(), []
    for q in cfg.get("queries", ["intern", "stage"]):
        for page in range(1, int(cfg.get("max_pages", 4)) + 1):
            data = _get(f"https://{cfg['host']}/api/jobs", params={"keywords": q, "limit": 100, "page": page}).json()
            jobs = data.get("jobs") or []
            for item in jobs:
                j = item.get("data") or {}
                rid = str(j.get("req_id") or j.get("slug") or "")
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                out.append(
                    {
                        "id": f"jb:{cfg['host']}:{rid}",
                        "company": cfg["company"],
                        "title": j.get("title", ""),
                        "location": ", ".join(x for x in [j.get("city"), j.get("country")] if x) or j.get("location_name", ""),
                        "url": f"https://{cfg['host']}/careers-home/jobs/{j.get('slug') or rid}",
                        "posted": (j.get("posted_date") or "")[:10],
                    }
                )
            if len(jobs) < 100:
                break
    return out


def wp_jobs(cfg):
    """Sites WordPress du groupe BPCE (Natixis, BPCE...) : API REST standard /wp/v2/job.
    Contrat, ville, région et pays viennent des taxonomies (classes tax_contract-stage, tax_city-paris...)."""
    import html

    api = f"{cfg['base_url'].rstrip('/')}{cfg.get('api_path', '/app/wp-json')}/wp/v2/job"
    out, page, pages = [], 1, 1
    while page <= min(pages, int(cfg.get("max_pages", 30))):
        r = _get(api, params={"per_page": 100, "page": page, **(cfg.get("params") or {})})
        pages = int(r.headers.get("X-WP-TotalPages", 1))
        for j in r.json():
            tax = {}
            for c in j.get("class_list", []):
                m = re.match(r"tax_(contract|city|place|country|brands)-(.+)$", c)
                if m:
                    tax.setdefault(m.group(1), m.group(2))
            city = tax.get("city", "").replace("-", " ").title()
            place = tax.get("place", "").title()
            country = tax.get("country", "").title()
            where = ", ".join(x for x in dict.fromkeys([city, place, country]) if x and x != "International")
            contract = tax.get("contract", "").replace("-", " ").title()
            brand = tax.get("brands", "")
            company = next((name for key, name in (cfg.get("brand_companies") or {}).items() if brand.startswith(key)), cfg["company"])
            out.append(
                {
                    "id": f"wp:{cfg['company']}:{j['id']}",
                    "company": company,
                    "entity": brand.replace("-", " ").title(),
                    "title": html.unescape(j.get("title", {}).get("rendered", "")),
                    "location": " · ".join(x for x in [contract, where] if x),
                    "url": j.get("link", ""),
                    "posted": (j.get("date") or "")[:10],
                }
            )
        page += 1
    return out


def brassring(cfg):
    """Portails BrassRing / Kenexa (UBS) : la page d'accueil donne la valeur de session et le jeton RFT,
    puis /Search/Ajax/MatchedJobs renvoie la liste (50 offres max par recherche, on croise plusieurs mots-clés)."""
    import json

    from bs4 import BeautifulSoup

    base = f"https://{cfg['host']}"
    home = f"{base}/TGnewUI/Search/home/Home?partnerid={cfg['partner']}&siteid={cfg['site']}"
    sess = requests.Session()
    sess.headers.update(UA)
    page = sess.get(home, timeout=TIMEOUT * 2)
    page.raise_for_status()
    hidden = {
        (i.get("id") or i.get("name")): (i.get("value") or "")
        for i in BeautifulSoup(page.text, "html.parser").find_all("input", type="hidden")
    }
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": home,
        "Origin": base,
        "RFT": hidden.get("__RequestVerificationToken", ""),
    }
    seen, out = set(), []
    for q in cfg.get("queries", ["intern", "internship"]):
        body = {
            "PartnerId": str(cfg["partner"]),
            "SiteId": str(cfg["site"]),
            "Keyword": q,
            "Location": "",
            "KeywordCustomSolrFields": "FORMTEXT2,FORMTEXT21,AutoReq,Department,JobTitle",
            "LocationCustomSolrFields": "FORMTEXT2,FORMTEXT23,Location",
            "FacetFilterFields": None,
            "TurnOffHttps": False,
            "Latitude": 0,
            "Longitude": 0,
            "PowerSearchOptions": {"PowerSearchOption": []},
            "encryptedsessionvalue": hidden.get("CookieValue", ""),
        }
        r = sess.post(f"{base}/TgNewUI/Search/Ajax/MatchedJobs", headers=headers, data=json.dumps(body), timeout=TIMEOUT * 2)
        r.raise_for_status()
        for job in (r.json().get("Jobs") or {}).get("Job") or []:
            f = {x.get("QuestionName"): x.get("Value") for x in job.get("Questions", [])}
            jid = str(f.get("reqid") or job.get("Link"))
            if jid in seen:
                continue
            seen.add(jid)
            out.append(
                {
                    "id": f"br:{cfg['host']}:{jid}",
                    "company": cfg["company"],
                    "title": f.get("jobtitle", ""),
                    "location": " · ".join(str(f[k]) for k in cfg.get("location_fields", ["location"]) if f.get(k)),
                    "url": (job.get("Link") or "").replace("\\u0026", "&"),
                    "posted": str(f.get("lastupdated") or ""),
                }
            )
    return out


COLLECTORS = {
    "rss": rss,
    "workable": workable,
    "oracle_hcm": oracle_hcm,
    "oleeo_feed": oleeo_feed,
    "html_links": html_links,
    "generic_json": generic_json,
    "generic_html": generic_html,
    "greenhouse": greenhouse,
    "lever": lever,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
    "eightfold": eightfold,
    "jibe": jibe,
    "wp_jobs": wp_jobs,
    "brassring": brassring,
}
