"""Tour 10 : en-tetes exacts de la requete MatchedJobs d'UBS faite par le navigateur."""
import json
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
    cap = {}

    def on_req(rq):
        if rq.method == "POST" and "MatchedJobs" in rq.url:
            cap["h"] = rq.headers
            cap["b"] = rq.post_data
            cap["url"] = rq.url

    pg.on("request", on_req)
    pg.goto(HOME, wait_until="domcontentloaded", timeout=40000)
    pg.wait_for_timeout(6000)
    hidden = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('input[type=hidden]')].map(e => [e.id || e.name, e.value]))")
    box = pg.locator("input[type=text]:visible, input[type=search]:visible").first
    box.fill("intern", timeout=8000)
    box.press("Enter")
    pg.wait_for_timeout(9000)
    if "h" in cap:
        h = dict(cap["h"])
        for k in list(h):
            if k.lower() == "cookie":
                h[k] = re.sub(r"=([^;]{6})[^;]*", r"=\1...", h[k])
        print("URL:", cap["url"])
        print("HEADERS:", json.dumps(h, indent=0)[:1800])
        body = json.loads(cap["b"])
        enc = body.get("encryptedsessionvalue", "")
        print("enc len", len(enc), "== hidden:", [k for k, v in hidden.items() if v == enc])
        rft = cap["h"].get("rft") or cap["h"].get("RFT")
        print("header RFT == hidden:", [k for k, v in hidden.items() if rft and v == rft])
        for k in cap["h"]:
            if re.search(r"token|rft|verif|csrf|xsrf", k, re.I):
                print("  header", k, "== hidden:", [n for n, v in hidden.items() if v == cap["h"][k]])
    else:
        print("aucune requete MatchedJobs capturee")
    cookies = {c["name"]: (c["value"][:12] + "...") for c in ctx.cookies()}
    print("cookies:", cookies)
    b.close()
print("FIN ROUND10")
