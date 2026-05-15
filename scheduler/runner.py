import sys
import os
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

# add parent to path
sys.path.append(str(Path(__file__).parent.parent))


def run_job_discovery():
    """Find new jobs, score them, generate cover letters, save to DB"""
    print(f"\n{'='*50}")
    print(f"JOB DISCOVERY RUN — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    try:
        from core.job_finder import find_all_jobs
        from core.resume_parser import get_candidate_profile
        from core.job_scorer import score_all_jobs
        from core.cover_letter import generate_and_save_cover_letter
        from core.resume_builder import build_resume_pdf
        from core.tracker import (
            get_setting, save_job, already_applied,
            init_database
        )

        init_database()

        max_jobs = int(get_setting("max_jobs_per_run") or 50)
        min_score = int(get_setting("min_match_score") or 70)
        work_location = get_setting("work_location") or "remote"

        print(f"Settings: max_jobs={max_jobs}, min_score={min_score}, work_location={work_location}")

        # step 1 — load candidate profile
        print("\n[1/5] Loading candidate profile...")
        profile = get_candidate_profile()
        print(f"  Profile loaded for: {profile.get('name')}")

        # step 2 — find jobs
        print("\n[2/5] Discovering jobs...")
        jobs = find_all_jobs(max_jobs=max_jobs, work_location=work_location)
        print(f"  Found {len(jobs)} jobs")

        # step 3 — score jobs
        print("\n[3/5] Scoring jobs with Claude...")
        scored_jobs = score_all_jobs(jobs, profile, min_score=min_score)
        print(f"  {len(scored_jobs)} jobs above {min_score}% threshold")

        # step 4 — save to database
        print("\n[4/5] Saving to database...")
        new_jobs = 0
        for job in scored_jobs:
            save_job(job, job)
            new_jobs += 1
        print(f"  Saved {new_jobs} jobs")

        # step 5 — generate cover letters and resumes for top jobs
        print("\n[5/5] Generating cover letters for top matches...")
        top_jobs = sorted(
            scored_jobs,
            key=lambda x: (x.get("priority_flag", 0), x.get("match_score", 0)),
            reverse=True
        )[:10]

        generated = 0
        for job in top_jobs:
            try:
                if not already_applied(job.get("company", ""), job.get("job_title", "")):
                    generate_and_save_cover_letter(job, profile)
                    build_resume_pdf(job, profile)
                    generated += 1
            except Exception as e:
                print(f"  Error generating materials for {job.get('company')}: {e}")

        print(f"  Generated materials for {generated} jobs")

        print(f"\n✅ Discovery run complete — {len(scored_jobs)} jobs ready")

    except Exception as e:
        print(f"\n❌ Discovery run failed: {e}")
        import traceback
        traceback.print_exc()


def run_auto_apply():
    """Auto-apply to Greenhouse and Lever jobs"""
    print(f"\n{'='*50}")
    print(f"AUTO-APPLY RUN — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    try:
        from core.tracker import (
            get_jobs, get_setting, get_connection,
            already_applied
        )
        from core.resume_parser import get_candidate_profile
        from apply.greenhouse import apply_greenhouse
        from apply.lever import apply_lever

        auto_platforms = (get_setting("auto_apply_platforms") or "greenhouse,lever").split(",")
        print(f"Auto-apply platforms: {auto_platforms}")

        profile = get_candidate_profile()

        # get jobs ready to apply to
        jobs_to_apply = get_jobs(status="found", min_score=75, limit=20)
        print(f"Found {len(jobs_to_apply)} jobs to apply to")

        applied = 0
        skipped = 0

        for job in jobs_to_apply:
            platform = job.get("apply_platform", "")
            company = job.get("company", "")
            title = job.get("title", "")

            if already_applied(company, title):
                skipped += 1
                continue

            if platform not in auto_platforms:
                continue

            # find cover letter
            from pathlib import Path
            cover_letters_dir = Path("generated_resumes")
            company_slug = company.replace(" ", "_").replace("/", "_")
            title_slug = title.replace(" ", "_").replace("/", "_")[:25]

            cover_letter_path = cover_letters_dir / f"cover_letter_{company_slug}_{title_slug}.txt"
            cover_letter_text = ""
            if cover_letter_path.exists():
                with open(cover_letter_path, "r", encoding="utf-8") as f:
                    cover_letter_text = f.read()

            # find resume
            resume_path = f"generated_resumes/resume_{company_slug}_{title_slug}.pdf"
            if not Path(resume_path).exists():
                resume_path = "data/base_resume.pdf"

            # apply
            if platform == "greenhouse":
                result = apply_greenhouse(
                    job=job,
                    scored_job=job,
                    candidate_profile=profile,
                    cover_letter_text=cover_letter_text,
                    resume_path=resume_path
                )
            elif platform == "lever":
                result = apply_lever(
                    job=job,
                    scored_job=job,
                    candidate_profile=profile,
                    cover_letter_text=cover_letter_text,
                    resume_path=resume_path
                )
            else:
                continue

            if result.get("success"):
                applied += 1
            else:
                skipped += 1

        print(f"\n✅ Auto-apply complete — Applied: {applied}, Skipped: {skipped}")

    except Exception as e:
        print(f"\n❌ Auto-apply failed: {e}")
        import traceback
        traceback.print_exc()


def run_inbox_monitor():
    """Check Gmail inbox and send notifications"""
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
    """Sync GitHub repos to update project bank"""
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
    """Run the complete pipeline once"""
    print(f"\n🤖 JOB AGENT FULL RUN — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_github_sync()
    run_job_discovery()
    run_auto_apply()
    run_inbox_monitor()
    print(f"\n🏁 Full run complete — {datetime.now().strftime('%H:%M:%S')}")


def start_scheduler():
    """Start the 24/7 scheduler"""
    scheduler = BlockingScheduler(timezone="America/New_York")

    # daily full run at 8am
    scheduler.add_job(
        run_all,
        CronTrigger(hour=8, minute=0),
        id="daily_run",
        name="Daily Full Run"
    )

    # inbox check every 2 hours
    scheduler.add_job(
        run_inbox_monitor,
        CronTrigger(hour="*/2", minute=30),
        id="inbox_check",
        name="Inbox Monitor"
    )

    # github sync every day at midnight
    scheduler.add_job(
        run_github_sync,
        CronTrigger(hour=0, minute=0),
        id="github_sync",
        name="GitHub Sync"
    )

    print("🤖 Job Agent Scheduler Started")
    print("Schedule:")
    print("  • 8:00 AM daily — Full run (discover, score, apply)")
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
    parser.add_argument("--apply", action="store_true", help="Run auto-apply only")
    parser.add_argument("--inbox", action="store_true", help="Check inbox only")
    parser.add_argument("--sync", action="store_true", help="Sync GitHub only")
    parser.add_argument("--schedule", action="store_true", help="Start 24/7 scheduler")

    args = parser.parse_args()

    if args.run_now:
        run_all()
    elif args.discover:
        run_job_discovery()
    elif args.apply:
        run_auto_apply()
    elif args.inbox:
        run_inbox_monitor()
    elif args.sync:
        run_github_sync()
    elif args.schedule:
        start_scheduler()
    else:
        # default — run everything once
        run_all()
