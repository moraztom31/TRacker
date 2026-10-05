import html
import os

import requests


def send(text):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return  # Telegram facultatif : alertes visibles sur le site
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15,
    )
    if not r.ok:
        print("[telegram] erreur", r.status_code, r.text[:200])


def new_jobs(jobs, max_detailed=10):
    for j in jobs[:max_detailed]:
        send(
            f"🆕 <b>{html.escape(j['title'])}</b>\n"
            f"{html.escape(j['company'])} · {html.escape(j.get('location') or 'lieu non précisé')}\n"
            f"<a href=\"{html.escape(j['url'])}\">Postuler</a>"
        )
    rest = jobs[max_detailed:]
    if rest:
        lines = "\n".join(
            f"• {html.escape(j['company'])} : <a href=\"{html.escape(j['url'])}\">{html.escape(j['title'])}</a>"
            for j in rest[:30]
        )
        send(f"<b>+{len(rest)} autres offres</b>\n{lines}")
