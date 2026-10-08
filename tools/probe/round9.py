"""Tour 9 : recrutement.bpce.fr (groupe BPCE) et page francaise d'Oddo BHF."""
import collections
import json
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}


def sh(s, n=300):
    return re.sub(r"\s+", " ", str(s))[:n]


print("##### BPCE wp/v2/job")
try:
    B = "https://recrutement.bpce.fr/app/wp-json"
    for u in [f"{B}/wp/v2/job?per_page=100&page=1", "https://recrutement.bpce.fr/wp-json/wp/v2/job?per_page=100&page=1"]:
        rr = requests.get(u, headers=UA, timeout=30)
        print(rr.status_code, u[-50:], "total", rr.headers.get("X-WP-Total"), "pages", rr.headers.get("X-WP-TotalPages"), len(rr.text), sh(rr.text, 100))
        if rr.ok and rr.text.startswith("["):
            jobs = rr.json()
            j = jobs[0]
            print("cles:", list(j.keys()))
            print("class_list:", j.get("class_list"))
            for k in ("acf", "meta"):
                if k in j:
                    print(k, sh(json.dumps(j[k], ensure_ascii=False), 600))
            print("taxonomies:", sorted({t.split('-')[0] for x in jobs for t in x.get('class_list', []) if t.startswith('tax_')}))
            print("contrats:", collections.Counter(t for x in jobs for t in x.get("class_list", []) if t.startswith("tax_contract")).most_common(12))
            print("lieux:", collections.Counter(t for x in jobs for t in x.get("class_list", []) if re.match(r"tax_(city|ville|location|place|geo|region|country|pays|lieu)", t)).most_common(10))
            print("exemples:", [(x["title"]["rendered"], x["link"]) for x in jobs[:4]])
            break
    # filtre contrat cote serveur, comme l'URL donnee par l'utilisateur
    for u in [f"{B}/wp/v2/job?per_page=100&tax_contract=stage", f"{B}/wp/v2/job?per_page=5&contract=stage"]:
        rr = requests.get(u, headers=UA, timeout=30)
        print(rr.status_code, u[len(B):], "total", rr.headers.get("X-WP-Total"), sh(rr.text, 150))
    tx = requests.get(f"{B}/wp/v2/taxonomies", headers=UA, timeout=20).json()
    print("taxonomies REST:", {k: v.get("rest_base") for k, v in tx.items()})
    for k, v in tx.items():
        if re.search(r"contract|lieu|location|city|region|place|geo", k, re.I):
            terms = requests.get(f"{B}/wp/v2/{v['rest_base']}?per_page=100", headers=UA, timeout=20)
            print(" ", k, terms.status_code, sh([(t.get('id'), t.get('slug')) for t in terms.json()][:30] if terms.ok else terms.text, 700))
except Exception as e:
    print("ERR bpce", type(e).__name__, str(e)[:200])

print("\n##### BPCE routes (liste complete)")
try:
    r = requests.get("https://recrutement.bpce.fr/app/wp-json/bpce/v1/routes/?lang=fr", headers=UA, timeout=30)
    print(r.status_code, len(r.text))
    if r.ok:
        rt = r.json()
        print("routes:", len(rt), "job:", len([x for x in rt if x.get("component") == "Template Job"]))
except Exception as e:
    print("ERR routes", type(e).__name__, str(e)[:100])

print("\n##### Oddo page francaise")
try:
    r = requests.get("https://www.oddo-bhf.com/fr/decouvrez-nos-offres-demplois/", headers=UA, timeout=30)
    t = r.text
    print(r.status_code, len(t))
    print("iframes/scripts ATS:", sorted(set(re.findall(r"""(?:src|href|data-src)=["']([^"']*(?:altays|talent-?soft|recrut|taleo|workday|smartrecruiters|successfactors|welcometothejungle|jobteaser|teamtailor|lever|greenhouse|oraclecloud|cvwebsite|eolia)[^"']*)["']""", t, re.I)))[:10])
    print("liens offres:", [l for l in dict.fromkeys(re.findall(r'href="([^"]+)"', t)) if re.search(r"offre|job|emploi|recrut", l, re.I)][:15])
except Exception as e:
    print("ERR oddo fr", type(e).__name__, str(e)[:100])
for u in ["https://recrutement.altays-progiciels.com/oddo/fr/recherche.html", "https://recrutement.altays-progiciels.com/oddo/fr/offres.html",
          "https://recrutement.altays-progiciels.com/oddo/fr/", "https://recrutement.altays-progiciels.com/oddo/fr/offres/nombre.json?page=1"]:
    try:
        r = requests.get(u, headers=UA, timeout=20)
        t = r.text
        links = list(dict.fromkeys(re.findall(r'href="([^"]*/offres/[^"]+\.html)"', t)))
        print(r.status_code, u[-48:], len(t), sh(t[:90], 90), "| liens offres:", len(links), [l[-70:] for l in links[:3]])
    except Exception as e:
        print("ERR", u[-40:], type(e).__name__)
print("FIN ROUND9")
