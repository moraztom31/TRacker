"""Tour 6 : recherche UBS (BrassRing) capturee dans un navigateur."""
import re

from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
HOME = "https://jobs.ubs.com/TGnewUI/Search/home/Home?partnerid=25008&siteid=5012"


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(user_agent=UA, locale="en-GB", viewport={"width": 1400, "height": 1000})
    pg = ctx.new_page()
    posts = []

    def on_resp(r):
        if r.request.method == "POST" and "jobs.ubs.com" in r.url and "Search" in r.url:
            try:
                body = r.text()
            except Exception:
                body = ""
            posts.append((r.url, (r.request.post_data or "")[:1800], r.status, len(body), body[:600]))

    pg.on("response", on_resp)
    pg.goto(HOME, wait_until="domcontentloaded", timeout=40000)
    pg.wait_for_timeout(7000)
    print("inputs:", pg.eval_on_selector_all("input", "els => els.map(e => [e.type, e.id, e.name, (e.placeholder||'').slice(0,30), (e.getAttribute('aria-label')||'').slice(0,30)])")[:15])
    print("boutons:", pg.eval_on_selector_all("button, [role=button], a.primaryButton", "els => els.map(e => [(e.innerText||'').trim().slice(0,40), e.id, (e.className||'').toString().slice(0,30)])")[:25])
    try:
        box = pg.locator("input[type=text]:visible, input[type=search]:visible").first
        box.fill("intern", timeout=8000)
        box.press("Enter")
        pg.wait_for_timeout(9000)
    except Exception as e:
        print("saisie ERR", type(e).__name__, str(e)[:120])
    links = pg.eval_on_selector_all("a[href]", "els => els.map(e => [e.href, (e.innerText||'').trim()])")
    jl = [l for l in links if re.search(r"jobid=", l[0], re.I)]
    print("liens offres apres recherche:", len(jl), [(h[-60:], t[:50]) for h, t in jl[:6]])
    print("texte resultats:", sh(pg.inner_text("body"), 500))
    print("POST captures:", len(posts))
    for u, d, st, n, body in posts:
        print("POST", u[:140], st, n, "\n   body:", sh(d, 900), "\n   resp:", sh(body, 400))
    b.close()
print("FIN ROUND6")
