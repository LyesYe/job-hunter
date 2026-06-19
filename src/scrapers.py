import hashlib
import json
import os
import time
import requests
from bs4 import BeautifulSoup
from src.config import RELEVANCE_KEYWORDS, EXCLUSION_KEYWORDS, SEARCH_QUERIES, LINKEDIN_GEO_ID_FRANCE

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_id(title: str, company: str) -> str:
    key = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


def is_relevant(job: dict) -> bool:
    # Only check title + description — never the 'tags' field (that stores the search query
    # we used, not actual content, so it would cause false positives).
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    for kw in EXCLUSION_KEYWORDS:
        if kw.lower() in text:
            return False

    for kw in RELEVANCE_KEYWORDS:
        if kw.lower() in text:
            return True

    return False


def dedupe(jobs: list) -> list:
    seen, result = set(), []
    for job in jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            result.append(job)
    return result


def safe_get(url, extra_headers: dict = None, **kwargs) -> requests.Response | None:
    headers = {**HEADERS, **(extra_headers or {})}
    try:
        resp = requests.get(url, headers=headers, timeout=12, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"    GET {url[:60]}... failed: {e}")
        return None


# ─── Adzuna ───────────────────────────────────────────────────────────────────

def scrape_adzuna() -> list:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        print("[Adzuna] Skipping — ADZUNA_APP_ID / ADZUNA_APP_KEY not set")
        return []

    jobs = []
    queries = [
        "unity developer", "XR developer", "VR developer",
        "computer graphics", "unreal engine", "shader developer",
        "spatial computing", "réalité virtuelle",
    ]

    for query in queries:
        resp = safe_get(
            "https://api.adzuna.com/v1/api/jobs/fr/search/1",
            params={
                "app_id": app_id,
                "app_key": app_key,
                "what": query,
                "results_per_page": 20,
                "content-type": "application/json",
            },
        )
        if not resp:
            continue

        for item in resp.json().get("results", []):
            job = {
                "id": make_id(item.get("title", ""), item.get("company", {}).get("display_name", "")),
                "title": item.get("title", ""),
                "company": item.get("company", {}).get("display_name", ""),
                "location": item.get("location", {}).get("display_name", ""),
                "description": item.get("description", ""),
                "url": item.get("redirect_url", ""),
                "source": "Adzuna",
                "contract": item.get("contract_type", "") or "",
                "tags": query,
            }
            if is_relevant(job):
                jobs.append(job)

        time.sleep(0.8)

    return dedupe(jobs)


# ─── Welcome to the Jungle ────────────────────────────────────────────────────

def scrape_wttj() -> list:
    """
    Welcome to the Jungle — scrape server-rendered Next.js page data (__NEXT_DATA__).
    No auth needed. Falls back gracefully if the page structure changes.
    """
    jobs = []
    queries = ["unity", "XR VR AR", "computer graphics", "unreal engine", "shader", "réalité virtuelle"]

    for query in queries:
        resp = safe_get(
            "https://www.welcometothejungle.com/fr/jobs",
            params={"query": query, "aroundQuery": "France"},
        )
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # Next.js embeds all page data in a <script id="__NEXT_DATA__"> tag
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag:
            continue

        try:
            page_data = json.loads(script_tag.string)
        except Exception:
            continue

        # Navigate the nested structure — may change between WTTJ deploys
        try:
            results = (
                page_data.get("props", {})
                .get("pageProps", {})
                .get("jobs", {})
                .get("data", {})
                .get("jobs", [])
            )
        except Exception:
            results = []

        for item in results:
            org = item.get("organization") or {}
            office = item.get("office") or {}
            contract_obj = item.get("contract_type") or {}
            slug = item.get("slug", "")
            org_slug = org.get("slug", "")

            job = {
                "id": make_id(item.get("name", ""), org.get("name", "")),
                "title": item.get("name", ""),
                "company": org.get("name", ""),
                "location": office.get("city", "France"),
                "description": item.get("description", ""),
                "url": f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{slug}",
                "source": "WTTJ",
                "contract": contract_obj.get("name", "") if contract_obj else "",
                "tags": "",
            }
            if is_relevant(job):
                jobs.append(job)

        time.sleep(1)

    return dedupe(jobs)


# ─── LinkedIn (guest API) ─────────────────────────────────────────────────────

def scrape_linkedin() -> list:
    jobs = []
    queries = [
        "unity developer", "XR developer", "VR developer",
        "computer graphics engineer", "unreal engine developer",
    ]

    for query in queries:
        resp = safe_get(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
            params={
                "keywords": query,
                "location": "France",
                "geoId": LINKEDIN_GEO_ID_FRANCE,
                "start": 0,
                "count": 25,
                "f_TPR": "r86400",  # last 24h
            },
        )
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for card in soup.select("li"):
            title_el = card.select_one(".base-search-card__title, h3")
            company_el = card.select_one(".base-search-card__subtitle, h4")
            location_el = card.select_one(".job-search-card__location, .base-search-card__metadata")
            link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else ""
            link = (link_el.get("href", "") or "").split("?")[0] if link_el else ""

            job = {
                "id": make_id(title, company),
                "title": title,
                "company": company,
                "location": location,
                "description": title,
                "url": link,
                "source": "LinkedIn",
                "contract": "",
                "tags": query,
            }
            if title and is_relevant(job):
                jobs.append(job)

        time.sleep(2)

    return dedupe(jobs)


# ─── France Travail (Pôle Emploi) ─────────────────────────────────────────────

def _get_france_travail_token() -> str | None:
    """Fetch a short-lived OAuth2 token from France Travail."""
    client_id = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID")
    client_secret = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    try:
        resp = requests.post(
            "https://entreprise.francetravail.fr/connexion/oauth2/access_token",
            params={"realm": "/partenaire"},
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        print(f"[France Travail] Auth failed: {e}")
        return None


def scrape_france_travail() -> list:
    """France Travail API — requires free registration at developer.francetravail.fr."""
    token = _get_france_travail_token()
    if not token:
        print("[France Travail] Skipping — FRANCE_TRAVAIL_CLIENT_ID / CLIENT_SECRET not set")
        return []

    jobs = []
    queries = [
        "unity developer", "développeur XR", "développeur VR",
        "computer graphics", "unreal engine", "réalité virtuelle",
    ]

    for query in queries:
        resp = safe_get(
            "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search",
            extra_headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            params={"motsCles": query, "range": "0-19", "sort": "1"},
        )
        if not resp:
            continue

        try:
            data = resp.json()
        except Exception:
            continue

        for item in data.get("resultats", []):
            lieu = item.get("lieuTravail", {})
            contract_map = {
                "CDI": "CDI", "CDD": "CDD", "MIS": "Mission",
                "SAI": "Saisonnier", "LIB": "Freelance",
            }
            contract_code = item.get("typeContrat", "")

            job = {
                "id": make_id(item.get("intitule", ""), item.get("entreprise", {}).get("nom", "")),
                "title": item.get("intitule", ""),
                "company": item.get("entreprise", {}).get("nom", ""),
                "location": lieu.get("libelle", ""),
                "description": item.get("description", ""),
                "url": item.get("origineOffre", {}).get("urlOrigine", ""),
                "source": "France Travail",
                "contract": contract_map.get(contract_code, contract_code),
                "tags": query,
            }
            if is_relevant(job):
                jobs.append(job)

        time.sleep(1)

    return dedupe(jobs)


# ─── AFJV ─────────────────────────────────────────────────────────────────────

def scrape_afjv() -> list:
    """Association Française du Jeu Vidéo — game/XR dev jobs."""
    jobs = []
    terms = ["unity", "XR", "VR", "réalité virtuelle", "3D", "unreal", "shader"]

    for term in terms:
        # AFJV search — try common URL patterns
        resp = (
            safe_get("https://emploi.afjv.com/index.php", params={"CHERCHE": term, "PAGE": 1})
            or safe_get("https://emploi.afjv.com/", params={"CHERCHE": term, "PAGE": 1})
        )
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # AFJV uses a table layout — find rows with job data
        for row in soup.select("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            link_el = cells[0].find("a")
            if not link_el:
                continue

            title = link_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://emploi.afjv.com/" + href

            company = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            location = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            contract = cells[3].get_text(strip=True) if len(cells) > 3 else ""

            job = {
                "id": make_id(title, company),
                "title": title,
                "company": company,
                "location": location,
                "description": title,
                "url": href,
                "source": "AFJV",
                "contract": contract,
                "tags": term,
            }
            if is_relevant(job):
                jobs.append(job)

        time.sleep(1)

    return dedupe(jobs)


# ─── AFXR ─────────────────────────────────────────────────────────────────────

def scrape_afxr() -> list:
    """Association Française XR — all listings are relevant by nature."""
    jobs = []

    resp = safe_get("https://www.afxr.org/page/976227-emplois-et-carrieres")
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try multiple selector patterns (site may use various CMS layouts)
    candidates = (
        soup.select(".job-item, .offer-item, .emploi-item, article.post")
        or soup.select("ul.items li, .list-offers li, .list-jobs li")
        or soup.select(".content a[href]")
    )

    for item in candidates:
        link_el = item if item.name == "a" else item.find("a")
        if not link_el:
            continue

        title = link_el.get_text(strip=True)
        href = link_el.get("href", "")

        if not title or len(title) < 8:
            continue

        # Skip navigation links
        skip_words = ["accueil", "contact", "about", "association", "membres", "actualités"]
        if any(w in title.lower() for w in skip_words):
            continue

        company_el = item.select_one(".company, .societe, .organization, .author")
        company = company_el.get_text(strip=True) if company_el else "Via AFXR"

        job = {
            "id": make_id(title, company),
            "title": title,
            "company": company,
            "location": "France",
            "description": title,
            "url": href,
            "source": "AFXR",
            "contract": "",
            "tags": "XR VR AR spatial computing",
        }
        jobs.append(job)

    return jobs


# ─── CNXR ─────────────────────────────────────────────────────────────────────

def scrape_cnxr() -> list:
    """Collectif National XR — all listings are relevant by nature."""
    jobs = []

    resp = safe_get("https://cnxr.fr/jobs/")
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # WordPress job board (WP Job Manager or similar)
    for item in soup.select(
        ".job_listing, article.type-job_listing, li.job_listing, "
        ".job-listing, .wpjob-item, .job-post"
    ):
        title_el = item.select_one("h1, h2, h3, .position, .job-title, .wpjb-col-title a")
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        link_el = item.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""

        company_el = item.select_one(".company, .societe, .wpjb-col-company")
        company = company_el.get_text(strip=True) if company_el else "Via CNXR"

        location_el = item.select_one(".location, .lieu, .wpjb-col-location, .job-location")
        location = location_el.get_text(strip=True) if location_el else "France"

        contract_el = item.select_one(".job-type, .contract, .wpjb-col-type")
        contract = contract_el.get_text(strip=True) if contract_el else ""

        if not title or len(title) < 5:
            continue

        job = {
            "id": make_id(title, company),
            "title": title,
            "company": company,
            "location": location,
            "description": title,
            "url": href,
            "source": "CNXR",
            "contract": contract,
            "tags": "XR VR AR spatial computing",
        }
        jobs.append(job)

    return jobs


# ─── Main aggregator ──────────────────────────────────────────────────────────

SCRAPERS = [
    ("Adzuna",        scrape_adzuna),
    ("WTTJ",          scrape_wttj),
    ("LinkedIn",      scrape_linkedin),
    ("France Travail",scrape_france_travail),
    ("AFJV",          scrape_afjv),
    ("AFXR",          scrape_afxr),
    ("CNXR",          scrape_cnxr),
]


def get_all_jobs() -> list:
    all_jobs = []

    for name, scraper in SCRAPERS:
        print(f"[{name}] Scraping...")
        try:
            results = scraper()
            print(f"[{name}] {len(results)} relevant jobs found")
            all_jobs.extend(results)
        except Exception as e:
            print(f"[{name}] Fatal error: {e}")

    # Cross-source deduplication (same job on multiple sites)
    return dedupe(all_jobs)
