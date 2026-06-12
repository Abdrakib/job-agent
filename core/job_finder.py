"""
job_finder.py — Job discovery using JSearch API + Greenhouse/Lever/Ashby direct APIs
Strategy:
  1. Greenhouse direct API → guaranteed auto-apply URLs (33 verified companies)
  2. Lever direct API → guaranteed auto-apply URLs (verified companies only)
  3. Ashby direct API → guaranteed auto-apply URLs (33 verified companies)
  4. JSearch → high volume from Indeed, LinkedIn, Glassdoor, ZipRecruiter + more
  5. Deduplicate + filter by location preference

ALL company slugs in this file are verified working.
Do NOT add slugs without testing first.
"""
import requests
import hashlib
import os
import time
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}

MAX_JOBS_PER_COMPANY = 5


# ─────────────────────────────────────────────
# ML/AI KEYWORDS
# ─────────────────────────────────────────────

ML_KEYWORDS = [
    "machine learning", "ml engineer", "ai engineer", "artificial intelligence",
    "deep learning", "nlp", "natural language", "computer vision",
    "data scientist", "data science", "llm", "generative ai",
    "neural network", "pytorch", "tensorflow", "ai researcher",
    "applied scientist", "research engineer", "ai intern", "ml intern",
    "software engineer", "backend engineer", "full stack", "python developer",
    "mlops", "model deployment", "huggingface", "langchain", "rag",
    "transformer", "fine-tuning", "inference", "model serving",
]

EXCLUDE_KEYWORDS = [
    "senior director", "vp of", "vice president", "chief ",
    "principal engineer", "staff engineer", "distinguished engineer",
    "10+ years", "15+ years", "12+ years", "8+ years",
    "phd required", "physics", "chemistry", "biology", "genomics",
    "hardware", "fpga", "embedded", "firmware", "sales", "marketing",
    "recruiter", "hr ", "accounting", "legal", "financial analyst"
]

# ─────────────────────────────────────────────
# JSEARCH QUERIES
# JSearch aggregates Indeed, LinkedIn, Glassdoor,
# ZipRecruiter, Dice, SimplyHired and more in one call.
# 28 queries x 2 pages x 10 results = up to 560 raw jobs
# Top 8 queries get an extra page 3 for more volume
# ─────────────────────────────────────────────
JSEARCH_QUERIES = [
    # Full-time entry level — primary target as May 2026 grad
    "machine learning engineer entry level remote",
    "AI engineer entry level remote",
    "junior machine learning engineer remote",
    "junior AI engineer remote",
    "ML engineer new grad remote",
    "AI engineer new grad 2026",
    "junior data scientist machine learning remote",
    "LLM engineer entry level remote",
    "generative AI engineer entry level",
    "NLP engineer entry level remote",
    "computer vision engineer entry level remote",
    "deep learning engineer entry level",
    "AI software engineer junior remote",
    "python machine learning engineer junior remote",
    # Broader roles Rakib qualifies for
    "MLOps engineer entry level remote",
    "AI platform engineer junior remote",
    "software engineer machine learning remote entry level",
    "research engineer AI entry level remote",
    "applied scientist entry level remote",
    "AI product engineer entry level remote",
    "PyTorch engineer entry level remote",
    "HuggingFace developer remote entry level",
    # Internships — secondary
    "machine learning intern remote 2026",
    "AI engineer intern remote 2026",
    "data science intern remote 2026",
    "LLM research intern remote",
    "generative AI intern 2026",
    "applied machine learning intern remote",
]

# These top queries get an extra page for more volume
JSEARCH_HIGH_VOLUME_QUERIES = {
    "machine learning engineer entry level remote",
    "AI engineer entry level remote",
    "junior machine learning engineer remote",
    "ML engineer new grad remote",
    "LLM engineer entry level remote",
    "generative AI engineer entry level",
    "MLOps engineer entry level remote",
    "software engineer machine learning remote entry level",
}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def make_job_id(title: str, company: str, source: str) -> str:
    raw = f"{source}_{title}_{company}".lower().replace(" ", "_")
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def detect_platform(url: str) -> str:
    if not url:
        return "direct"
    url_lower = url.lower()
    if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
        return "greenhouse"
    elif "lever.co" in url_lower:
        return "lever"
    elif "ashbyhq.com" in url_lower:
        return "ashby"
    elif "linkedin.com" in url_lower:
        return "linkedin"
    elif "indeed.com" in url_lower:
        return "indeed"
    elif "workday.com" in url_lower or "myworkday" in url_lower:
        return "workday"
    elif "ziprecruiter.com" in url_lower:
        return "ziprecruiter"
    elif "glassdoor.com" in url_lower:
        return "glassdoor"
    return "direct"


def is_relevant(title: str, description: str = "") -> bool:
    """Check if job is relevant ML/AI role."""
    title_lower = title.lower()
    desc_lower = (description or "").lower()[:500]

    for kw in EXCLUDE_KEYWORDS:
        if kw in title_lower:
            return False

    combined = title_lower + " " + desc_lower
    return any(kw in combined for kw in ML_KEYWORDS)


# ─────────────────────────────────────────────
# SOURCE 1: GREENHOUSE
# VERIFIED working slugs only — tested 2026-06-08
# boards-api.greenhouse.io/v1/boards/{slug}/jobs
# ─────────────────────────────────────────────

GREENHOUSE_COMPANIES = [
    # Core tech (verified working)
    "anthropic", "stripe", "airbnb", "lyft", "robinhood",
    "brex", "gusto", "figma", "vercel", "datadog",
    "databricks", "mongodb", "elastic", "twilio", "newrelic",
    "intercom", "asana", "airtable", "smartsheet", "klaviyo",
    "mixpanel", "amplitude", "instacart", "rippling", "doordash",
    "cloudflare", "pagerduty", "hightouch", "fivetran", "cockroachdb",
    "yotpo", "honeycomb", "fastly",
    # Verified from slug audit
    "duolingo", "waymo", "assemblyai", "coursera", "scaleai",
]


def fetch_greenhouse_jobs() -> list:
    """Fetch ML/AI jobs from Greenhouse public API. No auth needed."""
    print("  [Greenhouse] Scanning company boards...")
    jobs = []
    errors = 0

    for company in GREENHOUSE_COMPANIES:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
            resp = requests.get(url, timeout=8)

            if resp.status_code != 200:
                errors += 1
                continue

            company_jobs = []
            for job in resp.json().get("jobs", []):
                if len(company_jobs) >= MAX_JOBS_PER_COMPANY:
                    break

                title = job.get("title", "")
                # Get description from content if available
                content = job.get("content", "") or ""
                description = content[:500] if content else title

                if not is_relevant(title, description):
                    continue

                location_data = job.get("location", {})
                location = location_data.get("name", "") if isinstance(location_data, dict) else str(location_data)
                job_id = job.get("id", "")
                apply_url = f"https://boards.greenhouse.io/{company}/jobs/{job_id}"

                company_jobs.append({
                    "id": make_job_id(title, company, "greenhouse"),
                    "title": title,
                    "company": company.replace("-", " ").title(),
                    "location": location,
                    "country": "US",
                    "is_remote": any(w in location.lower() for w in ["remote", "anywhere", "distributed", "worldwide"]),
                    "is_local": "philadelphia" in location.lower() or ", pa" in location.lower(),
                    "description": description,
                    "apply_url": apply_url,
                    "posted_date": job.get("updated_at", ""),
                    "employment_type": "",
                    "apply_platform": "greenhouse",
                    "employer_logo": "",
                    "salary_min": None,
                    "salary_max": None,
                    "source": "greenhouse_direct"
                })
            jobs.extend(company_jobs)

        except Exception:
            errors += 1
            continue

    print(f"  [Greenhouse] Found {len(jobs)} ML/AI jobs ({errors} companies unreachable)")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 2: LEVER
# VERIFIED working slugs only — tested 2026-06-08
# api.lever.co/v0/postings/{slug}?mode=json
# ─────────────────────────────────────────────

LEVER_COMPANIES = [
    # Verified working from Lever audit
    "mistral", "openai", "cohere", "anthropic",
    "scale-ai", "stability-ai", "aleph-alpha",
    "stripe", "plaid", "brex", "mercury", "ramp",
    "notion", "linear", "vercel", "netlify", "render", "railway",
    "cloudflare", "fastly",
    "datadog", "grafana", "elastic",
    "mongodb", "redis", "neo4j",
    "huggingface", "together-ai", "replicate",
    "weights-biases", "neptune-ai",
    "labelbox", "humanloop",
    "grammarly", "writer",
    "duolingo", "coursera",
    "sentry", "newrelic",
    "segment", "rudderstack",
    "figma", "asana", "monday",
    "shopify", "klaviyo",
    "instacart",
    "waymo", "aurora",
    "anduril", "palantir",
    "recursion", "insitro",
    "soundhound", "deepgram", "assemblyai",
    "runway-ml", "synthesia",
    "rippling", "gusto", "deel",
    "lattice", "culture-amp",
    "retool", "replit", "gitpod",
    "dbt-labs", "airbyte", "fivetran",
    "pinecone", "weaviate", "chroma",
    "modal", "langchain", "llamaindex",
    "arize-ai", "fiddler-ai",
    "snorkel-ai", "predibase", "h2o",
]


def fetch_lever_jobs() -> list:
    """Fetch ML/AI jobs from Lever public API. No auth needed."""
    print("  [Lever] Scanning company boards...")
    jobs = []
    errors = 0

    for company in LEVER_COMPANIES:
        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            resp = requests.get(url, timeout=8)

            if resp.status_code != 200:
                errors += 1
                continue

            company_jobs = []
            for job in resp.json():
                if len(company_jobs) >= MAX_JOBS_PER_COMPANY:
                    break

                title = job.get("text", "")
                description = job.get("descriptionPlain", "")
                if not is_relevant(title, description):
                    continue

                categories = job.get("categories", {})
                location = categories.get("location", "")
                commitment = categories.get("commitment", "")
                apply_url = job.get("hostedUrl", "")

                company_jobs.append({
                    "id": make_job_id(title, company, "lever"),
                    "title": title,
                    "company": company.replace("-", " ").title(),
                    "location": location,
                    "country": "US",
                    "is_remote": any(w in location.lower() for w in ["remote", "anywhere", "distributed", "worldwide"]),
                    "is_local": "philadelphia" in location.lower() or ", pa" in location.lower(),
                    "description": description[:1000],
                    "apply_url": apply_url,
                    "posted_date": str(job.get("createdAt", "")),
                    "employment_type": commitment,
                    "apply_platform": "lever",
                    "employer_logo": "",
                    "salary_min": None,
                    "salary_max": None,
                    "source": "lever_direct"
                })
            jobs.extend(company_jobs)

        except Exception:
            errors += 1
            continue

    print(f"  [Lever] Found {len(jobs)} ML/AI jobs ({errors} companies unreachable)")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 3: ASHBY
# VERIFIED working slugs only — tested 2026-06-08
# api.ashbyhq.com/posting-api/job-board/{slug}
# ─────────────────────────────────────────────

ASHBY_COMPANIES = [
    # Verified working with job counts (tested 2026-06-08)
    "openai",        # 718 jobs
    "elevenlabs",    # 151 jobs
    "notion",        # 145 jobs
    "cohere",        # 128 jobs
    "langchain",     # 105 jobs
    "cursor",        # 93 jobs
    "synthesia",     # 75 jobs
    "perplexity",    # 69 jobs
    "baseten",       # 66 jobs
    "supabase",      # 46 jobs
    "runway-ml",     # 39 jobs
    "twelve-labs",   # 33 jobs
    "modal",         # 31 jobs
    "fireworks-ai",  # 27 jobs
    "roboflow",      # 26 jobs
    "linear",        # 24 jobs
    "render",        # 23 jobs
    "astronomer",    # 22 jobs
    "posthog",       # 16 jobs
    "character",     # 16 jobs
    "bubble",        # 14 jobs
    "anyscale",      # 10 jobs
    "railway",       # 9 jobs
    "glide",         # 9 jobs
    "neon",          # 7 jobs
    "pinecone",      # 6 jobs
    "lancedb",       # 6 jobs
    "plane",         # 6 jobs
    "weaviate",      # 5 jobs
    "pika",          # 5 jobs
    "prefect",       # 5 jobs
    "runway",        # 4 jobs
    "hightouch",     # 1 job
]


def fetch_ashby_jobs() -> list:
    """Fetch ML/AI jobs from Ashby public API. No auth needed.
    Used by OpenAI, Notion, Cursor, Perplexity, Cohere and many more AI companies.
    """
    print("  [Ashby] Scanning company boards...")
    jobs = []
    errors = 0

    for company in ASHBY_COMPANIES:
        try:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
            resp = requests.get(url, timeout=8)

            if resp.status_code != 200:
                errors += 1
                continue

            company_jobs = []
            for job in resp.json().get("jobs", []):
                if len(company_jobs) >= MAX_JOBS_PER_COMPANY:
                    break

                title = job.get("title", "")
                description = job.get("descriptionPlain", "") or job.get("descriptionHtml", "")
                if not is_relevant(title, description):
                    continue

                location = job.get("locationName", "") or job.get("location", "") or ""
                if isinstance(location, dict):
                    location = location.get("name", "")

                apply_url = job.get("jobUrl", "") or job.get("applyUrl", "") or f"https://jobs.ashbyhq.com/{company}"
                is_remote = job.get("isRemote", False) or "remote" in location.lower()

                company_jobs.append({
                    "id": make_job_id(title, company, "ashby"),
                    "title": title,
                    "company": company.replace("-", " ").title(),
                    "location": location,
                    "country": "US",
                    "is_remote": is_remote,
                    "is_local": "philadelphia" in location.lower() or ", pa" in location.lower(),
                    "description": str(description)[:1000],
                    "apply_url": apply_url,
                    "posted_date": job.get("publishedAt", ""),
                    "employment_type": job.get("employmentType", ""),
                    "apply_platform": "ashby",
                    "employer_logo": "",
                    "salary_min": job.get("compensation", {}).get("minValue") if job.get("compensation") else None,
                    "salary_max": job.get("compensation", {}).get("maxValue") if job.get("compensation") else None,
                    "source": "ashby_direct"
                })
            jobs.extend(company_jobs)

        except Exception:
            errors += 1
            continue

    print(f"  [Ashby] Found {len(jobs)} ML/AI jobs ({errors} companies unreachable)")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 4: JSEARCH API
# Aggregates: Indeed, LinkedIn, Glassdoor,
# ZipRecruiter, Dice, SimplyHired, and more
# 28 queries + extra pages for top queries = max ~700 raw results
# ─────────────────────────────────────────────

def fetch_jsearch_jobs(work_location: str = "remote") -> list:
    """Fetch from JSearch which pulls from Indeed, LinkedIn, Glassdoor and more."""
    if not RAPIDAPI_KEY:
        print("  [JSearch] No RAPIDAPI_KEY set, skipping")
        return []

    print(f"  [JSearch] Running {len(JSEARCH_QUERIES)} queries...")
    jobs = []
    seen_ids = set()

    for query in JSEARCH_QUERIES:
        # Determine how many pages to fetch
        # Top queries get 3 pages, others get 2
        num_pages = 3 if query in JSEARCH_HIGH_VOLUME_QUERIES else 2

        try:
            params = {
                "query": query,
                "page": "1",
                "num_pages": str(num_pages),
                "date_posted": "month",
                "employment_types": "FULLTIME,INTERN,CONTRACTOR",
                "job_requirements": "no_experience,under_3_years_experience",
            }
            # Only filter remote strictly when location is remote
            if work_location == "remote":
                params["remote_jobs_only"] = "true"

            resp = requests.get(
                JSEARCH_URL,
                headers=JSEARCH_HEADERS,
                params=params,
                timeout=30
            )
            data = resp.json()

            if data.get("status") == "OK":
                for raw in data.get("data", []):
                    title = raw.get("job_title", "")
                    description = raw.get("job_description", "")

                    if not is_relevant(title, description):
                        continue

                    company = raw.get("employer_name", "")
                    job_id = make_job_id(title, company, "jsearch")

                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    city = raw.get("job_city") or ""
                    state = raw.get("job_state") or ""
                    location = f"{city}, {state}".strip(", ")
                    apply_url = raw.get("job_apply_link", "")

                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "country": raw.get("job_country", "US"),
                        "is_remote": raw.get("job_is_remote", False),
                        "is_local": "philadelphia" in location.lower() or ", pa" in location.lower(),
                        "description": description[:2000],
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
                print(f"  [JSearch] Error for '{query}': {data.get('message', 'unknown')}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  [JSearch] Error for '{query}': {e}")

    print(f"  [JSearch] Found {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────
# DEDUP + FILTER + MAIN
# ─────────────────────────────────────────────

def deduplicate_jobs(jobs: list) -> list:
    seen_ids = set()
    seen_combos = set()
    unique = []

    for job in jobs:
        job_id = job.get("id", "")
        combo = f"{job.get('title','').lower()[:40]}_{job.get('company','').lower()[:30]}"

        if job_id in seen_ids or combo in seen_combos:
            continue

        seen_ids.add(job_id)
        seen_combos.add(combo)
        unique.append(job)

    return unique


def filter_by_location(jobs: list, work_location: str) -> list:
    auto_apply = ["greenhouse", "lever", "ashby"]
    if work_location == "remote":
        return [j for j in jobs if j.get("is_remote") or j.get("apply_platform") in auto_apply]
    elif work_location == "hybrid":
        return [j for j in jobs if
                j.get("is_remote") or j.get("is_local") or
                "hybrid" in (j.get("location") or "").lower() or
                j.get("apply_platform") in auto_apply]
    elif work_location == "onsite":
        return [j for j in jobs if j.get("is_local") or not j.get("is_remote")]
    return jobs


def cap_per_company(jobs: list, max_per_company: int = 5) -> list:
    company_counts = {}
    result = []
    for job in jobs:
        company = job.get("company", "").lower()
        count = company_counts.get(company, 0)
        if count < max_per_company:
            company_counts[company] = count + 1
            result.append(job)
    return result


def find_all_jobs(max_jobs: int = 100, work_location: str = "remote") -> list:
    """
    Main discovery function.
    Priority: Greenhouse → Lever → Ashby → JSearch
    Greenhouse + Lever + Ashby = direct auto-apply
    JSearch = volume from Indeed, LinkedIn, Glassdoor, ZipRecruiter etc.
    """
    print(f"\n{'='*50}")
    print(f"JOB DISCOVERY — {work_location.upper()} | max {max_jobs}")
    print(f"Sources: Greenhouse, Lever, Ashby, JSearch (Indeed/LinkedIn/Glassdoor)")
    print(f"{'='*50}\n")

    all_jobs = []

    gh_jobs = fetch_greenhouse_jobs()
    all_jobs.extend(gh_jobs)

    lv_jobs = fetch_lever_jobs()
    all_jobs.extend(lv_jobs)

    ab_jobs = fetch_ashby_jobs()
    all_jobs.extend(ab_jobs)

    js_jobs = fetch_jsearch_jobs(work_location)
    all_jobs.extend(js_jobs)

    print(f"\nRaw total: {len(all_jobs)} jobs")
    print(f"  Greenhouse: {len(gh_jobs)} | Lever: {len(lv_jobs)} | Ashby: {len(ab_jobs)} | JSearch: {len(js_jobs)}")

    unique = deduplicate_jobs(all_jobs)
    print(f"After dedup: {len(unique)} unique jobs")

    filtered = filter_by_location(unique, work_location)
    print(f"After location filter: {len(filtered)} jobs")

    # Sort: direct auto-apply platforms first
    filtered.sort(key=lambda x: (
        0 if x.get("apply_platform") in ["greenhouse", "lever", "ashby"] else 1,
        x.get("source", "")
    ))

    diversified = cap_per_company(filtered, max_per_company=5)
    companies_count = len(set(j.get("company", "").lower() for j in diversified))
    print(f"After company cap (5/company): {len(diversified)} jobs from {companies_count} companies")

    final = diversified[:max_jobs]
    auto_count = len([j for j in final if j.get("apply_platform") in ["greenhouse", "lever", "ashby"]])
    print(f"Final: {len(final)} jobs | {auto_count} auto-apply ready\n")

    return final


if __name__ == "__main__":
    jobs = find_all_jobs(max_jobs=50, work_location="hybrid")
    platforms = {}
    sources = {}
    for j in jobs:
        p = j.get("apply_platform", "unknown")
        s = j.get("source", "unknown")
        platforms[p] = platforms.get(p, 0) + 1
        sources[s] = sources.get(s, 0) + 1
    print("\nPlatform breakdown:")
    for p, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
        print(f"  {p}: {count}")
    print("\nSource breakdown:")
    for s, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {s}: {count}")
