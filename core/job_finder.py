"""
job_finder.py — Job discovery using JSearch API + Greenhouse/Lever direct APIs
Strategy:
  1. Greenhouse direct API → guaranteed auto-apply URLs
  2. Lever direct API → guaranteed auto-apply URLs  
  3. JSearch → high volume, fills the rest
  4. Deduplicate + filter by location preference
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

# 14 targeted ML/AI queries — covers all relevant roles
JSEARCH_QUERIES = [
    "machine learning engineer intern remote",
    "AI engineer intern remote",
    "machine learning internship entry level",
    "generative AI engineer entry level",
    "NLP engineer intern remote",
    "computer vision engineer intern",
    "deep learning engineer intern",
    "LLM engineer entry level remote",
    "data scientist intern remote",
    "applied machine learning intern",
    "AI research intern remote",
    "junior ML engineer remote",
    "generative AI intern",
    "AI software engineer intern remote",
]

# ML/AI keywords to filter relevant jobs
ML_KEYWORDS = [
    "machine learning", "ml engineer", "ai engineer", "artificial intelligence",
    "deep learning", "nlp", "natural language", "computer vision",
    "data scientist", "data science", "llm", "generative ai",
    "neural network", "pytorch", "tensorflow", "ai researcher",
    "applied scientist", "research engineer", "ai intern", "ml intern",
    "software engineer", "backend engineer", "full stack", "python developer"
]

# Roles to exclude — too senior or irrelevant
EXCLUDE_KEYWORDS = [
    "senior director", "vp of", "vice president", "chief ",
    "principal engineer", "staff engineer", "distinguished engineer",
    "10+ years", "15+ years", "12+ years", "8+ years",
    "phd required", "physics", "chemistry", "biology", "genomics",
    "hardware", "fpga", "embedded", "firmware", "sales", "marketing",
    "recruiter", "hr ", "accounting", "legal", "financial analyst"
]


def make_job_id(title: str, company: str, source: str) -> str:
    raw = f"{source}_{title}_{company}".lower().replace(" ", "_")
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def detect_platform(url: str) -> str:
    if not url:
        return "direct"
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
    return "direct"


def is_relevant(title: str, description: str = "") -> bool:
    """Check if job is relevant ML/AI role for Rakib"""
    title_lower = title.lower()
    desc_lower = (description or "").lower()[:300]

    for kw in EXCLUDE_KEYWORDS:
        if kw in title_lower:
            return False

    combined = title_lower + " " + desc_lower
    return any(kw in combined for kw in ML_KEYWORDS)


# ─────────────────────────────────────────────
# SOURCE 1: Greenhouse Direct API
# ─────────────────────────────────────────────

# 150+ companies that use Greenhouse and hire ML/AI roles
GREENHOUSE_COMPANIES = [
    "anthropic", "openai", "scale", "cohere", "huggingface",
    "mistral", "adept", "inflection", "perplexity", "together",
    "nvidia", "google", "meta", "apple", "microsoft",
    "amazon", "stripe", "airbnb", "lyft", "doordash",
    "robinhood", "plaid", "brex", "rippling", "gusto",
    "figma", "notion", "linear", "vercel", "supabase",
    "datadog", "snowflake", "databricks", "palantir", "confluent",
    "hashicorp", "mongodb", "elastic", "cockroachdb",
    "twilio", "cloudflare", "fastly", "pagerduty", "newrelic",
    "hubspot", "intercom", "zendesk", "freshworks",
    "asana", "airtable", "smartsheet", "clickup",
    "shopify", "klaviyo", "yotpo", "instacart",
    "waymo", "cruise", "aurora", "zoox",
    "anduril", "c3ai", "recursion", "veritone",
    "synthesia", "runway", "soundhound", "deepgram",
    "assemblyai", "grammarly", "jasper", "duolingo",
    "sentry", "mixpanel", "amplitude", "heap",
    "dbt-labs", "fivetran", "airbyte", "hightouch",
    "retool", "temporal", "prefect", "dagster",
    "pinecone", "weaviate", "weights-biases",
    "labelbox", "humanloop", "braintrust",
    "rocketlawyer", "ironclad", "docusign",
    "tome", "gamma", "canva", "pitch",
    "khan-academy", "coursera", "udacity", "brilliant",
    "sentry", "logrocket", "fullstory", "posthog",
    "segment", "rudderstack", "census",
    "modal", "replicate", "lambdalabs",
    "groq", "sambanova", "cerebras",
    "primer", "shield-ai", "saildrone",
    "benchling", "insitro", "recursion",
    "nuro", "gatik", "kodiak", "embark",
    "scale-ai", "appen", "defined",
    "comet", "neptune-ai", "determined-ai",
    "cleanlab", "aquarium", "encord",
    "langchain", "llamaindex", "guardrails-ai",
    "vectara", "zilliz", "qdrant",
    "arize", "fiddler", "evidently",
    "tecton", "feast", "hopsworks",
    "superwise", "arthur", "truera",
    "snorkel", "scale", "surge",
    "predibase", "h2oai", "datarobot",
    "bigpanda", "moogsoft", "blameless",
    "observe", "honeycomb", "lightstep",
    "chronosphere", "coralogix", "logz",
]


def fetch_greenhouse_jobs() -> list:
    """Fetch ML/AI jobs directly from Greenhouse public board API — no auth needed"""
    print("  [Greenhouse] Scanning company boards...")
    jobs = []
    errors = 0

    for company in GREENHOUSE_COMPANIES:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
            resp = requests.get(url, timeout=6)

            if resp.status_code != 200:
                continue

            for job in resp.json().get("jobs", []):
                title = job.get("title", "")
                if not is_relevant(title):
                    continue

                location_data = job.get("location", {})
                location = location_data.get("name", "") if isinstance(location_data, dict) else str(location_data)
                job_id = job.get("id", "")
                apply_url = f"https://boards.greenhouse.io/{company}/jobs/{job_id}"

                jobs.append({
                    "id": make_job_id(title, company, "greenhouse"),
                    "title": title,
                    "company": company.replace("-", " ").title(),
                    "location": location,
                    "country": "US",
                    "is_remote": any(w in location.lower() for w in ["remote", "anywhere", "distributed", "worldwide"]),
                    "is_local": "philadelphia" in location.lower() or "pa" in location.lower(),
                    "description": title,
                    "apply_url": apply_url,
                    "posted_date": job.get("updated_at", ""),
                    "employment_type": "",
                    "apply_platform": "greenhouse",
                    "employer_logo": "",
                    "salary_min": None,
                    "salary_max": None,
                    "source": "greenhouse_direct"
                })

        except Exception:
            errors += 1
            continue

    print(f"  [Greenhouse] Found {len(jobs)} ML/AI jobs ({errors} companies unreachable)")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 2: Lever Direct API
# ─────────────────────────────────────────────

LEVER_COMPANIES = [
    "openai", "anthropic", "cohere", "mistral", "adept",
    "scale-ai", "imbue", "aleph-alpha", "stability-ai",
    "nvidia", "amd", "qualcomm", "intel", "arm",
    "stripe", "plaid", "brex", "mercury", "ramp",
    "notion", "coda", "craft-docs",
    "linear", "height", "shortcut",
    "vercel", "netlify", "render", "railway",
    "cloudflare", "fastly", "akamai",
    "datadog", "grafana", "elastic",
    "mongodb", "redis", "neo4j",
    "huggingface", "together-ai", "replicate",
    "weights-biases", "neptune-ai", "comet-ml",
    "labelbox", "scale", "humanloop",
    "grammarly", "writer", "jasper",
    "duolingo", "brilliant", "coursera",
    "sentry", "datadog", "newrelic",
    "segment", "rudderstack", "mparticle",
    "figma", "sketch", "invision",
    "asana", "monday", "clickup",
    "shopify", "klaviyo", "recharge",
    "instacart", "gopuff", "getir",
    "waymo", "aurora", "motional",
    "anduril", "shield-ai", "palantir",
    "recursion", "insitro", "insilico-medicine",
    "soundhound", "deepgram", "assemblyai",
    "runway-ml", "pika-labs", "synthesia",
    "ramp", "brex", "mercury", "pilot",
    "rippling", "gusto", "deel", "remote",
    "lattice", "culture-amp", "leapsome",
    "gem", "greenhouse", "lever",
    "retool", "airplane", "internal",
    "temporal", "replit", "gitpod",
    "dbt-labs", "airbyte", "fivetran",
    "pinecone", "weaviate", "chroma",
    "modal", "beam", "banana",
    "langchain", "llamaindex",
    "arize-ai", "fiddler-ai", "evidently-ai",
    "snorkel-ai", "predibase", "h2o",
]


def fetch_lever_jobs() -> list:
    """Fetch ML/AI jobs directly from Lever public posting API — no auth needed"""
    print("  [Lever] Scanning company boards...")
    jobs = []
    errors = 0

    for company in LEVER_COMPANIES:
        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            resp = requests.get(url, timeout=6)

            if resp.status_code != 200:
                continue

            for job in resp.json():
                title = job.get("text", "")
                description = job.get("descriptionPlain", "")
                if not is_relevant(title, description):
                    continue

                categories = job.get("categories", {})
                location = categories.get("location", "")
                commitment = categories.get("commitment", "")
                apply_url = job.get("hostedUrl", "")

                jobs.append({
                    "id": make_job_id(title, company, "lever"),
                    "title": title,
                    "company": company.replace("-", " ").title(),
                    "location": location,
                    "country": "US",
                    "is_remote": any(w in location.lower() for w in ["remote", "anywhere", "distributed", "worldwide"]),
                    "is_local": "philadelphia" in location.lower() or "pa" in location.lower(),
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

        except Exception:
            errors += 1
            continue

    print(f"  [Lever] Found {len(jobs)} ML/AI jobs ({errors} companies unreachable)")
    return jobs


# ─────────────────────────────────────────────
# SOURCE 3: JSearch API (high volume)
# ─────────────────────────────────────────────

def fetch_jsearch_jobs(work_location: str = "remote") -> list:
    """Fetch from JSearch — 14 targeted queries, 1500 calls/month plan"""
    if not RAPIDAPI_KEY:
        print("  [JSearch] No API key, skipping")
        return []

    print(f"  [JSearch] Running {len(JSEARCH_QUERIES)} queries...")
    jobs = []

    for query in JSEARCH_QUERIES:
        try:
            params = {
                "query": query,
                "page": "1",
                "num_pages": "2",  # 2 pages = 20 results per query
                "date_posted": "week",  # fresh jobs only
                "employment_types": "FULLTIME,INTERN,PARTTIME",
                "job_requirements": "no_experience,under_3_years_experience",
                "remote_jobs_only": "true" if work_location == "remote" else "false"
            }

            resp = requests.get(JSEARCH_URL, headers=JSEARCH_HEADERS, params=params, timeout=30)
            data = resp.json()

            if data.get("status") == "OK":
                for raw in data.get("data", []):
                    title = raw.get("job_title", "")
                    if not is_relevant(title, raw.get("job_description", "")):
                        continue

                    company = raw.get("employer_name", "")
                    city = raw.get("job_city") or ""
                    state = raw.get("job_state") or ""
                    location = f"{city}, {state}".strip(", ")
                    apply_url = raw.get("job_apply_link", "")

                    jobs.append({
                        "id": make_job_id(title, company, "jsearch"),
                        "title": title,
                        "company": company,
                        "location": location,
                        "country": raw.get("job_country", "US"),
                        "is_remote": raw.get("job_is_remote", False),
                        "is_local": "philadelphia" in location.lower() or ", pa" in location.lower(),
                        "description": raw.get("job_description", "")[:2000],
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

            time.sleep(0.5)  # small delay to avoid throttling

        except Exception as e:
            print(f"  [JSearch] Error for '{query}': {e}")

    print(f"  [JSearch] Found {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────
# DEDUP + FILTER
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
    if work_location == "remote":
        return [j for j in jobs if j.get("is_remote") or j.get("apply_platform") in ["greenhouse", "lever"]]
    elif work_location == "hybrid":
        return [j for j in jobs if
                j.get("is_remote") or j.get("is_local") or
                "hybrid" in (j.get("location") or "").lower() or
                j.get("apply_platform") in ["greenhouse", "lever"]]
    elif work_location == "onsite":
        return [j for j in jobs if j.get("is_local") or not j.get("is_remote")]
    return jobs  # any


def find_all_jobs(max_jobs: int = 100, work_location: str = "remote") -> list:
    """
    Main discovery function.
    Priority order: Greenhouse → Lever → JSearch
    Greenhouse + Lever = auto-apply guaranteed
    JSearch = volume + variety
    """
    print(f"\n{'='*50}")
    print(f"JOB DISCOVERY — {work_location.upper()} | max {max_jobs}")
    print(f"Sources: Greenhouse Direct, Lever Direct, JSearch")
    print(f"{'='*50}\n")

    all_jobs = []

    # Priority 1: Greenhouse (auto-apply)
    gh_jobs = fetch_greenhouse_jobs()
    all_jobs.extend(gh_jobs)

    # Priority 2: Lever (auto-apply)
    lv_jobs = fetch_lever_jobs()
    all_jobs.extend(lv_jobs)

    # Priority 3: JSearch (volume)
    js_jobs = fetch_jsearch_jobs(work_location)
    all_jobs.extend(js_jobs)

    print(f"\nRaw total: {len(all_jobs)} jobs")
    print(f"  Greenhouse: {len(gh_jobs)} | Lever: {len(lv_jobs)} | JSearch: {len(js_jobs)}")

    unique = deduplicate_jobs(all_jobs)
    print(f"After dedup: {len(unique)} unique jobs")

    filtered = filter_by_location(unique, work_location)
    print(f"After location filter: {len(filtered)} jobs")

    # sort: auto-apply platforms first, then by source
    filtered.sort(key=lambda x: (
        0 if x.get("apply_platform") in ["greenhouse", "lever"] else 1,
        x.get("source", "")
    ))

    final = filtered[:max_jobs]
    auto_apply_count = len([j for j in final if j.get("apply_platform") in ["greenhouse", "lever"]])
    print(f"Final: {len(final)} jobs | {auto_apply_count} auto-apply ready\n")

    return final


if __name__ == "__main__":
    jobs = find_all_jobs(max_jobs=50, work_location="remote")
    platforms = {}
    for j in jobs:
        p = j.get("apply_platform", "unknown")
        platforms[p] = platforms.get(p, 0) + 1
    print("\nPlatform breakdown:")
    for p, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
        print(f"  {p}: {count}")
