"""
apply_ashby.py — Ashby auto-apply via Playwright browser automation
Uses a real headless browser to fill and submit Ashby job applications.
Ashby form URLs follow: https://jobs.ashbyhq.com/<company>/<job-id>/application
"""
import os
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MAX_PER_DAY = int(os.getenv("MAX_AUTO_APPLY_PER_DAY", "20"))
BROWSER_TIMEOUT = 45000   # 45 seconds max per page action
APPLY_TIMEOUT   = 90      # 90 seconds hard limit per application

CANDIDATE = {
    "first_name": "Abdou Rakib",
    "last_name": "Abente",
    "name": "Abdou Rakib Abente",
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


def _answer(label: str, cover_letter: str = "") -> str:
    l = label.lower()
    if "first name" in l: return CANDIDATE["first_name"]
    if "last name" in l: return CANDIDATE["last_name"]
    if "full name" in l or (("name" in l) and "last" not in l and "first" not in l): return CANDIDATE["name"]
    if "email" in l: return CANDIDATE["email"]
    if "phone" in l: return CANDIDATE["phone"]
    if "linkedin" in l: return CANDIDATE["linkedin"]
    if "github" in l: return CANDIDATE["github"]
    if "portfolio" in l or "website" in l or "personal site" in l: return CANDIDATE["portfolio"]
    if "cover letter" in l or "additional info" in l or "anything else" in l: return cover_letter[:3000]
    if "salary" in l or "compensation" in l: return CANDIDATE["salary"]
    if "authorized" in l or "visa" in l: return "Yes"
    if "sponsorship" in l or "sponsor" in l: return "No"
    if "degree" in l or "education" in l: return CANDIDATE["degree"]
    if "school" in l or "university" in l or "college" in l: return CANDIDATE["university"]
    if "major" in l or "field of study" in l: return CANDIDATE["major"]
    if "graduation" in l: return CANDIDATE["graduation"]
    if "years" in l and "experience" in l: return "1"
    if "city" in l: return "Philadelphia"
    if "state" in l: return "Pennsylvania"
    if "country" in l: return "United States"
    if "zip" in l or "postal" in l: return "19111"
    if "start" in l or "available" in l: return "Immediately"
    if "hear" in l or "source" in l or "referred" in l: return "LinkedIn"
    if "race" in l or "ethnicity" in l: return "Decline to self-identify"
    if "gender" in l: return "Decline to self-identify"
    if "veteran" in l or "military" in l: return "I am not a protected veteran"
    if "disability" in l: return "I don't wish to answer"
    if "remote" in l or "hybrid" in l: return "Yes"
    return ""


async def _fill_and_submit(apply_url: str, cover_letter: str, resume_path: str) -> dict:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    # Normalize URL
    if "/application" not in apply_url:
        apply_url = apply_url.rstrip("/") + "/application"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--use-gl=swiftshader",
                "--disable-setuid-sandbox",
            ]
        )
        page = await browser.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        try:
            await page.goto(apply_url, timeout=30000, wait_until="domcontentloaded")

            # Fill text inputs
            inputs = await page.query_selector_all("input[type='text'], input[type='email'], input[type='tel'], textarea")
            for inp in inputs:
                label_text = ""
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
                    try:
                        await inp.fill(answer)
                    except Exception:
                        pass

            # Upload resume
            if resume_path and Path(resume_path).exists():
                file_inputs = await page.query_selector_all("input[type='file']")
                for fi in file_inputs:
                    try:
                        fi_name = (await fi.get_attribute("name") or "").lower()
                        fi_id = (await fi.get_attribute("id") or "").lower()
                        if "cover" not in fi_name and "cover" not in fi_id:
                            await fi.set_input_files(resume_path)
                            break
                    except Exception:
                        pass

            # Handle dropdowns
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

            # Submit
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
                try:
                    btn = await page.query_selector("button[type='submit']")
                    if btn:
                        await btn.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        submitted = True
                except Exception:
                    pass

            page_text = (await page.inner_text("body")).lower()
            success_signals = ["application submitted", "thank you", "we received", "successfully applied", "application received"]
            closed_signals = ["no longer open", "position has been filled", "not accepting", "job has been closed", "no longer available"]
            success = any(s in page_text for s in success_signals)

            if not success and any(s in page_text for s in closed_signals):
                await browser.close()
                return {"submitted": False, "success": False, "error": "job_closed"}

            await browser.close()
            return {"submitted": submitted, "success": success}

        except PWTimeout:
            await browser.close()
            return {"submitted": False, "success": False, "error": "timeout"}
        except Exception as e:
            try:
                await browser.close()
            except Exception:
                pass
            return {"submitted": False, "success": False, "error": str(e)[:200]}


def apply_ashby(
    job: dict,
    scored_job: dict,
    candidate_profile: dict,
    cover_letter_text: str,
    resume_path: str,
    applied_today_count: int = 0
) -> dict:
    apply_url = job.get("apply_url", "")
    company = job.get("company", scored_job.get("company", ""))
    title = job.get("title") or job.get("job_title") or scored_job.get("job_title", "")

    if applied_today_count >= MAX_PER_DAY:
        return {"success": False, "reason": "daily_limit_reached", "company": company, "title": title}

    from core.tracker import already_applied
    if already_applied(company, title):
        return {"success": False, "reason": "duplicate", "company": company, "title": title}

    if not apply_url:
        return {"success": False, "reason": "invalid_url", "company": company, "title": title}

    print(f"  [Ashby] 🌐 Applying via browser: {title} at {company}")

    try:
        result = asyncio.run(
            asyncio.wait_for(_fill_and_submit(apply_url, cover_letter_text, resume_path), timeout=APPLY_TIMEOUT)
        )
    except asyncio.TimeoutError:
        print(f"  [Ashby] ⏱️  Hard timeout ({APPLY_TIMEOUT}s): {title} at {company} — skipping")
        return {"success": False, "reason": "hard_timeout", "company": company, "title": title}
    except Exception as e:
        return {"success": False, "reason": str(e)[:100], "company": company, "title": title}

    # Pause between applications to avoid overloading server
    time.sleep(5)

    if result.get("success"):
        print(f"  [Ashby] ✅ Applied: {title} at {company}")
        return {"success": True, "company": company, "title": title, "platform": "ashby", "apply_url": apply_url}
    elif result.get("submitted"):
        print(f"  [Ashby] ✅ Submitted (unconfirmed): {title} at {company}")
        return {"success": True, "company": company, "title": title, "platform": "ashby", "apply_url": apply_url}
    else:
        error = result.get("error", "unknown")
        if error != "job_closed":
            print(f"  [Ashby] ❌ Failed: {title} at {company} — {error}")
        return {"success": False, "reason": error, "company": company, "title": title}
