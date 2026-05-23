import hashlib
import os
import re
import time

import requests
from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")

ML_QUERIES = [
    "machine learning engineer",
    "AI engineer",
    "NLP engineer",
    "computer vision engineer",
    "deep learning engineer",
    "generative AI engineer",
    "LLM engineer",
    "data scientist",
    "applied ML engineer",
    "AI research intern",
    "ML intern",
    "AI software engineer",
]


def make_job_id(title: str, company: str, source: str) -> str:
    raw = f"{source}_{title}_{company}".lower().replace(" ", "_")
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def detect_platform(url: str) -> str:
    if not url:
        return "unknown"
    url = url.lower()
    if "greenhouse.io" in url or "boards.greenhouse" in url:
        return "greenhouse"
    elif "lever.co" in url:
        return "lever"
    elif "linkedin.com" in url:
        return "linkedin"
    elif "indeed.com" in url:
        return "indeed"
    elif "workday.com" in url or "myworkday" in url:
        return "workday"
    else:
        return "direct"


# ─────────────────────────────────────────────
# SOURCE 0: JSearch via RapidAPI (5 calls/run to stay under 200/month)
# ─────────────────────────────────────────────
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}

# Full query list — runs all on paid plan
JSEARCH_QUERIES = [
    "ML Engineer intern remote",
    "AI Engineer intern remote",
    "machine learning internship remote",
    "generative AI engineer entry level",
    "NLP engineer intern remote",
    "computer vision engineer intern",
    "deep learning engineer intern",
    "LLM engineer entry level",
    "data scientist intern remote",
    "applied machine learning intern",
    "AI research intern remote",
    "junior ML engineer remote",
    "generative AI intern",
    "AI software engineer intern",
    "machine learning intern site:boards.greenhouse.io",
    "AI engineer intern site:jobs.lever.co",
    "ML intern site:greenhouse.io",
]

JSEARCH_LOCATIONS = [
    "United States",
    "Remote",
    "Philadelphia Pennsylvania",
]


def fetch_jsearch_jobs() -> list:
    """Fetch from JSearch — full queries on paid plan"""
    if not RAPIDAPI_KEY:
        print("  [JSearch] No API key, skipping")
        return []

    print(f"  [JSearch] Fetching jobs ({len(JSEARCH_QUERIES)} queries)...")
    jobs = []

    for query in JSEARCH_QUERIES:
        try:
            for location in JSEARCH_LOCATIONS[:2]:  # 2 locations per query
                params = {
                    "query": f"{query} in {location}",
                    "page": "1",
                    "num_pages": "1",
                    "date_posted": "month",
                    "employment_types": "FULLTIME,INTERN",
                    "job_requirements": "no_experience,under_3_years_experience"
                }
                response = requests.get(
                    JSEARCH_URL, headers=JSEARCH_HEADERS, params=params, timeout=30
                )
                data = response.json()

                if data.get("status") == "OK":
                    for raw in data.get("data", []):
                        title = raw.get("job_title", "")
                        company = raw.get("employer_name", "")
                        city = raw.get("job_city") or ""
                        state = raw.get("job_state") or ""
                        loc = f"{city}, {state}".strip(", ")
                        apply_url = raw.get("job_apply_link", "")

                        jobs.append({
                            "id": make_job_id(title, company, "jsearch"),
                            "title": title,
                            "company": company,
                            "location": loc,
                            "country": raw.get("job_country", "US"),
                            "is_remote": raw.get("job_is_remote", False),
                            "is_local": False,
                            "description": raw.get("job_description", "")[:3000],
                            "apply_url": apply_url,
                            "posted_date": raw.get("job_posted_at_datetime_utc", ""),
                            "employment_type": raw.get("job_employment_type", ""),
                            "apply_platform": detect_platform(apply_url),
                            "employer_logo": raw.get("employer_logo", ""),
                            "salary_min": raw.get("job_min_salary"),
                            "salary_max": raw.get("job_max_salary"),
                            "source": "jsearch"
                        })
                else:
                    print(f"  [JSearch] API error: {data.get('message', 'unknown')}")

        except Exception as e:
            print(f"  [JSearch] Error for '{query}': {e}")

        time.sleep(1)

    print(f"  [JSearch] Found {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 1: LinkedIn (Greenhouse/Lever apply links)
# ─────────────────────────────────────────────
def fetch_linkedin_jobs(work_location: str = "remote") -> list:
    """
    Fetch ML/AI jobs from LinkedIn public job search.
    LinkedIn listings often embed Greenhouse/Lever apply URLs → enables auto-apply.
    """
    print("  [LinkedIn] Fetching ML/AI jobs...")
    jobs = []

    queries = [
        "machine learning engineer intern",
        "AI engineer intern",
        "ML engineer entry level",
        "NLP engineer intern",
        "generative AI engineer",
        "LLM engineer intern",
        "data scientist intern",
        "computer vision engineer intern",
    ]

    location_param = "United States"
    remote_filter = ""
    if work_location in ["remote", "hybrid"]:
        remote_filter = "&f_WT=2"  # LinkedIn remote filter

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for query in queries[:5]:  # limit to save time
        try:
            url = (
                f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                f"?keywords={requests.utils.quote(query)}"
                f"&location={requests.utils.quote(location_param)}"
                f"{remote_filter}&start=0&count=10"
            )
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                continue

            from html.parser import HTMLParser

            class LinkedInParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.jobs = []
                    self.current_job = {}
                    self.in_title = False
                    self.in_company = False
                    self.in_location = False

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    classes = attrs_dict.get("class", "")

                    if "base-card__full-link" in classes or "job-search-card__link-absolute" in classes:
                        href = attrs_dict.get("href", "")
                        if href and "linkedin.com/jobs/view" in href:
                            self.current_job["apply_url"] = href.split("?")[0]

                    if "base-search-card__title" in classes or "job-search-card__title" in classes:
                        self.in_title = True

                    if "base-search-card__subtitle" in classes or "job-search-card__subtitle" in classes:
                        self.in_company = True

                    if "job-search-card__location" in classes:
                        self.in_location = True

                def handle_data(self, data):
                    data = data.strip()
                    if not data:
                        return
                    if self.in_title:
                        self.current_job["title"] = data
                        self.in_title = False
                    elif self.in_company:
                        self.current_job["company"] = data
                        self.in_company = False
                    elif self.in_location:
                        self.current_job["location"] = data
                        self.in_location = False

                    if ("title" in self.current_job and
                        "company" in self.current_job and
                        "apply_url" in self.current_job and
                        self.current_job not in self.jobs):
                        self.jobs.append(dict(self.current_job))

            parser = LinkedInParser()
            parser.feed(response.text)

            for raw in parser.jobs:
                title = raw.get("title", "")
                company = raw.get("company", "")
                location = raw.get("location", "")
                apply_url = raw.get("apply_url", "")

                if not title or not company:
                    continue

                is_remote = any(w in location.lower() for w in ["remote", "anywhere"])

                # try to extract real apply URL from LinkedIn job page
                real_apply_url = apply_url
                real_platform = "linkedin"
                try:
                    job_resp = requests.get(
                        apply_url, headers=headers, timeout=10, allow_redirects=True
                    )
                    job_html = job_resp.text
                    gh_match = re.search(
                        r'https://boards\.greenhouse\.io/[^\s"\'<>]+', job_html
                    )
                    lv_match = re.search(
                        r'https://jobs\.lever\.co/[^\s"\'<>]+', job_html
                    )
                    if gh_match:
                        real_apply_url = gh_match.group(0)
                        real_platform = "greenhouse"
                    elif lv_match:
                        real_apply_url = lv_match.group(0)
                        real_platform = "lever"
                except Exception:
                    pass

                jobs.append({
                    "id": make_job_id(title, company, "linkedin"),
                    "title": title,
                    "company": company,
                    "location": location,
                    "country": "US",
                    "is_remote": is_remote,
                    "is_local": False,
                    "description": f"{title} at {company} — {location}",
                    "apply_url": real_apply_url,
                    "posted_date": "",
                    "employment_type": "",
                    "apply_platform": real_platform,
                    "employer_logo": "",
                    "salary_min": None,
                    "salary_max": None,
                    "source": "linkedin"
                })

        except Exception as e:
            print(f"  [LinkedIn] Error for '{query}': {e}")

    print(f"  [LinkedIn] Found {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 2: Remotive (free, no key, remote only)
# ─────────────────────────────────────────────
def fetch_remotive_jobs() -> list:
    print("  [Remotive] Fetching remote tech jobs...")
    jobs = []
    categories = ["software-dev", "data", "qa"]

    for category in categories:
        try:
            url = f"https://remotive.com/api/remote-jobs?category={category}&limit=50"
            response = requests.get(url, timeout=15)
            data = response.json()

            for job in data.get("jobs", []):
                title = job.get("title", "")
                title_lower = title.lower()
                if not any(kw in title_lower for kw in [
                    "machine learning", "ml ", "ai ", "artificial intelligence",
                    "data science", "data scientist", "nlp", "computer vision",
                    "deep learning", "llm", "generative", "neural"
                ]):
                    continue

                company = job.get("company_name", "")
                apply_url = job.get("url", "")
                jobs.append({
                    "id": make_job_id(title, company, "remotive"),
                    "title": title,
                    "company": company,
                    "location": "Remote",
                    "country": "Worldwide",
                    "is_remote": True,
                    "is_local": False,
                    "description": job.get("description", "")[:3000],
                    "apply_url": apply_url,
                    "posted_date": job.get("publication_date", ""),
                    "employment_type": job.get("job_type", ""),
                    "apply_platform": detect_platform(apply_url),
                    "employer_logo": job.get("company_logo", ""),
                    "salary_min": None,
                    "salary_max": None,
                    "source": "remotive"
                })
        except Exception as e:
            print(f"  [Remotive] Error: {e}")

    print(f"  [Remotive] Found {len(jobs)} ML/AI jobs")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 3: Arbeitnow (free, no key, remote+hybrid)
# ─────────────────────────────────────────────
def fetch_arbeitnow_jobs() -> list:
    print("  [Arbeitnow] Fetching remote+hybrid tech jobs...")
    jobs = []

    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        response = requests.get(url, timeout=15)
        data = response.json()

        for job in data.get("data", []):
            title = job.get("title", "")
            title_lower = title.lower()

            if not any(kw in title_lower for kw in [
                "machine learning", "ml ", " ml", "ai ", " ai", "artificial intelligence",
                "data science", "data scientist", "nlp", "computer vision",
                "deep learning", "llm", "generative", "neural", "python developer",
                "software engineer", "backend engineer"
            ]):
                continue

            company = job.get("company_name", "")
            is_remote = job.get("remote", False)
            location = job.get("location", "")
            apply_url = job.get("url", "")

            jobs.append({
                "id": make_job_id(title, company, "arbeitnow"),
                "title": title,
                "company": company,
                "location": location if location else ("Remote" if is_remote else ""),
                "country": "US/EU",
                "is_remote": is_remote,
                "is_local": False,
                "description": job.get("description", "")[:3000],
                "apply_url": apply_url,
                "posted_date": str(job.get("created_at", "")),
                "employment_type": "",
                "apply_platform": detect_platform(apply_url),
                "employer_logo": "",
                "salary_min": None,
                "salary_max": None,
                "source": "arbeitnow"
            })

    except Exception as e:
        print(f"  [Arbeitnow] Error: {e}")

    print(f"  [Arbeitnow] Found {len(jobs)} ML/AI/tech jobs")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 4: Adzuna (250 free/month)
# ─────────────────────────────────────────────
def fetch_adzuna_jobs(work_location: str = "remote") -> list:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("  [Adzuna] No API key, skipping")
        return []

    print("  [Adzuna] Fetching jobs...")
    jobs = []

    for query in ML_QUERIES[:6]:
        try:
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": 10,
                "what": f"{query} remote" if work_location in ["remote", "hybrid"] else query,
                "content-type": "application/json",
            }
            if work_location == "onsite":
                params["where"] = "Philadelphia"
                params["distance"] = "40"

            url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            for job in data.get("results", []):
                title = job.get("title", "")
                company = job.get("company", {}).get("display_name", "")
                location_data = job.get("location", {})
                location = ", ".join(location_data.get("area", [])[-2:])
                apply_url = job.get("redirect_url", "")

                jobs.append({
                    "id": make_job_id(title, company, "adzuna"),
                    "title": title,
                    "company": company,
                    "location": location,
                    "country": "US",
                    "is_remote": "remote" in (job.get("description") or "").lower()[:500],
                    "is_local": work_location == "onsite",
                    "description": job.get("description", "")[:3000],
                    "apply_url": apply_url,
                    "posted_date": job.get("created", ""),
                    "employment_type": job.get("contract_time", ""),
                    "apply_platform": detect_platform(apply_url),
                    "employer_logo": "",
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "source": "adzuna"
                })

        except Exception as e:
            print(f"  [Adzuna] Error for '{query}': {e}")

    print(f"  [Adzuna] Found {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 5: HiringCafe (free, no key)
# ─────────────────────────────────────────────
def fetch_hiringcafe_jobs() -> list:
    print("  [HiringCafe] Fetching ML/AI jobs...")
    jobs = []

    try:
        url = "https://hiring.cafe/api/jobs"
        params = {"q": "machine learning engineer", "remote": "true"}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            for job in data.get("jobs", [])[:30]:
                title = job.get("title", "")
                company = job.get("company", "")
                apply_url = job.get("apply_url", "")
                jobs.append({
                    "id": make_job_id(title, company, "hiringcafe"),
                    "title": title,
                    "company": company,
                    "location": job.get("location", "Remote"),
                    "country": "US",
                    "is_remote": True,
                    "is_local": False,
                    "description": job.get("description", "")[:3000],
                    "apply_url": apply_url,
                    "posted_date": "",
                    "employment_type": "",
                    "apply_platform": detect_platform(apply_url),
                    "employer_logo": "",
                    "salary_min": None,
                    "salary_max": None,
                    "source": "hiringcafe"
                })
    except Exception as e:
        print(f"  [HiringCafe] Error or unavailable: {e}")

    print(f"  [HiringCafe] Found {len(jobs)} jobs")
    return jobs


def deduplicate_jobs(jobs: list) -> list:
    seen_ids = set()
    seen_combos = set()
    unique = []

    for job in jobs:
        job_id = job.get("id", "")
        combo = f"{job.get('title','').lower()[:40]}_{job.get('company','').lower()[:30]}"

        if job_id in seen_ids:
            continue
        if combo in seen_combos:
            continue

        seen_ids.add(job_id)
        seen_combos.add(combo)
        unique.append(job)

    return unique


def filter_by_location(jobs: list, work_location: str) -> list:
    if work_location == "remote":
        return [j for j in jobs if j.get("is_remote")]
    elif work_location == "hybrid":
        return [j for j in jobs if j.get("is_remote") or
                "hybrid" in (j.get("location") or "").lower() or
                "hybrid" in (j.get("title") or "").lower() or
                not j.get("location") or
                j.get("location", "").lower() in ["", "worldwide", "remote"]]
    elif work_location == "onsite":
        return [j for j in jobs if not j.get("is_remote")]
    else:
        return jobs


def find_all_jobs(max_jobs: int = 100, work_location: str = "remote") -> list:
    print(f"\nStarting job discovery...")
    print(f"Work preference: {work_location.upper()}")
    print(f"Max jobs: {max_jobs}")
    print(f"Sources: JSearch, LinkedIn, Remotive, Arbeitnow, Adzuna, HiringCafe\n")

    all_jobs = []
    all_jobs.extend(fetch_jsearch_jobs())
    all_jobs.extend(fetch_linkedin_jobs(work_location))
    all_jobs.extend(fetch_remotive_jobs())
    all_jobs.extend(fetch_arbeitnow_jobs())
    all_jobs.extend(fetch_adzuna_jobs(work_location))
    all_jobs.extend(fetch_hiringcafe_jobs())

    print(f"\nRaw jobs from all sources: {len(all_jobs)}")
    unique_jobs = deduplicate_jobs(all_jobs)
    print(f"After deduplication: {len(unique_jobs)} unique jobs")
    filtered = filter_by_location(unique_jobs, work_location)
    print(f"After location filter ({work_location}): {len(filtered)} jobs")
    final = filtered[:max_jobs]
    print(f"Final job list: {len(final)} jobs ready for scoring\n")

    return final
