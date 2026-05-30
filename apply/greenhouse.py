"""
greenhouse.py — Greenhouse public API auto-apply
Submits applications directly via Greenhouse's public board API.
No browser needed — pure HTTP requests.
"""
import requests
import json
import os
import re
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"

# Daily apply limit
MAX_PER_DAY = int(os.getenv("MAX_AUTO_APPLY_PER_DAY", "20"))


def extract_greenhouse_board(apply_url: str) -> tuple:
    """Extract (board_token, job_id) from any Greenhouse URL format"""
    patterns = [
        r"greenhouse\.io/([^/]+)/jobs/(\d+)",
        r"boards\.greenhouse\.io/([^/]+)/jobs/(\d+)",
        r"job-boards\.greenhouse\.io/([^/]+)/jobs/(\d+)",
        r"boards-api\.greenhouse\.io/v1/boards/([^/]+)/jobs/(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, apply_url)
        if match:
            return match.group(1), match.group(2)
    return None, None


def get_job_questions(board_token: str, job_id: str) -> list:
    """Fetch custom application questions for a Greenhouse job"""
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("questions", [])
    except Exception:
        pass
    return []


def answer_question(label: str, q_type: str, candidate_profile: dict) -> str:
    """Intelligently answer any Greenhouse application question"""
    label_lower = label.lower()

    # URLs and social
    if "github" in label_lower:
        return "https://github.com/Abdrakib"
    if "linkedin" in label_lower:
        return "https://linkedin.com/in/rakib-abente"
    if "portfolio" in label_lower or "website" in label_lower or "personal site" in label_lower:
        return "https://abdourakib.com"
    if "huggingface" in label_lower:
        return "https://huggingface.co/Abdourakib"

    # Work authorization
    if any(w in label_lower for w in ["authorized", "eligible", "visa", "sponsorship", "work in the us"]):
        return "Yes"
    if "require sponsorship" in label_lower or "need sponsorship" in label_lower:
        return "No"

    # Education
    if "degree" in label_lower or "highest education" in label_lower:
        return "Associate's Degree"
    if "school" in label_lower or "university" in label_lower or "institution" in label_lower:
        return "Community College of Philadelphia"
    if "major" in label_lower or "field of study" in label_lower:
        return "Computer Science"
    if "graduation" in label_lower or "grad date" in label_lower:
        return "May 2026"
    if "gpa" in label_lower:
        return "3.5"

    # Experience
    if "years of experience" in label_lower or "years experience" in label_lower:
        return "1"
    if "current company" in label_lower or "employer" in label_lower:
        return "Buildawn Labs (ML Internship)"
    if "current title" in label_lower or "current role" in label_lower:
        return "Machine Learning Intern"

    # Availability
    if "start date" in label_lower or "available" in label_lower:
        return "Immediately"
    if "notice period" in label_lower:
        return "2 weeks"

    # Salary
    if "salary" in label_lower or "compensation" in label_lower or "expected" in label_lower:
        return "70000"

    # Location
    if "city" in label_lower:
        return "Philadelphia"
    if "state" in label_lower:
        return "Pennsylvania"
    if "country" in label_lower:
        return "United States"
    if "zip" in label_lower or "postal" in label_lower:
        return "19111"

    # How did you hear
    if any(w in label_lower for w in ["hear about", "find out", "referred", "source"]):
        return "LinkedIn"

    # Race/ethnicity (optional, answer prefer not to say)
    if "race" in label_lower or "ethnicity" in label_lower:
        return "Decline to self-identify"

    # Gender (optional)
    if "gender" in label_lower:
        return "Decline to self-identify"

    # Veteran status
    if "veteran" in label_lower or "military" in label_lower:
        return "I am not a protected veteran"

    # Disability
    if "disability" in label_lower or "disabled" in label_lower:
        return "I don't wish to answer"

    # Remote/hybrid
    if "remote" in label_lower or "hybrid" in label_lower or "onsite" in label_lower:
        return "Yes"

    # Cover letter as text
    if "cover letter" in label_lower and q_type in ["textarea", "long_text"]:
        return ""  # handled separately

    return ""


def build_application_payload(
    candidate_profile: dict,
    questions: list,
    cover_letter_text: str,
    resume_path: str
) -> dict:
    """Build complete Greenhouse application payload"""
    name_parts = candidate_profile.get("name", "Abdou Rakib Abente").split()
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else name_parts[-1]

    # encode resume
    resume_b64 = ""
    resume_filename = "resume_abdou_rakib.pdf"
    resume_file = Path(resume_path) if resume_path else None

    if resume_file and resume_file.exists():
        with open(resume_file, "rb") as f:
            resume_b64 = base64.b64encode(f.read()).decode("utf-8")
        resume_filename = resume_file.name

    # encode cover letter
    cl_b64 = ""
    if cover_letter_text:
        cl_b64 = base64.b64encode(cover_letter_text.encode("utf-8")).decode("utf-8")

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email": candidate_profile.get("email", "Rakibabente8@gmail.com"),
        "phone": candidate_profile.get("phone", "+12673445217"),
        "resume_content": resume_b64,
        "resume_content_filename": resume_filename,
        "cover_letter_content": cl_b64,
        "cover_letter_content_filename": "cover_letter_abdou_rakib.txt",
        "linkedin_profile_url": "https://linkedin.com/in/rakib-abente",
        "website": "https://abdourakib.com",
        "social_media_urls": [{"url": "https://github.com/Abdrakib"}],
        "mapped_questions": []
    }

    # answer all custom questions
    for q in questions:
        q_id = q.get("id")
        q_label = q.get("label", "")
        q_type = q.get("type", "input_text")
        q_required = q.get("required", False)

        if not q_id:
            continue

        # skip questions already handled in main payload
        label_lower = q_label.lower()
        if any(w in label_lower for w in ["first name", "last name", "email", "phone", "resume", "cover letter"]):
            continue

        answer = answer_question(q_label, q_type, candidate_profile)

        # for cover letter text questions
        if "cover letter" in label_lower and not answer:
            answer = cover_letter_text[:3000] if cover_letter_text else ""

        if answer or q_required:
            payload["mapped_questions"].append({
                "id": q_id,
                "answer": answer or ""
            })

    return payload


def apply_greenhouse(
    job: dict,
    scored_job: dict,
    candidate_profile: dict,
    cover_letter_text: str,
    resume_path: str,
    applied_today_count: int = 0
) -> dict:
    """
    Submit application to Greenhouse.
    Returns result dict with success/failure details.
    """
    apply_url = job.get("apply_url", "")
    company = job.get("company", scored_job.get("company", ""))
    title = job.get("title", scored_job.get("job_title", ""))

    # daily limit check
    if applied_today_count >= MAX_PER_DAY:
        return {"success": False, "reason": "daily_limit_reached", "company": company, "title": title}

    # duplicate check
    from core.tracker import already_applied
    if already_applied(company, title):
        return {"success": False, "reason": "duplicate", "company": company, "title": title}

    # extract board token + job ID
    board_token, job_id = extract_greenhouse_board(apply_url)
    if not board_token or not job_id:
        print(f"  [Greenhouse] Could not parse URL: {apply_url}")
        return {"success": False, "reason": "invalid_url", "company": company, "title": title}

    print(f"  [Greenhouse] Applying: {title} at {company} (board: {board_token}, job: {job_id})")

    # get custom questions
    questions = get_job_questions(board_token, job_id)

    # build payload
    payload = build_application_payload(
        candidate_profile, questions, cover_letter_text, resume_path
    )

    # submit application
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
    try:
        resp = requests.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if resp.status_code in [200, 201]:
            print(f"  [Greenhouse] ✅ Applied: {title} at {company}")
            return {
                "success": True,
                "company": company,
                "title": title,
                "platform": "greenhouse",
                "apply_url": apply_url,
                "status_code": resp.status_code
            }
        elif resp.status_code == 422:
            # unprocessable — missing required field
            print(f"  [Greenhouse] ⚠️  422 Unprocessable: {resp.text[:200]}")
            return {"success": False, "reason": f"422_unprocessable", "company": company, "title": title}
        elif resp.status_code == 403:
            print(f"  [Greenhouse] ⚠️  403 Forbidden — company disabled API submissions")
            return {"success": False, "reason": "api_disabled", "company": company, "title": title}
        else:
            print(f"  [Greenhouse] ❌ Failed {resp.status_code}: {resp.text[:100]}")
            return {"success": False, "reason": f"http_{resp.status_code}", "company": company, "title": title}

    except Exception as e:
        print(f"  [Greenhouse] ❌ Exception: {e}")
        return {"success": False, "reason": str(e)[:100], "company": company, "title": title}
