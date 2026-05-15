import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "applications.db"


def get_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # returns dict-like rows
    return conn


def init_database():
    """Create all tables if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()

    # Jobs table — every job the agent finds
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            is_remote INTEGER DEFAULT 0,
            is_hybrid INTEGER DEFAULT 0,
            employment_type TEXT,
            apply_url TEXT,
            apply_platform TEXT,
            description TEXT,
            salary_min REAL,
            salary_max REAL,
            match_score INTEGER DEFAULT 0,
            recommendation TEXT,
            reasoning TEXT,
            best_projects TEXT,
            cover_letter_angle TEXT,
            missing_skills TEXT,
            strengths TEXT,
            priority_flag INTEGER DEFAULT 0,
            date_found TEXT,
            date_applied TEXT,
            status TEXT DEFAULT 'found',
            notes TEXT
        )
    """)

    # Applications table — every application submitted
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            apply_platform TEXT,
            apply_url TEXT,
            cover_letter_path TEXT,
            resume_path TEXT,
            date_applied TEXT NOT NULL,
            status TEXT DEFAULT 'applied',
            last_updated TEXT,
            follow_up_date TEXT,
            follow_up_sent INTEGER DEFAULT 0,
            response_date TEXT,
            response_type TEXT,
            notes TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    # Settings table — user preferences
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT
        )
    """)

    # Follow-ups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            job_id TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            scheduled_date TEXT NOT NULL,
            sent INTEGER DEFAULT 0,
            sent_date TEXT,
            response_received INTEGER DEFAULT 0,
            FOREIGN KEY (application_id) REFERENCES applications(id)
        )
    """)

    conn.commit()
    conn.close()

    # insert default settings if not exist
    save_default_settings()
    print("Database initialized successfully.")


def save_default_settings():
    """Save default user preferences"""
    defaults = {
        "work_location": "remote",           # remote, hybrid, onsite, any
        "job_types": "internship,fulltime",   # internship, fulltime
        "min_match_score": "70",
        "min_salary": "0",
        "show_no_salary": "true",
        "follow_up_days": "7",
        "max_jobs_per_run": "50",
        "auto_apply_platforms": "greenhouse,lever",
        "email_notifications": "true",
        "daily_run_time": "08:00"
    }

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    for key, value in defaults.items():
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, now))

    conn.commit()
    conn.close()


def get_setting(key: str) -> str:
    """Get a setting value"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else None


def save_setting(key: str, value: str):
    """Save or update a setting"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
    """, (key, value, now))
    conn.commit()
    conn.close()


def save_job(job: dict, scored_data: dict = None):
    """Save a discovered job to the database"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    best_projects = json.dumps(scored_data.get("best_projects", [])) if scored_data else "[]"
    missing_skills = json.dumps(scored_data.get("missing_skills", [])) if scored_data else "[]"
    strengths = json.dumps(scored_data.get("strengths", [])) if scored_data else "[]"

    cursor.execute("""
        INSERT OR REPLACE INTO jobs (
            id, title, company, location, is_remote, is_hybrid,
            employment_type, apply_url, apply_platform, description,
            salary_min, salary_max, match_score, recommendation,
            reasoning, best_projects, cover_letter_angle,
            missing_skills, strengths, priority_flag, date_found, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job.get("id", ""),
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        1 if job.get("is_remote") else 0,
        1 if "hybrid" in job.get("location", "").lower() else 0,
        job.get("employment_type", ""),
        job.get("apply_url", ""),
        job.get("apply_platform", ""),
        job.get("description", "")[:1000],
        job.get("salary_min"),
        job.get("salary_max"),
        scored_data.get("match_score", 0) if scored_data else 0,
        scored_data.get("recommendation", "") if scored_data else "",
        scored_data.get("reasoning", "") if scored_data else "",
        best_projects,
        scored_data.get("cover_letter_angle", "") if scored_data else "",
        missing_skills,
        strengths,
        1 if (scored_data and scored_data.get("priority_flag")) else 0,
        now,
        "found"
    ))

    conn.commit()
    conn.close()


def save_application(job_id: str, company: str, title: str,
                     platform: str, apply_url: str,
                     cover_letter_path: str = None,
                     resume_path: str = None) -> int:
    """Record a submitted application. Returns application ID."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    follow_up_days = int(get_setting("follow_up_days") or 7)
    follow_up_date = (datetime.now() + timedelta(days=follow_up_days)).isoformat()

    cursor.execute("""
        INSERT INTO applications (
            job_id, company, title, apply_platform, apply_url,
            cover_letter_path, resume_path, date_applied,
            status, last_updated, follow_up_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id, company, title, platform, apply_url,
        cover_letter_path, resume_path, now,
        "applied", now, follow_up_date
    ))

    app_id = cursor.lastrowid

    # update job status
    cursor.execute("""
        UPDATE jobs SET status = 'applied', date_applied = ?
        WHERE id = ?
    """, (now, job_id))

    # schedule follow-up
    cursor.execute("""
        INSERT INTO follow_ups (
            application_id, job_id, company, title, scheduled_date
        ) VALUES (?, ?, ?, ?, ?)
    """, (app_id, job_id, company, title, follow_up_date))

    conn.commit()
    conn.close()
    return app_id


def update_application_status(application_id: int, status: str,
                               response_type: str = None, notes: str = None):
    """Update application status (interview, rejected, offer, etc.)"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        UPDATE applications SET
            status = ?,
            last_updated = ?,
            response_date = ?,
            response_type = ?,
            notes = COALESCE(?, notes)
        WHERE id = ?
    """, (status, now, now, response_type, notes, application_id))

    conn.commit()
    conn.close()


def get_applications(status: str = None, limit: int = 100) -> list:
    """Get all applications, optionally filtered by status"""
    conn = get_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute("""
            SELECT * FROM applications
            WHERE status = ?
            ORDER BY date_applied DESC
            LIMIT ?
        """, (status, limit))
    else:
        cursor.execute("""
            SELECT * FROM applications
            ORDER BY date_applied DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_jobs(status: str = None, min_score: int = 0,
             work_location: str = "any", limit: int = 100) -> list:
    """Get jobs with optional filters"""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM jobs WHERE match_score >= ?"
    params = [min_score]

    if status:
        query += " AND status = ?"
        params.append(status)

    if work_location == "remote":
        query += " AND is_remote = 1"
    elif work_location == "hybrid":
        query += " AND (is_remote = 1 OR is_hybrid = 1)"

    query += " ORDER BY priority_flag DESC, match_score DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_pending_follow_ups() -> list:
    """Get applications that need follow-up today"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        SELECT f.*, a.apply_url, a.cover_letter_path
        FROM follow_ups f
        JOIN applications a ON f.application_id = a.id
        WHERE f.scheduled_date <= ?
        AND f.sent = 0
        AND a.status = 'applied'
        ORDER BY f.scheduled_date ASC
    """, (now,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats() -> dict:
    """Get dashboard statistics"""
    conn = get_connection()
    cursor = conn.cursor()

    stats = {}

    cursor.execute("SELECT COUNT(*) as count FROM jobs")
    stats["total_jobs_found"] = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM applications")
    stats["total_applied"] = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE status = 'interview'")
    stats["interviews"] = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE status = 'rejected'")
    stats["rejections"] = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE status = 'offer'")
    stats["offers"] = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) as count FROM follow_ups
        WHERE sent = 0 AND scheduled_date <= ?
    """, (datetime.now().isoformat(),))
    stats["pending_followups"] = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) as count FROM jobs
        WHERE priority_flag = 1 AND status = 'found'
    """)
    stats["priority_jobs"] = cursor.fetchone()["count"]

    conn.close()
    return stats


def already_applied(company: str, title: str) -> bool:
    """Check if we already applied to this job"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) as count FROM applications
        WHERE LOWER(company) = LOWER(?)
        AND LOWER(title) LIKE LOWER(?)
    """, (company, f"%{title[:20]}%"))

    count = cursor.fetchone()["count"]
    conn.close()
    return count > 0


if __name__ == "__main__":
    print("Initializing database...")
    init_database()

    # test saving a sample job
    sample_job = {
        "id": "test_001",
        "title": "AI Engineer Intern",
        "company": "Ensono",
        "location": "Remote",
        "is_remote": True,
        "employment_type": "INTERN",
        "apply_url": "https://ensono.com/careers",
        "apply_platform": "greenhouse",
        "description": "AI/ML internship role"
    }

    sample_score = {
        "match_score": 88,
        "recommendation": "PRIORITY",
        "reasoning": "Exceptional match",
        "best_projects": [{"name": "Explainable ML Pipeline", "reason": "Direct match"}],
        "cover_letter_angle": "Lead with 50+ projects",
        "missing_skills": [],
        "strengths": ["Strong ML portfolio"],
        "priority_flag": True
    }

    save_job(sample_job, sample_score)
    print("Sample job saved.")

    # test application recording
    app_id = save_application(
        job_id="test_001",
        company="Ensono",
        title="AI Engineer Intern",
        platform="greenhouse",
        apply_url="https://ensono.com/careers"
    )
    print(f"Sample application recorded. ID: {app_id}")

    # show stats
    stats = get_stats()
    print("\n--- DATABASE STATS ---")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # check duplicate detection
    is_duplicate = already_applied("Ensono", "AI Engineer Intern")
    print(f"\nDuplicate check for Ensono: {is_duplicate}")
