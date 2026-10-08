"""Tour 4 : motif des liens BNP, Oddo (altays), detail Natixis, Pictet et UBS dans un navigateur."""
import json
import re

import requests
from curl_cffi import requests as cr

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


def section(t):
    print(f"\n##### {t}", flush=True)


section("BNP : liens d'offres page 1 et 2")
try:
    for page in (1, 2):
        u = "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/stage" + (f"?page={page}" if page > 1 else "")
        t = cr.get(u, impersonate="chrome124", timeout=30).text
        links = list(dict.fromkeys(re.findall(r'<a[^>]+href="([^"]+)"', t)))
        cand = [l for l in links if re.search(r"/(?:emploi-carriere/)?(?:offre|offres|job|jobs|emploi)[^\"]*/[^/\"]{20,}$", l) or re.search(r"[0-9]{5,}", l)]
        print(f"page {page}: {len(links)} liens, candidats offre: {len(cand)}")
        for l in cand[:12]:
            print("   ", l[:150])
        if page == 1 and cand:
            i = t.index(cand[0])
            print("HTML carte:", sh(t[max(0, i - 400):i + 900], 1300))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:150])

section("Oddo altays variantes")
for u in ["https://recrutement.altays-progiciels.com/oddo/en/offres/liste.json?page=1", "https://recrutement.altays-progiciels.com/oddo/en/offres.json?page=1",
          "https://recrutement.altays-progiciels.com/oddo/en/offres/offres.json?page=1", "https://recrutement.altays-progiciels.com/oddo/en/",
          "https://recrutement.altays-progiciels.com/oddo/fr/offres/liste.json?page=1", "https://recrutement.altays-progiciels.com/oddo/en/offres/liste?page=1"]:
    try:
        r = requests.get(u, headers=UA, timeout=20)
        print(r.status_code, u[-60:], len(r.text), sh(r.text, 160))
    except Exception as e:
        print("ERR", u[-50:], type(e).__name__)

section("Natixis detail d'une offre")
try:
    routes = requests.get("https://recrutement.natixis.com/app/wp-json/bpce/v1/routes/?lang=fr", headers=UA, timeout=20).json()
    jobs = [x for x in routes if x.get("component") == "Template Job"]
    print("routes job:", len(jobs))
    st = [x for x in jobs if re.search(r"stage|intern|v-i-e|alternan", x["path"])]
    print("dont stage/intern/vie/alternance:", len(st))
    x = st[0]
    d = requests.get("https://recrutement.natixis.com/app/wp-json/bpce/v1/pages/", params={"lang": "fr", "_uid": x["_uid"]}, headers=UA, timeout=20).json()
    print("uid", x["_uid"], "path", x["path"], "keys", list(d.keys())[:30])
    print(sh(json.dumps(d, ensure_ascii=False), 1800))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:150])

section("Navigateur : Oddo / Pictet / UBS")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])

        def page(url, wait=8000):
            ctx = b.new_context(user_agent=UA["User-Agent"], locale="en-GB")
            pg = ctx.new_page()
            reqs = []
            pg.on("request", lambda rq: reqs.append((rq.method, rq.url, (rq.post_data or "")[:700])))
            try:
                pg.goto(url, wait_until="domcontentloaded", timeout=30000)
                pg.wait_for_timeout(wait)
            except Exception as e:
                print("  goto ERR", type(e).__name__)
            return ctx, pg, reqs

        ctx, pg, reqs = page("https://www.oddo-bhf.com/discover-our-jobs/")
        print("Oddo requetes altays:")
        for m, u, d in reqs:
            if "altays" in u:
                print("  ", m, u[:170])
        for fr in pg.frames:
            if "altays" in fr.url:
                print("  frame", fr.url[:150])
                links = fr.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                print("  frame liens:", [l for l in links if 'offre' in l][:8], len(links))
                print("  texte:", sh(fr.inner_text("body"), 300))
        ctx.close()

        ctx, pg, reqs = page("https://career5.successfactors.eu/career?company=banquepict", wait=12000)
        links = pg.eval_on_selector_all("a[href]", "els => els.map(e => [e.href, e.innerText.trim()])")
        jl = [l for l in links if re.search(r"req_id|job", l[0], re.I)]
        print("Pictet liens offres DOM:", len(jl), [(a[:100], t[:60]) for a, t in jl[:5]])
        print("Pictet requetes:", [(m, u[:120]) for m, u, d in reqs if re.search(r"job|search|career_ns|odata", u, re.I)][:8])
        ctx.close()

        ctx, pg, reqs = page("https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid=5012", wait=6000)
        try:
            btn = pg.get_by_role("button", name=re.compile(r"search", re.I)).first
            btn.click(timeout=8000)
            pg.wait_for_timeout(7000)
        except Exception as e:
            print("UBS click ERR", type(e).__name__, str(e)[:100])
        for m, u, d in reqs:
            if re.search(r"Search/Ajax|MatchedJobs|ProcessSort|ShowMore", u, re.I):
                print("UBS", m, u[:150], "body:", sh(d, 500))
        links = pg.eval_on_selector_all("a[href]", "els => els.map(e => [e.href, e.innerText.trim()])")
        jl = [l for l in links if re.search(r"JobDetail|jobid|reqid", l[0], re.I)]
        print("UBS liens offres DOM:", len(jl), [(a[:120], t[:60]) for a, t in jl[:5]])
        ctx.close()
        b.close()
except Exception as e:
    print("ERR playwright", type(e).__name__, str(e)[:150])

section("CIC lever / Lazard")
try:
    j = requests.get("https://api.lever.co/v0/postings/cic?mode=json", headers=UA, timeout=20).json()
    print("lever cic:", len(j), [(x.get("text"), (x.get("categories") or {}).get("location")) for x in j[:3]])
except Exception as e:
    print("ERR lever", type(e).__name__)
for u in ["https://lazard-careers.tal.net/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/candidate/jobboard/vacancy/2/adv",
          "https://lazard-careers.tal.net/vx/mobile-0/appcentre-1/brand-4/candidate/jobboard/vacancy/2/feed"]:
    try:
        r = requests.get(u, headers=UA, timeout=20)
        print(r.status_code, u[-80:], len(r.text), "opp liens:", len(set(re.findall(r"/opp/(\d+)", r.text))))
    except Exception as e:
        print("ERR", u[-60:], type(e).__name__)
print("FIN ROUND4")
