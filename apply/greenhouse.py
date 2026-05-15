import requests
import json
import os
import base64
from pathlib import Path
from dotenv import load_dotenv
from core.tracker import save_application, already_applied

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"


def extract_greenhouse_board(apply_url: str) -> tuple:
    """
    Extract company board token and job ID from a Greenhouse URL.
    Examples:
    - https://boards.greenhouse.io/stripe/jobs/12345
    - https://job-boards.greenhouse.io/notion/jobs/67890
    Returns (board_token, job_id) or (None, None)
    """
    import re

    patterns = [
        r"greenhouse\.io/([^/]+)/jobs/(\d+)",
        r"boards\.greenhouse\.io/([^/]+)/jobs/(\d+)",
        r"job-boards\.greenhouse\.io/([^/]+)/jobs/(\d+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, apply_url)
        if match:
            return match.group(1), match.group(2)

    return None, None


def get_greenhouse_job_details(board_token: str, job_id: str) -> dict:
    """Fetch job details from Greenhouse public API"""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Greenhouse API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"  Failed to fetch job details: {e}")
        return None


def get_greenhouse_questions(board_token: str, job_id: str) -> list:
    """Get application questions for a Greenhouse job"""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("questions", [])
        return []
    except:
        return []


def build_greenhouse_application(
    candidate_profile: dict,
    job_details: dict,
    cover_letter_text: str,
    resume_path: str
) -> dict:
    """
    Build the application payload for Greenhouse API.
    Maps candidate data to Greenhouse's expected format.
    """

    # read resume as base64
    resume_b64 = ""
    resume_filename = "resume.pdf"
    if resume_path and Path(resume_path).exists():
        with open(resume_path, "rb") as f:
            resume_b64 = base64.b64encode(f.read()).decode("utf-8")
        resume_filename = Path(resume_path).name

    # build payload
    payload = {
        "first_name": candidate_profile.get("name", "Abdou Rakib").split()[0],
        "last_name": " ".join(candidate_profile.get("name", "Abdou Rakib Abente").split()[1:]),
        "email": candidate_profile.get("email", "Rakibabente8@gmail.com"),
        "phone": candidate_profile.get("phone", "+12673445217"),
        "resume_content": resume_b64,
        "resume_content_filename": resume_filename,
        "cover_letter_content": base64.b64encode(
            cover_letter_text.encode("utf-8")
        ).decode("utf-8") if cover_letter_text else "",
        "cover_letter_content_filename": "cover_letter.txt",
        "linkedin_profile_url": "https://linkedin.com/in/rakib-abente",
        "website": "https://abdourakib.com",
        "social_media_urls": [
            {"url": "https://github.com/Abdrakib"}
        ],
        "mapped_questions": []
    }

    # handle standard questions
    questions = job_details.get("questions", []) if job_details else []
    for question in questions:
        q_id = question.get("id")
        q_label = question.get("label", "").lower()
        q_required = question.get("required", False)

        answer = None

        # map common questions to answers
        if "github" in q_label or "portfolio" in q_label:
            answer = "https://github.com/Abdrakib"
        elif "linkedin" in q_label:
            answer = "https://linkedin.com/in/rakib-abente"
        elif "website" in q_label or "personal" in q_label:
            answer = "https://abdourakib.com"
        elif "visa" in q_label or "authorized" in q_label or "sponsorship" in q_label:
            answer = "Yes"  # US citizen / authorized to work
        elif "degree" in q_label or "education" in q_label:
            answer = "Associate's Degree"
        elif "start" in q_label and "date" in q_label:
            answer = "Immediately"
        elif "salary" in q_label or "compensation" in q_label:
            answer = "Open to discussion"
        elif "heard" in q_label or "source" in q_label or "find" in q_label:
            answer = "Job board"

        if answer and q_id:
            payload["mapped_questions"].append({
                "id": q_id,
                "answer": answer
            })

    return payload


def apply_greenhouse(
    job: dict,
    scored_job: dict,
    candidate_profile: dict,
    cover_letter_text: str,
    resume_path: str
) -> dict:
    """
    Submit application to a Greenhouse job.
    Returns result dict with success status.
    """
    apply_url = job.get("apply_url", "")
    company = job.get("company", "")
    title = job.get("title", "")

    print(f"\n  Applying to: {title} at {company} via Greenhouse")

    # check duplicate
    if already_applied(company, title):
        print(f"  Skipping — already applied to {company}")
        return {"success": False, "reason": "duplicate", "company": company, "title": title}

    # extract board token and job ID
    board_token, job_id = extract_greenhouse_board(apply_url)

    if not board_token or not job_id:
        print(f"  Could not extract Greenhouse board token from URL: {apply_url}")
        return {"success": False, "reason": "invalid_url", "company": company, "title": title}

    print(f"  Board: {board_token} | Job ID: {job_id}")

    # get job details and questions
    job_details = get_greenhouse_job_details(board_token, job_id)

    # build payload
    payload = build_greenhouse_application(
        candidate_profile, job_details, cover_letter_text, resume_path
    )

    # submit application
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"

    try:
        response = requests.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code in [200, 201]:
            print(f"  ✅ Applied successfully to {company}!")

            # save to tracker
            save_application(
                job_id=job.get("id", ""),
                company=company,
                title=title,
                platform="greenhouse",
                apply_url=apply_url,
                cover_letter_path=None,
                resume_path=resume_path
            )

            return {
                "success": True,
                "company": company,
                "title": title,
                "platform": "greenhouse",
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


def apply_to_all_greenhouse_jobs(
    scored_jobs: list,
    candidate_profile: dict,
    cover_letters: dict,
    resume_paths: dict
) -> list:
    """
    Apply to all Greenhouse jobs in the scored list.
    cover_letters and resume_paths are dicts keyed by job_id.
    """
    results = []
    greenhouse_jobs = [j for j in scored_jobs if j.get("apply_platform") == "greenhouse"]

    print(f"\nFound {len(greenhouse_jobs)} Greenhouse jobs to apply to")

    for job in greenhouse_jobs:
        job_id = job.get("job_id", "")
        cover_letter = cover_letters.get(job_id, "")
        resume_path = resume_paths.get(job_id, str(DATA_DIR / "base_resume.pdf"))

        result = apply_greenhouse(
            job=job,
            scored_job=job,
            candidate_profile=candidate_profile,
            cover_letter_text=cover_letter,
            resume_path=resume_path
        )
        results.append(result)

    successful = [r for r in results if r.get("success")]
    print(f"\nGreenhouse results: {len(successful)}/{len(results)} successful")
    return results


if __name__ == "__main__":
    # test with a sample Greenhouse URL
    test_url = "https://boards.greenhouse.io/anthropic/jobs/4020305008"
    board, job_id = extract_greenhouse_board(test_url)
    print(f"Board: {board}, Job ID: {job_id}")

    if board and job_id:
        details = get_greenhouse_job_details(board, job_id)
        if details:
            print(f"Job: {details.get('title')} at {details.get('company_name')}")
            print(f"Questions: {len(details.get('questions', []))}")
