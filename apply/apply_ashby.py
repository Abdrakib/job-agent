"""
apply/apply_ashby.py — Ashby auto-apply via Playwright browser automation

Ashby form URLs:
  https://jobs.ashbyhq.com/<company>/<job-id>/application
"""
import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MAX_PER_DAY = int(os.getenv("MAX_AUTO_APPLY_PER_DAY", "20"))
DEFAULT_TIMEOUT = 15_000

CANDIDATE = {
    "first_name": "Abdou Rakib",
    "last_name": "Abente",
    "email": os.getenv("CANDIDATE_EMAIL", "Rakibabente8@gmail.com"),
    "phone": os.getenv("CANDIDATE_PHONE", "+12673445217"),
    "linkedin": "https://linkedin.com/in/rakib-abente",
    "portfolio": "https://abdourakib.com",
    "github": "https://github.com/Abdrakib",
}


async def _fill_and_submit(apply_url: str, cover_letter: str, resume_path: str) -> dict:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

    if not apply_url.endswith("/application"):
        apply_url = apply_url.rstrip("/") + "/application"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            await page.goto(apply_url, wait_until="networkidle")

            await _fill_text(page, 'input[name="name.firstName"], input[placeholder*="First"]', CANDIDATE["first_name"])
            await _fill_text(page, 'input[name="name.lastName"], input[placeholder*="Last"]', CANDIDATE["last_name"])
            await _fill_text(page, 'input[name="email"], input[type="email"]', CANDIDATE["email"])
            await _fill_text(page, 'input[name="phone"], input[type="tel"]', CANDIDATE["phone"])

            resume_file = Path(resume_path) if resume_path else None
            if resume_file and resume_file.exists():
                resume_input = await _find_file_input(page, ["resume", "cv"])
                if resume_input:
                    await resume_input.set_input_files(str(resume_file))
                    logger.info("[Ashby] Resume uploaded")
                else:
                    logger.warning("[Ashby] No resume file input found — skipping")
            else:
                logger.warning(f"[Ashby] Resume not found at {resume_path}")

            await _fill_if_present(page, 'input[name*="linkedin" i], input[placeholder*="LinkedIn" i]', CANDIDATE["linkedin"])
            await _fill_if_present(page, 'input[name*="website" i], input[placeholder*="website" i], input[placeholder*="portfolio" i]', CANDIDATE["portfolio"])
            await _fill_if_present(page, 'input[name*="github" i], input[placeholder*="github" i]', CANDIDATE["github"])

            cl_textarea = page.locator('textarea[name*="cover" i], textarea[placeholder*="cover" i], textarea[aria-label*="cover" i]').first
            if await cl_textarea.count() > 0:
                await cl_textarea.fill(cover_letter)
                logger.info("[Ashby] Cover letter filled in textarea")
            else:
                cl_file_input = await _find_file_input(page, ["cover"])
                if cl_file_input:
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
                        tmp.write(cover_letter)
                        tmp_path = tmp.name
                    try:
                        await cl_file_input.set_input_files(tmp_path)
                        logger.info("[Ashby] Cover letter uploaded as file")
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
                else:
                    logger.info("[Ashby] No cover letter field found")

            await _handle_dynamic_questions(page)

            submit_btn = page.locator('button[type="submit"], button:has-text("Submit"), button:has-text("Apply")').last
            if await submit_btn.count() == 0:
                await browser.close()
                return {"submitted": False, "success": False, "error": "submit_button_not_found"}

            await submit_btn.scroll_into_view_if_needed()
            await submit_btn.click()

            try:
                await page.wait_for_selector(
                    "text=Thank you, text=Application submitted, text=received your application",
                    timeout=10_000
                )
                await browser.close()
                return {"submitted": True, "success": True}
            except PlaywrightTimeout:
                page_url = page.url.lower()
                if "confirmation" in page_url or "success" in page_url or "thank" in page_url:
                    await browser.close()
                    return {"submitted": True, "success": True}
                error_els = await page.locator(".error, [role='alert'], .field-error").all_text_contents()
                error_text = " | ".join(error_els) if error_els else "unknown error after submit"
                await browser.close()
                return {"submitted": True, "success": False, "error": error_text[:200]}

        except PlaywrightTimeout as e:
            await browser.close()
            return {"submitted": False, "success": False, "error": f"timeout: {e}"}
        except Exception as e:
            await browser.close()
            return {"submitted": False, "success": False, "error": str(e)[:200]}


async def _fill_text(page, selector: str, value: str):
    try:
        loc = page.locator(selector).first
        if await loc.count() > 0:
            await loc.fill(value)
    except Exception:
        pass


async def _fill_if_present(page, selector: str, value: str):
    await _fill_text(page, selector, value)


async def _find_file_input(page, keywords: list[str]):
    inputs = await page.locator('input[type="file"]').all()
    for inp in inputs:
        name = (await inp.get_attribute("name") or "").lower()
        id_ = (await inp.get_attribute("id") or "").lower()
        label = (await inp.get_attribute("aria-label") or "").lower()
        combined = f"{name} {id_} {label}"
        if any(kw in combined for kw in keywords):
            return inp
    if len(inputs) == 1:
        return inputs[0]
    return None


async def _handle_dynamic_questions(page):
    auth_selectors = [
        'select[name*="authorized" i]',
        'select[name*="work_auth" i]',
        'select[aria-label*="authorized" i]',
    ]
    for sel in auth_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.select_option(label=re.compile(r"yes", re.I))
        except Exception:
            pass

    sponsor_selectors = [
        'select[name*="sponsor" i]',
        'select[aria-label*="sponsor" i]',
    ]
    for sel in sponsor_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.select_option(label=re.compile(r"no", re.I))
        except Exception:
            pass

    try:
        hear_el = page.locator('select[name*="hear" i], select[aria-label*="hear" i]').first
        if await hear_el.count() > 0:
            options = await hear_el.locator("option").all()
            labels = [await o.text_content() for o in options]
            linkedin_opt = next((l for l in labels if "linkedin" in (l or "").lower()), None)
            if linkedin_opt:
                await hear_el.select_option(label=linkedin_opt)
            elif len(labels) > 1:
                await hear_el.select_option(index=1)
    except Exception:
        pass


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
    title = job.get("title", scored_job.get("job_title", ""))

    if applied_today_count >= MAX_PER_DAY:
        return {"success": False, "reason": "daily_limit_reached", "company": company, "title": title}

    from core.tracker import already_applied
    if already_applied(company, title):
        return {"success": False, "reason": "duplicate", "company": company, "title": title}

    if not apply_url:
        return {"success": False, "reason": "invalid_url", "company": company, "title": title}

    print(f"  [Ashby] 🌐 Applying via browser: {title} at {company}")

    try:
        result = asyncio.run(_fill_and_submit(apply_url, cover_letter_text, resume_path))
    except Exception as e:
        return {"success": False, "reason": str(e)[:100], "company": company, "title": title}

    if result.get("success"):
        print(f"  [Ashby] ✅ Applied: {title} at {company}")
        return {
            "success": True,
            "company": company,
            "title": title,
            "platform": "ashby",
            "apply_url": apply_url,
        }
    elif result.get("submitted"):
        print(f"  [Ashby] ✅ Submitted (unconfirmed): {title} at {company}")
        return {
            "success": True,
            "company": company,
            "title": title,
            "platform": "ashby",
            "apply_url": apply_url,
        }
    else:
        error = result.get("error", "unknown")
        print(f"  [Ashby] ❌ Failed: {title} at {company} — {error}")
        return {"success": False, "reason": error, "company": company, "title": title}
