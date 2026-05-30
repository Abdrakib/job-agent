"""
lever.py — Lever public API auto-apply
Submits applications directly via Lever's public posting API.
No browser needed — multipart form submission.
"""
import requests
import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
MAX_PER_DAY = int(os.getenv("MAX_AUTO_APPLY_PER_DAY", "20"))


def extract_lever_info(apply_url: str) -> tuple:
    """Extract (company_slug, posting_id) from any Lever URL"""
    patterns = [
        r"jobs\.lever\.co/([^/]+)/([a-f0-9-]+)",
        r"lever\.co/([^/]+)/([a-f0-9-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, apply_url)
        if match:
            return match.group(1), match.group(2)
    return None, None


def answer_question(field_name: str, candidate_profile: dict) -> str:
    """Answer Lever custom form fields intelligently"""
    field_lower = field_name.lower()

    if "linkedin" in field_lower:
        return "https://linkedin.com/in/rakib-abente"
    if "github" in field_lower:
        return "https://github.com/Abdrakib"
    if "portfolio" in field_lower or "website" in field_lower:
        return "https://abdourakib.com"
    if "twitter" in field_lower:
        return ""
    if "salary" in field_lower or "compensation" in field_lower:
        return "70000"
    if "start" in field_lower or "available" in field_lower:
        return "Immediately"
    if "authorized" in field_lower or "visa" in field_lower or "sponsorship" in field_lower:
        return "Yes"
    if "years" in field_lower and "experience" in field_lower:
        return "1"
    if "degree" in field_lower or "education" in field_lower:
        return "Associate's Degree in Computer Science"
    if "school" in field_lower or "university" in field_lower:
        return "Community College of Philadelphia"
    if "graduation" in field_lower:
        return "May 2026"
    if "city" in field_lower:
        return "Philadelphia"
    if "state" in field_lower:
        return "Pennsylvania"
    if "country" in field_lower:
        return "United States"
    if "hear" in field_lower or "source" in field_lower or "referred" in field_lower:
        return "LinkedIn"
    if "remote" in field_lower or "hybrid" in field_lower:
        return "Yes"

    return ""


def apply_lever(
    job: dict,
    scored_job: dict,
    candidate_profile: dict,
    cover_letter_text: str,
    resume_path: str,
    applied_today_count: int = 0
) -> dict:
    """
    Submit application to Lever posting.
    Uses multipart form with resume file upload.
    """
    apply_url = job.get("apply_url", "")
    company = job.get("company", scored_job.get("company", ""))
    title = job.get("title", scored_job.get("job_title", ""))

    # daily limit
    if applied_today_count >= MAX_PER_DAY:
        return {"success": False, "reason": "daily_limit_reached", "company": company, "title": title}

    # duplicate check
    from core.tracker import already_applied
    if already_applied(company, title):
        return {"success": False, "reason": "duplicate", "company": company, "title": title}

    # extract company + posting ID
    company_slug, posting_id = extract_lever_info(apply_url)
    if not company_slug or not posting_id:
        print(f"  [Lever] Could not parse URL: {apply_url}")
        return {"success": False, "reason": "invalid_url", "company": company, "title": title}

    print(f"  [Lever] Applying: {title} at {company} (slug: {company_slug})")

    name_parts = candidate_profile.get("name", "Abdou Rakib Abente").split()
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else name_parts[-1]

    form_data = {
        "name": candidate_profile.get("name", "Abdou Rakib Abente"),
        "email": candidate_profile.get("email", "Rakibabente8@gmail.com"),
        "phone": candidate_profile.get("phone", "+12673445217"),
        "org": "",
        "urls[LinkedIn]": "https://linkedin.com/in/rakib-abente",
        "urls[GitHub]": "https://github.com/Abdrakib",
        "urls[Portfolio]": "https://abdourakib.com",
        "comments": cover_letter_text[:3000] if cover_letter_text else "",
        "silent": "false",
        "source": "LinkedIn",
    }

    # prepare resume file
    files = {}
    resume_file = Path(resume_path) if resume_path else None
    if resume_file and resume_file.exists():
        files["resume"] = (resume_file.name, open(resume_file, "rb"), "application/pdf")

    # submit
    api_url = f"https://api.lever.co/v0/postings/{company_slug}/{posting_id}/apply"
    try:
        if files:
            resp = requests.post(api_url, data=form_data, files=files, timeout=30)
            files["resume"][1].close()
        else:
            resp = requests.post(api_url, data=form_data, timeout=30)

        if resp.status_code in [200, 201]:
            print(f"  [Lever] ✅ Applied: {title} at {company}")
            return {
                "success": True,
                "company": company,
                "title": title,
                "platform": "lever",
                "apply_url": apply_url,
                "status_code": resp.status_code
            }
        elif resp.status_code == 404:
            print(f"  [Lever] ⚠️  404 — posting not found or closed")
            return {"success": False, "reason": "posting_not_found", "company": company, "title": title}
        elif resp.status_code == 400:
            print(f"  [Lever] ⚠️  400 Bad Request: {resp.text[:150]}")
            return {"success": False, "reason": "bad_request", "company": company, "title": title}
        else:
            print(f"  [Lever] ❌ Failed {resp.status_code}: {resp.text[:100]}")
            return {"success": False, "reason": f"http_{resp.status_code}", "company": company, "title": title}

    except Exception as e:
        if "resume" in files:
            try:
                files["resume"][1].close()
            except Exception:
                pass
        print(f"  [Lever] ❌ Exception: {e}")
        return {"success": False, "reason": str(e)[:100], "company": company, "title": title}
