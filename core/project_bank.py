import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"

def load_repos() -> list[dict]:
    """Load all dedicated repos from repos.json"""
    with open(DATA_DIR / "repos.json", "r") as f:
        data = json.load(f)
    return data["repositories"]

def load_mono_repo_projects() -> list[dict]:
    """Parse LOCATION.md and extract all 50 projects"""
    with open(DATA_DIR / "LOCATION.md", "r", encoding="utf-8") as f:
        content = f.read()

    projects = []
    current_category = ""

    for line in content.split("\n"):
        # detect category headers
        if line.startswith("## "):
            current_category = line.replace("## ", "").replace("🏥", "").replace("💰", "").replace("👤", "").replace("🎯", "").replace("🖼️", "").replace("📝", "").replace("📊", "").replace("🎵", "").replace("🤖", "").replace("📚", "").strip()

        # detect table rows with project data
        if line.startswith("| ") and "ipynb" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                # get project name and location
                name = parts[1] if parts[0].isdigit() else parts[0]
                location = parts[2] if parts[0].isdigit() else parts[1]

                projects.append({
                    "name": name,
                    "category": current_category,
                    "location": location,
                    "repo_url": f"https://github.com/Abdrakib/AI_ML-Portfolio/tree/main/{location.split('/')[0]}",
                    "has_demo": False,
                    "source": "mono_repo",
                    "status": "complete"
                })

    return projects

def get_all_projects() -> dict:
    """
    Returns everything the agent knows about Rakib's projects.
    Combines dedicated repos + mono-repo projects.
    """
    repos = load_repos()
    mono_projects = load_mono_repo_projects()

    return {
        "dedicated_repos": repos,
        "mono_repo_projects": mono_projects,
        "total_dedicated": len(repos),
        "total_mono": len(mono_projects),
        "total": len(repos) + len(mono_projects)
    }

def get_projects_by_domain(domain_keyword: str) -> list[dict]:
    """
    Find all projects matching a domain keyword.
    Used by the job scorer to pick best projects per job.
    """
    keyword = domain_keyword.lower()
    matches = []

    repos = load_repos()
    for repo in repos:
        searchable = (
            repo.get("domain", "") +
            " ".join(repo.get("topics", [])) +
            " ".join(repo.get("skills_demonstrated", [])) +
            repo.get("description", "")
        ).lower()

        if keyword in searchable:
            matches.append({**repo, "source": "dedicated_repo"})

    mono_projects = load_mono_repo_projects()
    for project in mono_projects:
        if keyword in project.get("category", "").lower() or keyword in project.get("name", "").lower():
            matches.append(project)

    return matches

def get_best_projects_for_job(job_description: str, top_n: int = 5) -> list[dict]:
    """
    Simple keyword matching to pre-filter projects before Claude scores them.
    Claude does the final smart selection.
    """
    keywords = [
        "computer vision", "nlp", "llm", "deep learning", "machine learning",
        "finance", "medical", "audio", "reinforcement learning", "data science",
        "full stack", "fastapi", "react", "transformer", "generative ai"
    ]

    job_lower = job_description.lower()
    matched_domains = [kw for kw in keywords if kw in job_lower]

    all_matches = []
    for domain in matched_domains:
        matches = get_projects_by_domain(domain)
        all_matches.extend(matches)

    # deduplicate by name
    seen = set()
    unique_matches = []
    for p in all_matches:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique_matches.append(p)

    # prioritize dedicated repos with demos
    unique_matches.sort(key=lambda x: (
        x.get("source") == "dedicated_repo",
        x.get("has_demo") or x.get("live_demo") is not None
    ), reverse=True)

    return unique_matches[:top_n]

if __name__ == "__main__":
    # test it
    all_projects = get_all_projects()
    print(f"Total dedicated repos: {all_projects['total_dedicated']}")
    print(f"Total mono-repo projects: {all_projects['total_mono']}")
    print(f"Grand total: {all_projects['total']}")
    print("\nTesting domain search for 'computer vision':")
    cv_projects = get_projects_by_domain("computer vision")
    for p in cv_projects:
        print(f"  - {p['name']} ({p.get('source', 'unknown')})")
