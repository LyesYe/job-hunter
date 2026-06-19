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
    "cdi":        "♾️",
    "cdd":        "📅",
    "freelance":  "🧑‍💻",
    "stage":      "🎓",
    "alternance": "🔄",
    "phd":        "🔬",
    "doctorat":   "🔬",
    "thèse":      "🔬",
}

# Location keywords that indicate Paris / Île-de-France
IDF_KEYWORDS = [
    "paris", "île-de-france", "ile-de-france", "idf",
    "boulogne", "vincennes", "saint-ouen", "saint-denis",
    "nanterre", "issy", "levallois", "neuilly", "puteaux",
    "versailles", "massy", "saclay", "orsay", "palaiseau",
    "créteil", "bobigny", "pontoise", "évry", "cergy",
    "la défense", "suresnes", "montrouge", "châtillon",
    "92", "93", "94", "95", "77", "78", "91",  # département codes
]


def _post(webhook_url: str, payload: dict):
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        time.sleep(0.3)  # gentle rate limiting
    except Exception as e:
        print(f"[Discord] Failed to send: {e}")


def _contract_label(contract: str) -> str:
    if not contract:
        return ""
    c = contract.lower()
    for kw, emoji in CONTRACT_EMOJIS.items():
        if kw in c:
            return f"{emoji} {contract}"
    return contract


def _is_idf(job: dict) -> bool:
    location = job.get("location", "").lower()
    return any(kw in location for kw in IDF_KEYWORDS)


def _send_section_header(webhook_url: str, title: str, count: int):
    """Send a section divider message."""
    _post(webhook_url, {"content": f"\n{title} — **{count} offre{'s' if count > 1 else ''}**"})


def _send_embeds(webhook_url: str, jobs: list):
    """Send jobs as Discord embeds, max 10 per message."""
    batch = []
    for job in jobs:
        fields = []
        if job.get("company"):
            fields.append({"name": "🏢 Entreprise", "value": job["company"], "inline": True})
        if job.get("location"):
            fields.append({"name": "📍 Lieu", "value": job["location"], "inline": True})
        if job.get("contract"):
            label = _contract_label(job["contract"])
            if label:
                fields.append({"name": "📄 Contrat", "value": label, "inline": True})

        embed = {
            "title": f"{SOURCE_EMOJIS.get(job['source'], '📌')} {job['title']}",
            "color": SOURCE_COLORS.get(job["source"], 0x808080),
            "fields": fields,
            "footer": {"text": f"Source: {job['source']}"},
        }
        url = job.get("url")
        if url:
            embed["url"] = url

        batch.append(embed)

        if len(batch) == 10:
            _post(webhook_url, {"embeds": batch})
            batch = []

    if batch:
        _post(webhook_url, {"embeds": batch})


def send_discord(jobs: list):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[Discord] No DISCORD_WEBHOOK_URL — skipping")
        return

    now = datetime.now()
    date_str = now.strftime("%A %d %B %Y").capitalize()  # e.g. "Jeudi 19 Juin 2026"
    divider = "══════════════════════════════"

    # ── Daily separator ──────────────────────────────────────────────────────
    _post(webhook_url, {
        "content": (
            f"\n{divider}\n"
            f"## 🗓️ {date_str}\n"
            f"{divider}"
        )
    })

    if not jobs:
        _post(webhook_url, {
            "content": "_Aucune nouvelle offre aujourd'hui. À demain !_"
        })
        return

    # ── Summary ──────────────────────────────────────────────────────────────
    source_counts = {}
    for j in jobs:
        source_counts[j["source"]] = source_counts.get(j["source"], 0) + 1

    source_summary = "  ·  ".join(
        f"{SOURCE_EMOJIS.get(s, '📌')} {s} **{n}**"
        for s, n in sorted(source_counts.items(), key=lambda x: -x[1])
    )
    idf_jobs = [j for j in jobs if _is_idf(j)]
    other_jobs = [j for j in jobs if not _is_idf(j)]

    _post(webhook_url, {
        "content": (
            f"**{len(jobs)} nouvelles offres** XR · 3D · Graphics\n"
            f"{source_summary}\n"
            f"📍 Paris/IDF : **{len(idf_jobs)}**   🌍 Reste France + Remote : **{len(other_jobs)}**"
        )
    })

    # ── Section 1 : Paris / Île-de-France ────────────────────────────────────
    if idf_jobs:
        _send_section_header(webhook_url, "📍 __Paris · Île-de-France__", len(idf_jobs))
        _send_embeds(webhook_url, idf_jobs)

    # ── Section 2 : Reste France + Remote ────────────────────────────────────
    if other_jobs:
        _send_section_header(webhook_url, "🌍 __Reste France · Remote · PhD__", len(other_jobs))
        _send_embeds(webhook_url, other_jobs)
