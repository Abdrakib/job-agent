import requests
import json
import os
import base64
import re
from pathlib import Path
from dotenv import load_dotenv
from core.tracker import save_application, already_applied

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"


def extract_lever_info(apply_url: str) -> tuple:
    """
    Extract company and posting ID from Lever URL.
    Examples:
    - https://jobs.lever.co/stripe/abc123-def456
    - https://lever.co/notion/abc123
    Returns (company_slug, posting_id) or (None, None)
    """
    patterns = [
        r"jobs\.lever\.co/([^/]+)/([a-f0-9-]+)",
        r"lever\.co/([^/]+)/([a-f0-9-]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, apply_url)
        if match:
            return match.group(1), match.group(2)

    return None, None


def get_lever_job_details(company_slug: str, posting_id: str) -> dict:
    """Fetch job posting details from Lever public API"""
    url = f"https://api.lever.co/v0/postings/{company_slug}/{posting_id}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Lever API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"  Failed to fetch Lever job: {e}")
        return None


def build_lever_application(
    candidate_profile: dict,
    job_details: dict,
    cover_letter_text: str,
    resume_path: str
) -> dict:
    """Build the application payload for Lever API"""

    name = candidate_profile.get("name", "Abdou Rakib Abente")
    email = candidate_profile.get("email", "Rakibabente8@gmail.com")
    phone = candidate_profile.get("phone", "+12673445217")

    # Lever uses multipart form data
    form_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "org": "",  # current organization
        "urls[LinkedIn]": "https://linkedin.com/in/rakib-abente",
        "urls[GitHub]": "https://github.com/Abdrakib",
        "urls[Portfolio]": "https://abdourakib.com",
        "comments": cover_letter_text[:3000] if cover_letter_text else "",
        "silent": "false",
        "source": "Job Board"
    }

    return form_data


def apply_lever(
    job: dict,
    scored_job: dict,
    candidate_profile: dict,
    cover_letter_text: str,
    resume_path: str
) -> dict:
    """
    Submit application to a Lever job posting.
    Returns result dict with success status.
    """
    apply_url = job.get("apply_url", "")
    company = job.get("company", "")
    title = job.get("title", "")

    print(f"\n  Applying to: {title} at {company} via Lever")

    # check duplicate
    if already_applied(company, title):
        print(f"  Skipping — already applied to {company}")
        return {"success": False, "reason": "duplicate", "company": company, "title": title}

    # extract company slug and posting ID
    company_slug, posting_id = extract_lever_info(apply_url)

    if not company_slug or not posting_id:
        print(f"  Could not extract Lever info from URL: {apply_url}")
        return {"success": False, "reason": "invalid_url", "company": company, "title": title}

    print(f"  Company: {company_slug} | Posting: {posting_id}")

    # build form data
    form_data = build_lever_application(
        candidate_profile, None, cover_letter_text, resume_path
    )

    # prepare files
    files = {}
    if resume_path and Path(resume_path).exists():
        files["resume"] = (
            Path(resume_path).name,
            open(resume_path, "rb"),
            "application/pdf"
        )

    # submit to Lever API
    api_url = f"https://api.lever.co/v0/postings/{company_slug}/{posting_id}/apply"

    try:
        if files:
            response = requests.post(
                api_url,
                data=form_data,
                files=files,
                timeout=30
            )
        else:
            response = requests.post(
                api_url,
                data=form_data,
                timeout=30
            )

        # close file handle
        if "resume" in files:
            files["resume"][1].close()

        if response.status_code in [200, 201]:
            print(f"  ✅ Applied successfully to {company}!")

            save_application(
                job_id=job.get("id", ""),
                company=company,
                title=title,
                platform="lever",
                apply_url=apply_url,
                cover_letter_path=None,
                resume_path=resume_path
            )

            return {
                "success": True,
                "company": company,
                "title": title,
                "platform": "lever",
                "response_code": response.status_code
            }
        else:
            print(f"  ❌ Failed: {response.status_code} — {response.text[:200]}")
            return {
                "success": False,
                "reason": f"API error {response.status_code}",
                "company": company,
                "title": title
            }

    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return {"success": False, "reason": str(e), "company": company, "title": title}


def apply_to_all_lever_jobs(
    scored_jobs: list,
    candidate_profile: dict,
    cover_letters: dict,
    resume_paths: dict
) -> list:
    """Apply to all Lever jobs in the scored list"""
    results = []
    lever_jobs = [j for j in scored_jobs if j.get("apply_platform") == "lever"]

    print(f"\nFound {len(lever_jobs)} Lever jobs to apply to")

    for job in lever_jobs:
        job_id = job.get("job_id", "")
        cover_letter = cover_letters.get(job_id, "")
        resume_path = resume_paths.get(job_id, str(DATA_DIR / "base_resume.pdf"))

        result = apply_lever(
            job=job,
            scored_job=job,
            candidate_profile=candidate_profile,
            cover_letter_text=cover_letter,
            resume_path=resume_path
        )
        results.append(result)

    successful = [r for r in results if r.get("success")]
    print(f"\nLever results: {len(successful)}/{len(results)} successful")
    return results


if __name__ == "__main__":
    # test with a sample Lever URL
    test_url = "https://jobs.lever.co/anthropic/abc123-def456"
    company, posting = extract_lever_info(test_url)
    print(f"Company: {company}, Posting: {posting}")
