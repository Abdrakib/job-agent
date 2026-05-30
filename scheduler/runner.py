"""
runner.py — Job Agent 24/7 Scheduler
Pipeline: Discover → Score → Cover Letters → Auto-Apply → Email Report
"""
import sys
import os
from pathlib import Path
from datetime import datetime, date
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

CANDIDATE_EMAIL = "Rakibabente8@gmail.com"
DASHBOARD_URL = os.getenv("APP_URL", "web-production-f1ea50.up.railway.app")
MAX_AUTO_APPLY_PER_DAY = int(os.getenv("MAX_AUTO_APPLY_PER_DAY", "20"))


def get_applied_today_count() -> int:
    """Count how many applications submitted today"""
    try:
        from core.tracker import get_connection, _use_postgres
        conn = get_connection()
        cur = conn.cursor()
        today = date.today().isoformat()
        if _use_postgres():
            cur.execute(
                """
                SELECT COUNT(*) as count FROM applications
                WHERE date_applied::text LIKE %s
                """,
                (f"{today}%",),
            )
        else:
            cur.execute(
                """
                SELECT COUNT(*) as count FROM applications
                WHERE date_applied LIKE ?
                """,
                (f"{today}%",),
            )
        count = cur.fetchone()["count"]
        cur.close()
        conn.close()
        return count
    except Exception:
        return 0


def send_daily_report(auto_applied: list, manual: list, stats: dict):
    """Send daily summary email via SendGrid"""
    try:
        import urllib.request
        import json as _json

        key = os.getenv("SENDGRID_API_KEY", "")
        if not key:
            print("  No SENDGRID_API_KEY — skipping email")
            return

        today = datetime.now().strftime("%B %d, %Y")
        total_applied = stats.get("total_applied", 0)
        subject = f"Job Agent — {today} | {len(auto_applied)} auto-applied | {total_applied} total to date"

        body = f"""JOB AGENT DAILY REPORT — {today}
{'='*55}

AUTO-APPLIED ({len(auto_applied)} jobs) — DONE, nothing needed
{'-'*40}
"""
        if auto_applied:
            for j in auto_applied:
                platform = j.get("apply_platform", "").upper()
                body += f"  ✅ {j.get('job_title','?')} at {j.get('company','?')} [{platform}] {j.get('match_score','?')}%\n"
        else:
            body += "  No auto-applied jobs today (check Greenhouse/Lever company lists)\n"

        body += f"""
MANUAL APPLY ({len(manual)} jobs) — Materials ready in dashboard
{'-'*40}
"""
        for j in manual[:15]:
            body += f"  📋 {j.get('job_title','?')} at {j.get('company','?')} — {j.get('match_score','?')}%\n"
            body += f"     {j.get('apply_url','')}\n"

        body += f"""
STATS TO DATE
{'-'*40}
  Total jobs found:    {stats.get('total_jobs_found', 0)}
  Total applied:       {total_applied}
  Interviews:          {stats.get('interviews', 0)}
  Offers:              {stats.get('offers', 0)}
  Rejections:          {stats.get('rejections', 0)}

DASHBOARD: https://{DASHBOARD_URL}
  → Documents tab: tailored resume + cover letter per job
  → Applications tab: full application history
"""
        payload = _json.dumps({
            "personalizations": [{"to": [{"email": CANDIDATE_EMAIL}]}],
            "from": {"email": CANDIDATE_EMAIL},
            "reply_to": {"email": CANDIDATE_EMAIL},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 202:
                print(f"  ✅ Daily report sent to {CANDIDATE_EMAIL}")
            else:
                print(f"  ❌ Email failed: {resp.status}")

    except Exception as e:
        print(f"  ❌ Email failed: {e}")


def run_job_discovery():
    """
    Full pipeline:
    1. Discover: Greenhouse direct + Lever direct + JSearch
    2. Score with Claude (70%+ threshold)
    3. Generate tailored cover letter + resume per job
    4. Auto-apply: Greenhouse API → Lever API
    5. Send daily email report
    Daily limit: MAX_AUTO_APPLY_PER_DAY applications
    """
    print(f"\n{'='*60}")
    print(f"JOB AGENT PIPELINE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Daily limit: {MAX_AUTO_APPLY_PER_DAY} auto-applications")
    print(f"{'='*60}")

    auto_applied = []
    manual = []

    try:
        from core.job_finder import find_all_jobs
        from core.resume_parser import get_candidate_profile
        from core.job_scorer import score_all_jobs
        from core.cover_letter import generate_and_save_cover_letter
        from core.tracker import (
            get_setting, save_job, already_applied,
            init_database, save_application, get_stats
        )
        from apply.greenhouse import apply_greenhouse
        from apply.lever import apply_lever

        init_database()

        max_jobs = int(get_setting("max_jobs_per_run") or 100)
        min_score = int(get_setting("min_match_score") or 70)
        work_location = get_setting("work_location") or "remote"
        applied_today = get_applied_today_count()

        print(f"Settings: max={max_jobs}, min_score={min_score}%, location={work_location}")
        print(f"Already applied today: {applied_today}/{MAX_AUTO_APPLY_PER_DAY}")

        # STEP 1: load profile
        print("\n[1/5] Loading candidate profile...")
        profile = get_candidate_profile()
        print(f"  ✅ {profile.get('name')}")

        # STEP 2: discover jobs
        print("\n[2/5] Discovering jobs...")
        jobs = find_all_jobs(max_jobs=max_jobs, work_location=work_location)
        gh_count = len([j for j in jobs if j.get("apply_platform") == "greenhouse"])
        lv_count = len([j for j in jobs if j.get("apply_platform") == "lever"])
        print(f"  ✅ {len(jobs)} jobs | Greenhouse: {gh_count} | Lever: {lv_count}")

        # STEP 3: score with Claude
        print("\n[3/5] Scoring jobs with Claude...")
        scored_jobs = score_all_jobs(jobs, profile, min_score=min_score)
        gh_scored = len([j for j in scored_jobs if j.get("apply_platform") == "greenhouse"])
        lv_scored = len([j for j in scored_jobs if j.get("apply_platform") == "lever"])
        print(f"  ✅ {len(scored_jobs)} qualified | Greenhouse: {gh_scored} | Lever: {lv_scored}")

        if not scored_jobs:
            print("  No qualified jobs — stopping")
            return

        # STEP 4: save to DB + generate cover letters
        print("\n[4/5] Saving + generating cover letters...")
        jobs_by_id = {job.get("id", ""): job for job in jobs}
        for scored in scored_jobs:
            original = jobs_by_id.get(scored.get("job_id", ""), scored)
            save_job(original, scored)

        # generate cover letters for top 20
        top20 = sorted(scored_jobs, key=lambda x: x.get("match_score", 0), reverse=True)[:20]
        generated = 0
        for job in top20:
            if not already_applied(job.get("company", ""), job.get("job_title", "")):
                try:
                    generate_and_save_cover_letter(job, profile)
                    generated += 1
                except Exception as e:
                    print(f"  Cover letter error ({job.get('company')}): {e}")
        print(f"  ✅ {generated} cover letters + resumes generated")

        # STEP 5: auto-apply pipeline
        print(f"\n[5/5] Auto-apply pipeline (limit: {MAX_AUTO_APPLY_PER_DAY}/day)...")

        # sort: Greenhouse first, then Lever, then others
        sorted_jobs = sorted(scored_jobs, key=lambda x: (
            0 if x.get("apply_platform") == "greenhouse" else
            1 if x.get("apply_platform") == "lever" else 2
        ))

        for job in sorted_jobs:
            # check daily limit
            applied_today = get_applied_today_count()
            if applied_today >= MAX_AUTO_APPLY_PER_DAY:
                print(f"\n  🛑 Daily limit reached ({MAX_AUTO_APPLY_PER_DAY}) — stopping auto-apply")
                # remaining jobs go to manual
                remaining = [j for j in sorted_jobs if j not in auto_applied]
                manual.extend(remaining)
                break

            company = job.get("company", "")
            title = job.get("job_title", "")
            platform = job.get("apply_platform", "direct")
            apply_url = job.get("apply_url", "")
            cover_letter = job.get("cover_letter_text", "")

            if already_applied(company, title):
                continue

            # find resume path
            resume_path = "data/base_resume.pdf"
            if job.get("resume_path") and Path(job["resume_path"]).exists():
                resume_path = job["resume_path"]

            if platform == "greenhouse":
                result = apply_greenhouse(
                    job=job, scored_job=job,
                    candidate_profile=profile,
                    cover_letter_text=cover_letter,
                    resume_path=resume_path,
                    applied_today_count=applied_today
                )
                if result.get("success"):
                    auto_applied.append(job)
                    save_application(
                        job_id=job.get("job_id", ""),
                        company=company, title=title,
                        platform="greenhouse", apply_url=apply_url
                    )
                else:
                    manual.append(job)

            elif platform == "lever":
                result = apply_lever(
                    job=job, scored_job=job,
                    candidate_profile=profile,
                    cover_letter_text=cover_letter,
                    resume_path=resume_path,
                    applied_today_count=applied_today
                )
                if result.get("success"):
                    auto_applied.append(job)
                    save_application(
                        job_id=job.get("job_id", ""),
                        company=company, title=title,
                        platform="lever", apply_url=apply_url
                    )
                else:
                    manual.append(job)

            else:
                manual.append(job)

        # final summary
        stats = get_stats()
        print(f"\n{'='*60}")
        print(f"✅ PIPELINE COMPLETE")
        print(f"   Auto-applied this run:  {len(auto_applied)}")
        print(f"   Manual (in dashboard):  {len(manual)}")
        print(f"   Total applied to date:  {stats.get('total_applied', 0)}")
        print(f"   Interviews:             {stats.get('interviews', 0)}")
        print(f"{'='*60}")

        send_daily_report(auto_applied, manual, stats)

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


def run_inbox_monitor():
    """Check Gmail for replies"""
    print(f"\n[Inbox] {datetime.now().strftime('%H:%M')}")
    try:
        from gmail.notifier import process_inbox
        r = process_inbox()
        print(f"  Processed: {r['processed']} | Interviews: {r['interview_requests']}")
    except Exception as e:
        print(f"  Inbox failed: {e}")


def run_github_sync():
    """Sync GitHub repos"""
    print(f"\n[GitHub Sync] {datetime.now().strftime('%H:%M')}")
    try:
        from sync import sync_github_projects
        synced = sync_github_projects()
        print(f"  Synced {len(synced)} repos")
    except Exception as e:
        print(f"  Sync failed: {e}")


def run_all():
    run_github_sync()
    run_job_discovery()
    run_inbox_monitor()


def start_scheduler():
    scheduler = BlockingScheduler(timezone="America/New_York")
    scheduler.add_job(run_all, CronTrigger(hour=8, minute=0), id="daily")
    scheduler.add_job(run_inbox_monitor, CronTrigger(hour="*/2", minute=30), id="inbox")
    scheduler.add_job(run_github_sync, CronTrigger(hour=0, minute=0), id="sync")

    print("🤖 Job Agent Scheduler Running")
    print(f"  Daily limit: {MAX_AUTO_APPLY_PER_DAY} auto-applications/day")
    print("  8:00 AM — Full pipeline")
    print("  Every 2h — Inbox monitor")
    print("  Midnight — GitHub sync\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--inbox", action="store_true")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--schedule", action="store_true")
    args = parser.parse_args()

    if args.run_now:
        run_all()
    elif args.discover:
        run_job_discovery()
    elif args.inbox:
        run_inbox_monitor()
    elif args.sync:
        run_github_sync()
    elif args.schedule:
        start_scheduler()
    else:
        run_all()
