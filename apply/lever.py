"""
lever.py — Lever auto-apply via Playwright browser automation
Uses a real headless browser to fill and submit Lever job applications.
Lever's public API (v0) sometimes works — we try API first, fall back to browser.
"""
import os
import re
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MAX_PER_DAY = int(os.getenv("MAX_AUTO_APPLY_PER_DAY", "20"))

CANDIDATE = {
    "name": "Abdou Rakib Abente",
    "email": os.getenv("CANDIDATE_EMAIL", "Rakibabente8@gmail.com"),
    "phone": os.getenv("CANDIDATE_PHONE", "+12673445217"),
    "linkedin": "https://linkedin.com/in/rakib-abente",
    "github": "https://github.com/Abdrakib",
    "portfolio": "https://abdourakib.com",
    "university": "Community College of Philadelphia",
    "degree": "Associate's Degree",
    "major": "Computer Science",
    "graduation": "May 2026",
    "salary": "70000",
}


def extract_lever_info(apply_url: str) -> tuple:
    patterns = [
        r"jobs\.lever\.co/([^/]+)/([a-f0-9-]+)",
        r"lever\.co/([^/]+)/([a-f0-9-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, apply_url)
        if match:
            return match.group(1), match.group(2)
    return None, None


def _answer(label: str, cover_letter: str = "") -> str:
    l = label.lower()
    if "linkedin" in l: return CANDIDATE["linkedin"]
    if "github" in l: return CANDIDATE["github"]
    if "portfolio" in l or "website" in l: return CANDIDATE["portfolio"]
    if "cover letter" in l or "comment" in l: return cover_letter[:3000]
    if "salary" in l or "compensation" in l: return CANDIDATE["salary"]
    if "authorized" in l or "visa" in l: return "Yes"
    if "sponsorship" in l: return "No"
    if "degree" in l or "education" in l: return CANDIDATE["degree"]
    if "school" in l or "university" in l: return CANDIDATE["university"]
    if "major" in l or "field" in l: return CANDIDATE["major"]
    if "graduation" in l: return CANDIDATE["graduation"]
    if "years" in l and "experience" in l: return "1"
    if "city" in l: return "Philadelphia"
    if "state" in l: return "Pennsylvania"
    if "country" in l: return "United States"
    if "start" in l or "available" in l: return "Immediately"
    if "hear" in l or "source" in l or "referred" in l: return "LinkedIn"
    if "remote" in l or "hybrid" in l: return "Yes"
    return ""


def _try_lever_api(company_slug: str, posting_id: str, cover_letter: str, resume_path: str) -> dict:
    """Try Lever's public v0 API first — works for many companies"""
    form_data = {
        "name": CANDIDATE["name"],
        "email": CANDIDATE["email"],
        "phone": CANDIDATE["phone"],
        "org": "",
        "urls[LinkedIn]": CANDIDATE["linkedin"],
        "urls[GitHub]": CANDIDATE["github"],
        "urls[Portfolio]": CANDIDATE["portfolio"],
        "comments": cover_letter[:3000] if cover_letter else "",
        "silent": "false",
        "source": "LinkedIn",
    }

    files = {}
    resume_file = Path(resume_path) if resume_path else None
    if resume_file and resume_file.exists():
        files["resume"] = (resume_file.name, open(resume_file, "rb"), "application/pdf")

    api_url = f"https://api.lever.co/v0/postings/{company_slug}/{posting_id}/apply"
    try:
        if files:
            resp = requests.post(api_url, data=form_data, files=files, timeout=30)
            files["resume"][1].close()
        else:
            resp = requests.post(api_url, data=form_data, timeout=30)

        if resp.status_code in [200, 201]:
            return {"success": True, "method": "api"}
        else:
            return {"success": False, "status": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _fill_and_submit_browser(apply_url: str, cover_letter: str, resume_path: str) -> dict:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = await browser.new_page()

        try:
            await page.goto(apply_url, timeout=30000, wait_until="networkidle")

            # Click apply button if on landing page
            for btn_text in ["Apply for this job", "Apply Now", "Apply", "Easy Apply"]:
                try:
                    btn = page.get_by_role("link", name=btn_text).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_load_state("networkidle")
                        break
                except Exception:
                    pass

            # Fill name
            for name_sel in ["input[name='name']", "input[placeholder*='name' i]", "input[id*='name' i]"]:
                try:
                    el = await page.query_selector(name_sel)
                    if el and await el.is_visible():
                        await el.fill(CANDIDATE["name"])
                        break
                except Exception:
                    pass

            # Fill email
            for sel in ["input[type='email']", "input[name='email']"]:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.fill(CANDIDATE["email"])
                        break
                except Exception:
                    pass

            # Fill phone
            for sel in ["input[type='tel']", "input[name='phone']"]:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.fill(CANDIDATE["phone"])
                        break
                except Exception:
                    pass

            # Fill all other text inputs by label
            inputs = await page.query_selector_all("input[type='text'], textarea")
            for inp in inputs:
                label_text = ""
                try:
                    inp_id = await inp.get_attribute("id")
                    if inp_id:
                        label_el = await page.query_selector(f"label[for='{inp_id}']")
                        if label_el:
                            label_text = (await label_el.inner_text()).strip()
                    if not label_text:
                        label_text = await inp.get_attribute("placeholder") or await inp.get_attribute("name") or ""
                except Exception:
                    pass

                answer = _answer(label_text, cover_letter)
                if answer:
                    try:
                        await inp.fill(answer)
                    except Exception:
                        pass

            # Upload resume
            if resume_path and Path(resume_path).exists():
                file_inputs = await page.query_selector_all("input[type='file']")
                for fi in file_inputs:
                    try:
                        await fi.set_input_files(resume_path)
                        break
                    except Exception:
                        pass

            # Submit
            submitted = False
            for submit_text in ["Submit Application", "Submit", "Apply", "Send"]:
                try:
                    btn = page.get_by_role("button", name=submit_text).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        submitted = True
                        break
                except Exception:
                    pass

            if not submitted:
                try:
                    btn = await page.query_selector("button[type='submit']")
                    if btn:
                        await btn.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        submitted = True
                except Exception:
                    pass

            page_text = (await page.inner_text("body")).lower()
            success = any(s in page_text for s in ["thank you", "application submitted", "we received", "successfully"])

            await browser.close()
            return {"submitted": submitted, "success": success}

        except PWTimeout:
            await browser.close()
            return {"submitted": False, "success": False, "error": "timeout"}
        except Exception as e:
            await browser.close()
            return {"submitted": False, "success": False, "error": str(e)[:200]}


def apply_lever(
    job: dict,
    scored_job: dict,
    candidate_profile: dict,
    cover_letter_text: str,
    resume_path: str,
    applied_today_count: int = 0
) -> dict:
    apply_url = job.get("apply_url", "")
    company = job.get("company", scored_job.get("company", ""))
    title = job.get("title", scored_job.get("job_title", ""))

    if applied_today_count >= MAX_PER_DAY:
        return {"success": False, "reason": "daily_limit_reached", "company": company, "title": title}

    from core.tracker import already_applied
    if already_applied(company, title):
        return {"success": False, "reason": "duplicate", "company": company, "title": title}

    company_slug, posting_id = extract_lever_info(apply_url)
    if not company_slug or not posting_id:
        print(f"  [Lever] Could not parse URL: {apply_url}")
        return {"success": False, "reason": "invalid_url", "company": company, "title": title}

    print(f"  [Lever] Applying: {title} at {company}")

    # Try API first (faster)
    api_result = _try_lever_api(company_slug, posting_id, cover_letter_text, resume_path)
    if api_result.get("success"):
        print(f"  [Lever] ✅ Applied via API: {title} at {company}")
        return {
            "success": True,
            "company": company,
            "title": title,
            "platform": "lever",
            "apply_url": apply_url,
        }

    # Fall back to browser
    print(f"  [Lever] API failed ({api_result.get('status', '?')}), trying browser...")
    try:
        result = asyncio.run(_fill_and_submit_browser(apply_url, cover_letter_text, resume_path))
    except Exception as e:
        return {"success": False, "reason": str(e)[:100], "company": company, "title": title}

    if result.get("success") or result.get("submitted"):
        print(f"  [Lever] ✅ Applied via browser: {title} at {company}")
        return {
            "success": True,
            "company": company,
            "title": title,
            "platform": "lever",
            "apply_url": apply_url,
        }
    else:
        error = result.get("error", "unknown")
        print(f"  [Lever] ❌ Failed: {title} at {company} — {error}")
        return {"success": False, "reason": error, "company": company, "title": title}
