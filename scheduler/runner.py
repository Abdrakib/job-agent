import sys
import os
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

CANDIDATE_EMAIL = "Rakibabente8@gmail.com"
DASHBOARD_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "web-production-f1ea50.up.railway.app")


def send_morning_report(auto_applied: list, hit_apply: list, manual: list):
    """Send daily summary email to Rakib"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        gmail_user = os.getenv("GMAIL_USER", CANDIDATE_EMAIL)
        gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")

        if not gmail_password:
            print("  No GMAIL_APP_PASSWORD set — skipping email report")
            return

        today = datetime.now().strftime("%B %d, %Y")
        subject = f"🤖 Job Agent Report — {today} | {len(auto_applied)} auto-applied, {len(hit_apply)+len(manual)} need you"

        body = f"""
🤖 JOB AGENT DAILY REPORT — {today}
{'='*50}

"""
        if auto_applied:
            body += f"✅ AUTO-APPLIED ({len(auto_applied)} jobs) — Nothing needed from you\n"
            body += "-" * 40 + "\n"
            for job in auto_applied:
                body += f"  • {job.get('job_title','?')} at {job.get('company','?')} — {job.get('match_score','?')}%\n"
            body += "\n"
        else:
            body += "✅ AUTO-APPLIED: 0 jobs (no Greenhouse/Lever jobs found today)\n\n"

        if hit_apply:
            body += f"👆 HIT APPLY ({len(hit_apply)} jobs) — Open link, everything pre-filled, just click Apply\n"
            body += "-" * 40 + "\n"
            for job in hit_apply:
                body += f"  • {job.get('job_title','?')} at {job.get('company','?')} — {job.get('match_score','?')}%\n"
                body += f"    Apply: {job.get('apply_url','')}\n"
            body += "\n"

        if manual:
            body += f"✍️  MANUAL APPLY ({len(manual)} jobs) — Resume + cover letter ready in dashboard\n"
            body += "-" * 40 + "\n"
            for job in manual:
                body += f"  • {job.get('job_title','?')} at {job.get('company','?')} — {job.get('match_score','?')}%\n"
                body += f"    Apply: {job.get('apply_url','')}\n"
            body += "\n"

        body += f"\n📊 Open your dashboard: https://{DASHBOARD_URL}\n"
        body += f"   → Documents tab has all resumes + cover letters ready to download\n"

        total = len(auto_applied) + len(hit_apply) + len(manual)
        body += f"\nTotal applications today: {total}\n"

        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = CANDIDATE_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)

        print(f"  ✅ Morning report sent to {CANDIDATE_EMAIL}")

    except Exception as e:
        print(f"  ❌ Email report failed: {e}")


def run_job_discovery():
    """Find new jobs, score them, generate cover letters, save to DB"""
    print(f"\n{'='*50}")
    print(f"JOB DISCOVERY RUN — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    auto_applied = []
    hit_apply = []
    manual = []

    try:
        from core.job_finder import find_all_jobs
        from core.resume_parser import get_candidate_profile
        from core.job_scorer import score_all_jobs
        from core.cover_letter import generate_and_save_cover_letter
        from core.tracker import get_setting, save_job, already_applied, init_database

        init_database()

        max_jobs = int(get_setting("max_jobs_per_run") or 50)
        min_score = int(get_setting("min_match_score") or 70)
        work_location = get_setting("work_location") or "remote"

        print(f"Settings: max_jobs={max_jobs}, min_score={min_score}, work_location={work_location}")

        print("\n[1/5] Loading candidate profile...")
        profile = get_candidate_profile()
        print(f"  Profile loaded for: {profile.get('name')}")

        print("\n[2/5] Discovering jobs...")
        jobs = find_all_jobs(max_jobs=max_jobs, work_location=work_location)
        print(f"  Found {len(jobs)} jobs")

        print("\n[3/5] Scoring jobs with Claude...")
        scored_jobs = score_all_jobs(jobs, profile, min_score=min_score)
        print(f"  {len(scored_jobs)} jobs above {min_score}% threshold")

        print("\n[4/5] Saving to database...")
        for job in scored_jobs:
            save_job(job, job)
        print(f"  Saved {len(scored_jobs)} jobs")

        print("\n[5/5] Generating cover letters and resumes...")
        top_jobs = sorted(
            scored_jobs,
            key=lambda x: (x.get("priority_flag", 0), x.get("match_score", 0)),
            reverse=True
        )[:15]

        for job in top_jobs:
            try:
                if not already_applied(job.get("company", ""), job.get("job_title", "")):
                    generate_and_save_cover_letter(job, profile)
            except Exception as e:
                print(f"  Error generating materials for {job.get('company')}: {e}")

        print("\n[6] Running auto-apply...")
        for job in scored_jobs:
            platform = job.get("apply_platform", "")
            company = job.get("company", "")
            title = job.get("job_title", "")

            if already_applied(company, title):
                continue

            if platform == "greenhouse":
                try:
                    from apply.greenhouse import apply_greenhouse
                    result = apply_greenhouse(
                        job=job, scored_job=job, candidate_profile=profile,
                        cover_letter_text=job.get("cover_letter_text", ""),
                        resume_path="data/base_resume.pdf"
                    )
                    if result.get("success"):
                        auto_applied.append(job)
                        print(f"  ✅ Auto-applied: {title} at {company}")
                except Exception as e:
                    print(f"  Greenhouse error: {e}")

            elif platform == "lever":
                try:
                    from apply.lever import apply_lever
                    result = apply_lever(
                        job=job, scored_job=job, candidate_profile=profile,
                        cover_letter_text=job.get("cover_letter_text", ""),
                        resume_path="data/base_resume.pdf"
                    )
                    if result.get("success"):
                        auto_applied.append(job)
                        print(f"  ✅ Auto-applied: {title} at {company}")
                except Exception as e:
                    print(f"  Lever error: {e}")

            elif platform == "linkedin":
                hit_apply.append(job)

            else:
                manual.append(job)

        print(f"\n  Auto-applied: {len(auto_applied)}")
        print(f"  Hit apply: {len(hit_apply)}")
        print(f"  Manual: {len(manual)}")

        print("\n[7] Sending morning report email...")
        send_morning_report(auto_applied, hit_apply[:10], manual[:10])

        print(f"\n✅ Discovery run complete")

    except Exception as e:
        print(f"\n❌ Discovery run failed: {e}")
        import traceback
        traceback.print_exc()


def run_inbox_monitor():
    print(f"\n{'='*50}")
    print(f"INBOX MONITOR — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    try:
        from gmail.notifier import process_inbox
        results = process_inbox()
        print(f"✅ Inbox processed — {results['processed']} emails, "
              f"{results['interview_requests']} interviews, "
              f"{results['notifications_sent']} notifications")
    except Exception as e:
        print(f"❌ Inbox monitor failed: {e}")


def run_github_sync():
    print(f"\n{'='*50}")
    print(f"GITHUB SYNC — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    try:
        from sync import sync_github_projects
        synced = sync_github_projects()
        print(f"✅ Synced {len(synced)} repos from GitHub")
    except Exception as e:
        print(f"❌ GitHub sync failed: {e}")


def run_all():
    print(f"\n🤖 JOB AGENT FULL RUN — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_github_sync()
    run_job_discovery()
    run_inbox_monitor()
    print(f"\n🏁 Full run complete — {datetime.now().strftime('%H:%M:%S')}")


def start_scheduler():
    scheduler = BlockingScheduler(timezone="America/New_York")

    scheduler.add_job(run_all, CronTrigger(hour=8, minute=0), id="daily_run", name="Daily Full Run")
    scheduler.add_job(run_inbox_monitor, CronTrigger(hour="*/2", minute=30), id="inbox_check", name="Inbox Monitor")
    scheduler.add_job(run_github_sync, CronTrigger(hour=0, minute=0), id="github_sync", name="GitHub Sync")

    print("🤖 Job Agent Scheduler Started")
    print("Schedule:")
    print("  • 8:00 AM daily — Full run (discover, score, cover letters, auto-apply, email report)")
    print("  • Every 2 hours — Check Gmail inbox")
    print("  • Midnight daily — Sync GitHub repos")
    print("\nPress Ctrl+C to stop\n")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\nScheduler stopped.")
        scheduler.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Job Agent Runner")
    parser.add_argument("--run-now", action="store_true", help="Run full pipeline immediately")
    parser.add_argument("--discover", action="store_true", help="Run job discovery only")
    parser.add_argument("--inbox", action="store_true", help="Check inbox only")
    parser.add_argument("--sync", action="store_true", help="Sync GitHub only")
    parser.add_argument("--schedule", action="store_true", help="Start 24/7 scheduler")

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
