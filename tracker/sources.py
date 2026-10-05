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


def _get(url, **kw):
    r = requests.get(url, headers=UA, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def greenhouse(cfg):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{cfg['slug']}/jobs").json()
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
        soup = BeautifulSoup(_get(url).text, "html.parser")
        found = 0
        for a in soup.find_all("a", href=True):
            if cfg["link_contains"] not in a["href"]:
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


COLLECTORS = {
    "oracle_hcm": oracle_hcm,
    "oleeo_feed": oleeo_feed,
    "html_links": html_links,
    "generic_json": generic_json,
    "generic_html": generic_html,
    "greenhouse": greenhouse,
    "lever": lever,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
}
