import os
import time
import requests
from datetime import datetime

SOURCE_COLORS = {
    "Adzuna":        0xFF6B00,
    "WTTJ":          0x00C4A7,
    "LinkedIn":      0x0A66C2,
    "France Travail":0x003189,
    "AFJV":          0x8B00FF,
    "AFXR":          0xFF1744,
    "CNXR":          0x00BCD4,
}

SOURCE_EMOJIS = {
    "Adzuna":        "🔎",
    "WTTJ":          "🌿",
    "LinkedIn":      "💼",
    "France Travail":"🇫🇷",
    "AFJV":          "🎮",
    "AFXR":          "🥽",
    "CNXR":          "🔬",
}

CONTRACT_EMOJIS = {
    "cdi": "♾️",
    "cdd": "📅",
    "freelance": "🧑‍💻",
    "stage": "🎓",
    "alternance": "🔄",
    "phd": "🔬",
    "doctorat": "🔬",
    "thèse": "🔬",
}


def _post(webhook_url: str, payload: dict):
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[Discord] Failed to send: {e}")


def _contract_emoji(contract: str) -> str:
    c = contract.lower()
    for kw, emoji in CONTRACT_EMOJIS.items():
        if kw in c:
            return f"{emoji} {contract}"
    return contract


def send_discord(jobs: list):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[Discord] No DISCORD_WEBHOOK_URL — skipping")
        return

    today = datetime.now().strftime("%d/%m/%Y")

    if not jobs:
        _post(webhook_url, {
            "content": (
                f"📋 **Job Hunt — {today}**\n"
                "_Aucune nouvelle offre aujourd'hui. À demain !_"
            )
        })
        return

    # ── Header message ──
    source_counts = {}
    for j in jobs:
        source_counts[j["source"]] = source_counts.get(j["source"], 0) + 1

    source_summary = "  ".join(
        f"{SOURCE_EMOJIS.get(s, '📌')} {s}: **{n}**"
        for s, n in sorted(source_counts.items(), key=lambda x: -x[1])
    )

    _post(webhook_url, {
        "content": (
            f"## 🎯 Job Hunt — {today}\n"
            f"**{len(jobs)} nouvelles offres** pour ton profil XR / 3D / Graphics\n"
            f"{source_summary}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    })
    time.sleep(0.5)

    # ── Job embeds (max 10 per message) ──
    batch = []

    for job in jobs:
        fields = []

        if job.get("company"):
            fields.append({"name": "🏢 Entreprise", "value": job["company"], "inline": True})
        if job.get("location"):
            fields.append({"name": "📍 Lieu", "value": job["location"], "inline": True})
        if job.get("contract"):
            fields.append({
                "name": "📄 Contrat",
                "value": _contract_emoji(job["contract"]),
                "inline": True,
            })

        embed = {
            "title": f"{SOURCE_EMOJIS.get(job['source'], '📌')} {job['title']}",
            "url": job.get("url") or None,
            "color": SOURCE_COLORS.get(job["source"], 0x808080),
            "fields": fields,
            "footer": {"text": f"Source: {job['source']}"},
        }
        # Remove None url (Discord rejects it)
        if not embed["url"]:
            del embed["url"]

        batch.append(embed)

        if len(batch) == 10:
            _post(webhook_url, {"embeds": batch})
            batch = []
            time.sleep(1)

    if batch:
        _post(webhook_url, {"embeds": batch})
