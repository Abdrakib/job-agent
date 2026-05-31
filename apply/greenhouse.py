"""
greenhouse.py — Greenhouse auto-apply via Playwright browser automation
Uses a real headless browser to fill and submit Greenhouse job applications.
"""
import os
import re
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MAX_PER_DAY = int(os.getenv("MAX_AUTO_APPLY_PER_DAY", "20"))

CANDIDATE = {
    "first_name": "Abdou Rakib",
    "last_name": "Abente",
    "email": os.getenv("CANDIDATE_EMAIL", "Rakibabente8@gmail.com"),
    "phone": os.getenv("CANDIDATE_PHONE", "+12673445217"),
    "linkedin": "https://linkedin.com/in/rakib-abente",
    "github": "https://github.com/Abdrakib",
    "portfolio": "https://abdourakib.com",
    "location": "Philadelphia, PA",
    "university": "Community College of Philadelphia",
    "degree": "Associate's Degree",
    "major": "Computer Science",
    "graduation": "May 2026",
    "salary": "70000",
}


def extract_greenhouse_board(apply_url: str) -> tuple:
    patterns = [
        r"greenhouse\.io/([^/]+)/jobs/(\d+)",
        r"boards\.greenhouse\.io/([^/]+)/jobs/(\d+)",
        r"job-boards\.greenhouse\.io/([^/]+)/jobs/(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, apply_url)
        if match:
            return match.group(1), match.group(2)
    return None, None


def _answer(label: str, cover_letter: str = "") -> str:
    l = label.lower()
    if "first name" in l: return CANDIDATE["first_name"]
    if "last name" in l: return CANDIDATE["last_name"]
    if "email" in l: return CANDIDATE["email"]
    if "phone" in l: return CANDIDATE["phone"]
    if "linkedin" in l: return CANDIDATE["linkedin"]
    if "github" in l: return CANDIDATE["github"]
    if "portfolio" in l or "website" in l: return CANDIDATE["portfolio"]
    if "cover letter" in l: return cover_letter[:3000]
    if "salary" in l or "compensation" in l: return CANDIDATE["salary"]
    if "authorized" in l or "visa" in l: return "Yes"
    if "sponsorship" in l or "sponsor" in l: return "No"
    if "degree" in l or "education" in l: return CANDIDATE["degree"]
    if "school" in l or "university" in l: return CANDIDATE["university"]
    if "major" in l or "field of study" in l: return CANDIDATE["major"]
    if "graduation" in l: return CANDIDATE["graduation"]
    if "years" in l and "experience" in l: return "1"
    if "city" in l: return "Philadelphia"
    if "state" in l: return "Pennsylvania"
    if "country" in l: return "United States"
    if "zip" in l or "postal" in l: return "19111"
    if "start" in l or "available" in l: return "Immediately"
    if "hear" in l or "source" in l: return "LinkedIn"
    if "race" in l or "ethnicity" in l: return "Decline to self-identify"
    if "gender" in l: return "Decline to self-identify"
    if "veteran" in l or "military" in l: return "I am not a protected veteran"
    if "disability" in l: return "I don't wish to answer"
    if "remote" in l or "hybrid" in l: return "Yes"
    return ""


async def _fill_and_submit(apply_url: str, cover_letter: str, resume_path: str) -> dict:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = await browser.new_page()

        try:
            await page.goto(apply_url, timeout=30000, wait_until="networkidle")

            # Click "Apply" button if present (some pages have a landing page first)
            for btn_text in ["Apply for this job", "Apply Now", "Apply", "Submit Application"]:
                try:
                    btn = page.get_by_role("link", name=btn_text).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_load_state("networkidle")
                        break
                except Exception:
                    pass

            # Fill all visible text inputs
            inputs = await page.query_selector_all("input[type='text'], input[type='email'], input[type='tel'], textarea")
            for inp in inputs:
                label_text = ""
                # try to find associated label
                try:
                    inp_id = await inp.get_attribute("id")
                    if inp_id:
                        label_el = await page.query_selector(f"label[for='{inp_id}']")
                        if label_el:
                            label_text = (await label_el.inner_text()).strip()
                except Exception:
                    pass

                if not label_text:
                    try:
                        label_text = await inp.get_attribute("placeholder") or ""
                        aria = await inp.get_attribute("aria-label") or ""
                        name_attr = await inp.get_attribute("name") or ""
                        label_text = label_text or aria or name_attr
                    except Exception:
                        pass

                answer = _answer(label_text, cover_letter)
                if answer:
                    await inp.fill(answer)

            # Upload resume
            if resume_path and Path(resume_path).exists():
                file_inputs = await page.query_selector_all("input[type='file']")
                for fi in file_inputs:
                    try:
                        await fi.set_input_files(resume_path)
                        break
                    except Exception:
                        pass

            # Handle dropdowns (select elements)
            selects = await page.query_selector_all("select")
            for sel in selects:
                try:
                    sel_id = await sel.get_attribute("id") or ""
                    label_el = await page.query_selector(f"label[for='{sel_id}']")
                    label_text = (await label_el.inner_text()).strip() if label_el else sel_id

                    options = await sel.query_selector_all("option")
                    answer = _answer(label_text, cover_letter).lower()

                    for opt in options:
                        opt_text = (await opt.inner_text()).lower()
                        opt_val = (await opt.get_attribute("value") or "").lower()
                        if answer and (answer in opt_text or answer in opt_val):
                            await sel.select_option(value=await opt.get_attribute("value"))
                            break
                except Exception:
                    pass

            # Submit the form
            submitted = False
            for submit_text in ["Submit Application", "Submit", "Apply", "Send Application"]:
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
                # fallback: find any submit button
                try:
                    btn = await page.query_selector("button[type='submit']")
                    if btn:
                        await btn.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        submitted = True
                except Exception:
                    pass

            # Check for success indicators
            page_text = (await page.inner_text("body")).lower()
            success_signals = ["application submitted", "thank you", "we received", "successfully applied", "application received"]
            success = any(s in page_text for s in success_signals)

            await browser.close()
            return {"submitted": submitted, "success": success, "page_text": page_text[:300]}

        except PWTimeout:
            await browser.close()
            return {"submitted": False, "success": False, "error": "timeout"}
        except Exception as e:
            await browser.close()
            return {"submitted": False, "success": False, "error": str(e)[:200]}


def apply_greenhouse(
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

    board_token, job_id = extract_greenhouse_board(apply_url)
    if not board_token or not job_id:
        print(f"  [Greenhouse] Could not parse URL: {apply_url}")
        return {"success": False, "reason": "invalid_url", "company": company, "title": title}

    print(f"  [Greenhouse] 🌐 Applying via browser: {title} at {company}")

    try:
        result = asyncio.run(_fill_and_submit(apply_url, cover_letter_text, resume_path))
    except Exception as e:
        return {"success": False, "reason": str(e)[:100], "company": company, "title": title}

    if result.get("success"):
        print(f"  [Greenhouse] ✅ Applied: {title} at {company}")
        return {
            "success": True,
            "company": company,
            "title": title,
            "platform": "greenhouse",
            "apply_url": apply_url,
        }
    elif result.get("submitted"):
        # submitted but couldn't confirm — treat as success
        print(f"  [Greenhouse] ✅ Submitted (unconfirmed): {title} at {company}")
        return {
            "success": True,
            "company": company,
            "title": title,
            "platform": "greenhouse",
            "apply_url": apply_url,
        }
    else:
        error = result.get("error", "unknown")
        print(f"  [Greenhouse] ❌ Failed: {title} at {company} — {error}")
        return {"success": False, "reason": error, "company": company, "title": title}
