import requests
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}

# Search queries tailored to Rakib's profile
SEARCH_QUERIES = [
    "Machine Learning Engineer intern",
    "AI Engineer intern",
    "ML Engineer entry level",
    "NLP Engineer intern",
    "Computer Vision Engineer intern",
    "Deep Learning Engineer intern",
    "AI Research intern",
    "Data Scientist intern",
    "Generative AI Engineer",
    "LLM Engineer entry level",
    "AI Engineer entry level",
    "Junior ML Engineer",
    "Applied ML Engineer intern",
    "Python Developer AI intern",
]

# Philadelphia metro area — within ~40 min drive from zip 19149
# Covers Philly + surrounding counties + South Jersey
PHILADELPHIA_LOCATIONS = [
    "Philadelphia Pennsylvania",
    "King of Prussia PA",
    "Conshohocken PA",
    "Horsham PA",
    "Blue Bell PA",
    "Wayne PA",
    "Malvern PA",
    "Exton PA",
    "Lansdale PA",
    "Willow Grove PA",
    "Cherry Hill NJ",
    "Mount Laurel NJ",
    "Marlton NJ",
    "Camden NJ",
    "Voorhees NJ",
]

# Remote/global locations
REMOTE_LOCATIONS = [
    "United States",
    "Remote",
]


def get_locations_for_preference(work_location: str) -> dict:
    """
    Returns search locations based on work preference.

    remote  → search globally, no geo filter
    hybrid  → global for remote + Philadelphia metro for hybrid
    onsite  → Philadelphia metro only
    any     → global + Philadelphia metro
    """
    if work_location == "remote":
        return {
            "remote": REMOTE_LOCATIONS,
            "local": []
        }
    elif work_location == "hybrid":
        return {
            "remote": REMOTE_LOCATIONS,
            "local": PHILADELPHIA_LOCATIONS
        }
    elif work_location == "onsite":
        return {
            "remote": [],
            "local": PHILADELPHIA_LOCATIONS
        }
    else:  # any
        return {
            "remote": REMOTE_LOCATIONS,
            "local": PHILADELPHIA_LOCATIONS
        }


def search_jobs(query: str, location: str, is_remote: bool = False) -> list:
    """Search JSearch API for jobs matching a query and location"""

    params = {
        "query": f"{query} in {location}",
        "page": "1",
        "num_pages": "1",
        "date_posted": "month",
        "employment_types": "FULLTIME,INTERN,PARTTIME",
        "job_requirements": "no_experience,under_3_years_experience"
    }

    if is_remote:
        params["remote_jobs_only"] = "true"

    try:
        response = requests.get(JSEARCH_URL, headers=HEADERS, params=params, timeout=15)
        data = response.json()

        if data.get("status") == "OK":
            jobs = data.get("data", [])
            print(f"  Found {len(jobs)} jobs for '{query}' in {location}")
            return jobs
        else:
            print(f"  API error for '{query}': {data.get('message', 'Unknown')}")
            return []

    except Exception as e:
        print(f"  Request failed: {e}")
        return []


def normalize_job(raw_job: dict, is_local: bool = False) -> dict:
    """Convert JSearch raw job to our clean format"""
    city = raw_job.get("job_city") or ""
    state = raw_job.get("job_state") or ""
    location = f"{city}, {state}".strip(", ")

    return {
        "id": raw_job.get("job_id", ""),
        "title": raw_job.get("job_title", ""),
        "company": raw_job.get("employer_name", ""),
        "location": location,
        "country": raw_job.get("job_country", ""),
        "is_remote": raw_job.get("job_is_remote", False),
        "is_local": is_local,
        "description": raw_job.get("job_description", ""),
        "apply_url": raw_job.get("job_apply_link", ""),
        "posted_date": raw_job.get("job_posted_at_datetime_utc", ""),
        "employment_type": raw_job.get("job_employment_type", ""),
        "apply_platform": detect_platform(raw_job.get("job_apply_link", "")),
        "is_easy_apply": raw_job.get("job_apply_is_direct", False),
        "employer_logo": raw_job.get("employer_logo", ""),
        "salary_min": raw_job.get("job_min_salary"),
        "salary_max": raw_job.get("job_max_salary"),
        "highlights": {
            "qualifications": raw_job.get("job_highlights", {}).get("Qualifications", []),
            "responsibilities": raw_job.get("job_highlights", {}).get("Responsibilities", []),
            "benefits": raw_job.get("job_highlights", {}).get("Benefits", [])
        }
    }


def detect_platform(apply_url: str) -> str:
    """Detect which platform the job is on for auto-apply routing"""
    if not apply_url:
        return "unknown"
    url = apply_url.lower()
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
    elif "taleo" in url:
        return "taleo"
    elif "icims" in url:
        return "icims"
    else:
        return "direct"


def deduplicate_jobs(jobs: list) -> list:
    """Remove duplicate jobs by ID and title+company combo"""
    seen_ids = set()
    seen_combos = set()
    unique = []

    for job in jobs:
        job_id = job.get("id", "")
        combo = f"{job.get('title','').lower()}_{job.get('company','').lower()}"

        if job_id and job_id in seen_ids:
            continue
        if combo in seen_combos:
            continue

        seen_ids.add(job_id)
        seen_combos.add(combo)
        unique.append(job)

    return unique


def find_all_jobs(max_jobs: int = 100, work_location: str = "remote") -> list:
    """
    Main function — searches based on work location preference.

    Remote only  → searches globally, returns remote jobs
    Hybrid       → global remote + Philadelphia metro hybrid/onsite
    Onsite       → Philadelphia metro only
    Any          → everything
    """
    print(f"\nStarting job discovery...")
    print(f"Work preference: {work_location.upper()}")
    print(f"Max jobs: {max_jobs}")
    print(f"Search queries: {len(SEARCH_QUERIES)}\n")

    locations = get_locations_for_preference(work_location)
    remote_locs = locations["remote"]
    local_locs = locations["local"]

    if local_locs:
        print(f"Local search area: Philadelphia metro ({len(local_locs)} locations)")
    if remote_locs:
        print(f"Remote search: Global ({len(remote_locs)} location types)\n")

    all_raw_jobs = []

    # search remote/global locations
    if remote_locs:
        print("--- Remote/Global Search ---")
        for query in SEARCH_QUERIES:
            for location in remote_locs:
                jobs = search_jobs(query, location, is_remote=True)
                all_raw_jobs.extend([(j, False) for j in jobs])
                if len(all_raw_jobs) >= max_jobs * 3:
                    break
            if len(all_raw_jobs) >= max_jobs * 3:
                break

    # search local Philadelphia metro locations
    if local_locs:
        print("\n--- Philadelphia Metro Search ---")
        for query in SEARCH_QUERIES:
            # only search a subset of local locations to save API calls
            for location in local_locs[:5]:
                jobs = search_jobs(query, location, is_remote=False)
                all_raw_jobs.extend([(j, True) for j in jobs])
                if len(all_raw_jobs) >= max_jobs * 3:
                    break
            if len(all_raw_jobs) >= max_jobs * 3:
                break

    print(f"\nRaw jobs found: {len(all_raw_jobs)}")

    # normalize all jobs
    normalized = []
    for raw_job, is_local in all_raw_jobs:
        try:
            normalized.append(normalize_job(raw_job, is_local=is_local))
        except Exception as e:
            continue

    # deduplicate
    unique_jobs = deduplicate_jobs(normalized)
    print(f"After deduplication: {len(unique_jobs)} unique jobs")

    # limit to max
    final_jobs = unique_jobs[:max_jobs]
    print(f"Final job list: {len(final_jobs)} jobs ready for scoring\n")

    return final_jobs


def get_platform_breakdown(jobs: list) -> dict:
    """Show how many jobs per platform"""
    breakdown = {}
    for job in jobs:
        platform = job.get("apply_platform", "unknown")
        breakdown[platform] = breakdown.get(platform, 0) + 1
    return breakdown


if __name__ == "__main__":
    # test with remote only (default)
    print("=== TEST: Remote Only ===")
    jobs = find_all_jobs(max_jobs=10, work_location="remote")

    print("\n--- PLATFORM BREAKDOWN ---")
    breakdown = get_platform_breakdown(jobs)
    for platform, count in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
        auto = platform in ["greenhouse", "lever", "linkedin", "indeed"]
        print(f"  {platform}: {count} [{'AUTO' if auto else 'manual'}]")

    print(f"\nTotal: {len(jobs)} jobs")

    print("\n--- SAMPLE JOBS ---")
    for job in jobs[:5]:
        local_tag = "📍 LOCAL" if job.get("is_local") else "🌐 Remote"
        print(f"  {local_tag} | {job['title']} at {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  Platform: {job['apply_platform']}")
        print()
