import anthropic
import json
import os
from dotenv import load_dotenv
from core.project_bank import get_all_projects

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Jobs with these keywords in title are pre-filtered out — not relevant to Rakib
TITLE_BLACKLIST = [
    "physics", "chemistry", "biology", "biomedical", "genomics", "drug discovery",
    "life sciences", "clinical", "healthcare", "medical", "radiology", "pathology",
    "quant", "quantitative", "financial engineer", "actuar",
    "mathematics", "math research", "fluid dynamics", "materials science",
    "hardware", "fpga", "embedded", "firmware", "asic",
    "sales", "marketing", "recruiter", "hr ", "human resources",
    "phd required", "doctoral", "professor", "faculty",
    "graduate chemistry", "graduate physics", "graduate math",
]

# Companies known for spam/low-quality listings
COMPANY_BLACKLIST = [
    "dataannotation", "data annotation", "virtualvocations", "virtual vocations",
    "clickworker", "remotasks", "scale ai annotator",
]


def is_relevant_job(job: dict) -> bool:
    """Pre-filter jobs before sending to Claude. Returns False if job should be skipped."""
    title = (job.get("title") or "").lower()
    company = (job.get("company") or "").lower()
    description = (job.get("description") or "").lower()

    # check title blacklist
    for kw in TITLE_BLACKLIST:
        if kw in title:
            return False

    # check company blacklist
    for kw in COMPANY_BLACKLIST:
        if kw in company:
            return False

    # skip jobs requiring PhD
    phd_signals = ["phd required", "phd students only", "must be enrolled in phd",
                   "pursuing a phd", "doctoral students", "phd candidate required"]
    for signal in phd_signals:
        if signal in description:
            return False

    return True


def score_job(job: dict, candidate_profile: dict, all_projects: dict) -> dict:
    """
    Claude scores a single job against Rakib's profile.
    Returns match score, best projects to highlight, and reasoning.
    """

    dedicated_repos = all_projects["dedicated_repos"]
    mono_projects = all_projects["mono_repo_projects"]

    project_summary = "DEDICATED REPOS (with demos):\n"
    for repo in dedicated_repos:
        demo = repo.get("live_demo") or "no demo"
        project_summary += f"- {repo['name']}: {repo['description'][:100]} | Domain: {repo['domain']} | Demo: {demo}\n"

    project_summary += "\nMONO-REPO PROJECTS (50+ notebooks):\n"
    categories = {}
    for p in mono_projects:
        cat = p.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(p["name"])

    for cat, names in categories.items():
        project_summary += f"- {cat}: {', '.join(names[:5])}\n"

    prompt = f"""You are an expert recruiter scoring a job for this specific candidate. Be accurate and strict.

CANDIDATE PROFILE:
Name: {candidate_profile.get('name')}
Education: Associate's degree in Computer Science (Community College of Philadelphia, May 2026)
Experience: ML Intern at Buildawn Labs (computer vision, LLMs, RL). Currently DSP worker.
Skills: {json.dumps(candidate_profile.get('skills', {}))}
Summary: {candidate_profile.get('summary')}

CANDIDATE PROJECTS:
{project_summary}

JOB TO SCORE:
Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')} (Remote: {job.get('is_remote')})
Description: {job.get('description', '')[:2000]}

IMPORTANT SCORING RULES — apply these strictly:
1. If the job requires a PhD or is for PhD students only → score 0-20, recommend SKIP
2. If the job is in a domain Rakib has no background in (physics, chemistry, biology, finance/quant, hardware) → score 0-35, recommend SKIP even if it mentions ML/AI
3. If the job requires 3+ years of experience and isn't entry-level/intern → score below 50
4. Strong fits: ML engineering, AI engineering, NLP, computer vision, LLM/generative AI, data science, AI agents, autonomous systems
5. The candidate has an Associate's degree only — be realistic about company fit

Return ONLY a JSON object with no markdown or extra text:
{{
    "match_score": <0-100 integer>,
    "recommendation": "<APPLY|SKIP|PRIORITY>",
    "reasoning": "<2-3 sentences why this score. Be specific about fit or misfit.>",
    "best_projects": [
        {{
            "name": "<project name>",
            "reason": "<why this project fits this job>"
        }}
    ],
    "missing_skills": ["<skill the job wants that candidate lacks>"],
    "strengths": ["<candidate strength that fits this job>"],
    "cover_letter_angle": "<the key angle/hook to use in the cover letter for this specific job>",
    "priority_flag": <true only if company is well-known tech company or role is exceptional match>
}}

Scoring guide:
- 90-100: Perfect match, apply immediately
- 75-89: Strong match, definitely apply
- 60-74: Good match, worth applying
- 40-59: Partial match, borderline
- 0-39: Poor match or domain mismatch, skip

Select exactly 3-5 best projects from the candidate's portfolio that match this specific job."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)

    result["job_id"] = job.get("id")
    result["job_title"] = job.get("title")
    result["company"] = job.get("company")
    result["apply_url"] = job.get("apply_url")
    result["apply_platform"] = job.get("apply_platform")
    result["location"] = job.get("location")
    result["is_remote"] = job.get("is_remote")
    result["job_description"] = job.get("description", "")[:500]

    return result


def score_all_jobs(jobs: list[dict], candidate_profile: dict, min_score: int = 70) -> list[dict]:
    """
    Score all jobs and return only those above the minimum score.
    Pre-filters irrelevant jobs before calling Claude.
    Sorted by match score descending.
    """
    all_projects = get_all_projects()

    # pre-filter before hitting Claude API
    relevant_jobs = [j for j in jobs if is_relevant_job(j)]
    filtered_out = len(jobs) - len(relevant_jobs)
    print(f"Pre-filter: removed {filtered_out} irrelevant jobs, {len(relevant_jobs)} remaining\n")

    scored_jobs = []
    print(f"Scoring {len(relevant_jobs)} jobs with Claude...\n")

    for i, job in enumerate(relevant_jobs):
        try:
            print(f"  [{i+1}/{len(relevant_jobs)}] Scoring: {job.get('title')} at {job.get('company')}...")
            scored = score_job(job, candidate_profile, all_projects)
            scored_jobs.append(scored)

            score = scored.get("match_score", 0)
            rec = scored.get("recommendation", "")
            print(f"    Score: {score}/100 | {rec}")

        except Exception as e:
            print(f"    Error scoring job: {e}")
            continue

    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    qualified = [j for j in scored_jobs if j.get("match_score", 0) >= min_score]

    print(f"\nScoring complete:")
    print(f"  Total scored: {len(scored_jobs)}")
    print(f"  Above {min_score}% threshold: {len(qualified)}")
    print(f"  Priority jobs: {len([j for j in qualified if j.get('priority_flag')])}")

    return qualified


if __name__ == "__main__":
    from core.job_finder import find_all_jobs
    from core.resume_parser import get_candidate_profile

    print("Loading candidate profile...")
    profile = get_candidate_profile()

    print("Finding jobs...")
    jobs = find_all_jobs(max_jobs=5)

    print("\nScoring jobs...")
    scored = score_all_jobs(jobs, profile, min_score=60)

    print("\n--- TOP MATCHES ---")
    for job in scored[:5]:
        print(f"\n{job['job_title']} at {job['company']}")
        print(f"  Score: {job['match_score']}/100 | {job['recommendation']}")
        print(f"  Reasoning: {job['reasoning']}")
        print(f"  Best projects: {[p['name'] for p in job.get('best_projects', [])]}")
