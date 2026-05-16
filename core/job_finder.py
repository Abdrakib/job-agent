import requests
import hashlib
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Adzuna API (250 free/month, needs key)
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")

# Search queries tailored to Rakib's profile
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
    """Generate a stable unique ID from job fields"""
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
# SOURCE 1: Remotive (free, no key, remote only)
# ─────────────────────────────────────────────
def fetch_remotive_jobs() -> list:
    """Fetch remote tech jobs from Remotive API"""
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
                # filter for ML/AI roles
                title_lower = title.lower()
                if not any(kw in title_lower for kw in [
                    "machine learning", "ml ", "ai ", "artificial intelligence",
                    "data science", "data scientist", "nlp", "computer vision",
                    "deep learning", "llm", "generative", "neural"
                ]):
                    continue

                company = job.get("company_name", "")
                jobs.append({
                    "id": make_job_id(title, company, "remotive"),
                    "title": title,
                    "company": company,
                    "location": "Remote",
                    "country": "Worldwide",
                    "is_remote": True,
                    "is_local": False,
                    "description": job.get("description", "")[:3000],
                    "apply_url": job.get("url", ""),
                    "posted_date": job.get("publication_date", ""),
                    "employment_type": job.get("job_type", ""),
                    "apply_platform": detect_platform(job.get("url", "")),
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
# SOURCE 2: Arbeitnow (free, no key, remote+hybrid)
# ─────────────────────────────────────────────
def fetch_arbeitnow_jobs() -> list:
    """Fetch remote/hybrid tech jobs from Arbeitnow"""
    print("  [Arbeitnow] Fetching remote+hybrid tech jobs...")
    jobs = []

    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        response = requests.get(url, timeout=15)
        data = response.json()

        for job in data.get("data", []):
            title = job.get("title", "")
            title_lower = title.lower()

            # filter for ML/AI/data roles
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

            jobs.append({
                "id": make_job_id(title, company, "arbeitnow"),
                "title": title,
                "company": company,
                "location": location if location else ("Remote" if is_remote else ""),
                "country": "US/EU",
                "is_remote": is_remote,
                "is_local": False,
                "description": job.get("description", "")[:3000],
                "apply_url": job.get("url", ""),
                "posted_date": str(job.get("created_at", "")),
                "employment_type": "",
                "apply_platform": detect_platform(job.get("url", "")),
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
# SOURCE 3: Adzuna (250 free/month, remote+onsite)
# ─────────────────────────────────────────────
def fetch_adzuna_jobs(work_location: str = "remote") -> list:
    """Fetch jobs from Adzuna API"""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("  [Adzuna] No API key, skipping")
        return []

    print("  [Adzuna] Fetching jobs...")
    jobs = []
    queries_to_run = ML_QUERIES[:6]  # limit to save monthly quota

    for query in queries_to_run:
        try:
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": 10,
                "what": query,
                "content-type": "application/json",
            }

            if work_location in ["remote", "hybrid"]:
                params["what"] = f"{query} remote"
            else:
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

                jobs.append({
                    "id": make_job_id(title, company, "adzuna"),
                    "title": title,
                    "company": company,
                    "location": location,
                    "country": "US",
                    "is_remote": "remote" in (job.get("description") or "").lower()[:500],
                    "is_local": work_location == "onsite",
                    "description": job.get("description", "")[:3000],
                    "apply_url": job.get("redirect_url", ""),
                    "posted_date": job.get("created", ""),
                    "employment_type": job.get("contract_time", ""),
                    "apply_platform": detect_platform(job.get("redirect_url", "")),
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
# SOURCE 4: HiringCafe (free, no key)
# ─────────────────────────────────────────────
def fetch_hiringcafe_jobs() -> list:
    """Fetch from HiringCafe free API"""
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
                jobs.append({
                    "id": make_job_id(title, company, "hiringcafe"),
                    "title": title,
                    "company": company,
                    "location": job.get("location", "Remote"),
                    "country": "US",
                    "is_remote": True,
                    "is_local": False,
                    "description": job.get("description", "")[:3000],
                    "apply_url": job.get("apply_url", ""),
                    "posted_date": "",
                    "employment_type": "",
                    "apply_platform": detect_platform(job.get("apply_url", "")),
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
    """Remove duplicate jobs by ID and title+company combo"""
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
    """Filter jobs based on work location preference"""
    if work_location == "remote":
        return [j for j in jobs if j.get("is_remote")]
    elif work_location == "hybrid":
        return [j for j in jobs if j.get("is_remote") or
                "hybrid" in (j.get("location") or "").lower() or
                "hybrid" in (j.get("title") or "").lower()]
    elif work_location == "onsite":
        return [j for j in jobs if not j.get("is_remote")]
    else:  # any
        return jobs


def find_all_jobs(max_jobs: int = 100, work_location: str = "remote") -> list:
    """
    Main function — fetches jobs from all free sources.
    Filters by work location preference.
    """
    print(f"\nStarting job discovery...")
    print(f"Work preference: {work_location.upper()}")
    print(f"Max jobs: {max_jobs}")
    print(f"Sources: Remotive, Arbeitnow, Adzuna, HiringCafe\n")

    all_jobs = []

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


if __name__ == "__main__":
    jobs = find_all_jobs(max_jobs=20, work_location="remote")
    print(f"\n--- SAMPLE JOBS ---")
    for job in jobs[:5]:
        print(f"  [{job['source']}] {job['title']} at {job['company']}")
        print(f"  Location: {job['location']} | Remote: {job['is_remote']}")
        print(f"  Platform: {job['apply_platform']}")
        print()
