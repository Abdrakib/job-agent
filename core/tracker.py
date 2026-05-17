import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "applications.db"


def _use_postgres() -> bool:
    return bool(DATABASE_URL)


def get_connection():
    """PostgreSQL when DATABASE_URL is set; otherwise local SQLite."""
    if _use_postgres():
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _close(conn, cursor=None):
    if cursor is not None:
        cursor.close()
    conn.close()


def init_database():
    """Create all tables if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()

    if _use_postgres():
        app_id_type = "SERIAL PRIMARY KEY"
    else:
        app_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cursor.execute(f"""
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
            cover_letter_text TEXT,
            resume_path TEXT,
            date_found TEXT,
            date_applied TEXT,
            status TEXT DEFAULT 'found',
            notes TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS applications (
            id {app_id_type},
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS follow_ups (
            id {app_id_type},
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

    _migrate_jobs_columns(cursor)
    conn.commit()
    _close(conn, cursor)
    save_default_settings()
    print("Database initialized successfully.")


def _migrate_jobs_columns(cursor):
    """Add columns for existing databases."""
    for col in ("cover_letter_text", "resume_path"):
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
        except Exception:
            pass


def save_default_settings():
    defaults = {
        "work_location": "remote",
        "job_types": "internship,fulltime",
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
        if _use_postgres():
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (key, value, now))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))

    conn.commit()
    _close(conn, cursor)


def get_setting(key: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    if _use_postgres():
        cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
    else:
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    _close(conn, cursor)
    return row["value"] if row else None


def save_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    if _use_postgres():
        cursor.execute("""
            INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
        """, (key, value, now))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, now))
    conn.commit()
    _close(conn, cursor)


def _job_hybrid_flag(job: dict) -> int:
    location_str = (job.get("location") or "").lower()
    title_str = (job.get("title") or "").lower()
    desc_str = (job.get("description") or "").lower()
    return 1 if any("hybrid" in s for s in [location_str, title_str, desc_str]) else 0


def save_job(job: dict, scored_data: dict = None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    best_projects = json.dumps(scored_data.get("best_projects", [])) if scored_data else "[]"
    missing_skills = json.dumps(scored_data.get("missing_skills", [])) if scored_data else "[]"
    strengths = json.dumps(scored_data.get("strengths", [])) if scored_data else "[]"

    params = (
        job.get("id", ""),
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        1 if job.get("is_remote") else 0,
        _job_hybrid_flag(job),
        job.get("employment_type", ""),
        job.get("apply_url", ""),
        job.get("apply_platform", ""),
        (job.get("description") or "")[:1000],
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
        "found",
    )

    upsert_sql = """
        INSERT INTO jobs (
            id, title, company, location, is_remote, is_hybrid,
            employment_type, apply_url, apply_platform, description,
            salary_min, salary_max, match_score, recommendation,
            reasoning, best_projects, cover_letter_angle,
            missing_skills, strengths, priority_flag, date_found, status
        ) VALUES ({vals})
        ON CONFLICT (id) DO UPDATE SET
            match_score = excluded.match_score,
            recommendation = excluded.recommendation,
            reasoning = excluded.reasoning,
            best_projects = excluded.best_projects,
            cover_letter_angle = excluded.cover_letter_angle,
            missing_skills = excluded.missing_skills,
            strengths = excluded.strengths,
            priority_flag = excluded.priority_flag
    """

    if _use_postgres():
        vals = ",".join(["%s"] * 22)
        cursor.execute(upsert_sql.format(vals=vals), params)
    else:
        vals = ",".join(["?"] * 22)
        cursor.execute(upsert_sql.format(vals=vals), params)

    conn.commit()
    _close(conn, cursor)


def save_cover_letter(job_id: str, cover_letter_text: str, resume_path: str = None):
    """Save generated cover letter text and resume path to job record."""
    conn = get_connection()
    cursor = conn.cursor()
    if _use_postgres():
        cursor.execute(
            "UPDATE jobs SET cover_letter_text = %s, resume_path = %s WHERE id = %s",
            (cover_letter_text, resume_path, job_id),
        )
    else:
        cursor.execute(
            "UPDATE jobs SET cover_letter_text = ?, resume_path = ? WHERE id = ?",
            (cover_letter_text, resume_path, job_id),
        )
    conn.commit()
    _close(conn, cursor)


def get_documents(min_score: int = 70, limit: int = 50) -> list:
    """Get jobs that have generated cover letters."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT id, title, company, location, is_remote, apply_url,
               apply_platform, match_score, priority_flag, status,
               cover_letter_text, resume_path, date_found,
               reasoning, best_projects
        FROM jobs
        WHERE match_score >= {ph}
        AND cover_letter_text IS NOT NULL
        ORDER BY priority_flag DESC, match_score DESC
        LIMIT {ph}
    """
    if _use_postgres():
        cursor.execute(query.format(ph="%s"), (min_score, limit))
    else:
        cursor.execute(query.format(ph="?"), (min_score, limit))
    rows = cursor.fetchall()
    _close(conn, cursor)
    return [dict(row) for row in rows]


def save_application(job_id: str, company: str, title: str,
                     platform: str, apply_url: str,
                     cover_letter_path: str = None,
                     resume_path: str = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    follow_up_days = int(get_setting("follow_up_days") or 7)
    follow_up_date = (datetime.now() + timedelta(days=follow_up_days)).isoformat()

    insert_params = (
        job_id, company, title, platform, apply_url,
        cover_letter_path, resume_path, now, "applied", now, follow_up_date,
    )

    if _use_postgres():
        cursor.execute("""
            INSERT INTO applications (
                job_id, company, title, apply_platform, apply_url,
                cover_letter_path, resume_path, date_applied,
                status, last_updated, follow_up_date
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, insert_params)
        app_id = cursor.fetchone()["id"]
        cursor.execute(
            "UPDATE jobs SET status = 'applied', date_applied = %s WHERE id = %s",
            (now, job_id),
        )
        cursor.execute("""
            INSERT INTO follow_ups (application_id, job_id, company, title, scheduled_date)
            VALUES (%s,%s,%s,%s,%s)
        """, (app_id, job_id, company, title, follow_up_date))
    else:
        cursor.execute("""
            INSERT INTO applications (
                job_id, company, title, apply_platform, apply_url,
                cover_letter_path, resume_path, date_applied,
                status, last_updated, follow_up_date
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, insert_params)
        app_id = cursor.lastrowid
        cursor.execute(
            "UPDATE jobs SET status = 'applied', date_applied = ? WHERE id = ?",
            (now, job_id),
        )
        cursor.execute("""
            INSERT INTO follow_ups (application_id, job_id, company, title, scheduled_date)
            VALUES (?,?,?,?,?)
        """, (app_id, job_id, company, title, follow_up_date))

    conn.commit()
    _close(conn, cursor)
    return app_id


def update_application_status(application_id: int, status: str,
                            response_type: str = None, notes: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    params = (status, now, now, response_type, notes, application_id)
    if _use_postgres():
        cursor.execute("""
            UPDATE applications SET status=%s, last_updated=%s, response_date=%s,
            response_type=%s, notes=COALESCE(%s, notes) WHERE id=%s
        """, params)
    else:
        cursor.execute("""
            UPDATE applications SET status=?, last_updated=?, response_date=?,
            response_type=?, notes=COALESCE(?, notes) WHERE id=?
        """, params)
    conn.commit()
    _close(conn, cursor)


def mark_follow_up_sent(follow_up_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    if _use_postgres():
        cursor.execute(
            "UPDATE follow_ups SET sent=1, sent_date=%s WHERE id=%s",
            (now, follow_up_id),
        )
    else:
        cursor.execute(
            "UPDATE follow_ups SET sent=1, sent_date=? WHERE id=?",
            (now, follow_up_id),
        )
    conn.commit()
    _close(conn, cursor)


def get_applications(status: str = None, limit: int = 100) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        if _use_postgres():
            cursor.execute(
                "SELECT * FROM applications WHERE status=%s ORDER BY date_applied DESC LIMIT %s",
                (status, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM applications WHERE status=? ORDER BY date_applied DESC LIMIT ?",
                (status, limit),
            )
    else:
        if _use_postgres():
            cursor.execute(
                "SELECT * FROM applications ORDER BY date_applied DESC LIMIT %s",
                (limit,),
            )
        else:
            cursor.execute(
                "SELECT * FROM applications ORDER BY date_applied DESC LIMIT ?",
                (limit,),
            )
    rows = cursor.fetchall()
    _close(conn, cursor)
    return [dict(row) for row in rows]


def get_jobs(status: str = None, min_score: int = 0,
             work_location: str = "any", limit: int = 100) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM jobs WHERE match_score >= " + ("%s" if _use_postgres() else "?")
    params = [min_score]

    if status:
        query += " AND status = " + ("%s" if _use_postgres() else "?")
        params.append(status)

    if work_location == "remote":
        query += " AND is_remote = 1"
    elif work_location == "hybrid":
        query += " AND (is_remote = 1 OR is_hybrid = 1)"
    elif work_location == "onsite":
        query += " AND is_remote = 0 AND is_hybrid = 0"

    query += " ORDER BY priority_flag DESC, match_score DESC LIMIT " + (
        "%s" if _use_postgres() else "?"
    )
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    _close(conn, cursor)
    return [dict(row) for row in rows]


def get_pending_follow_ups() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    if _use_postgres():
        cursor.execute("""
            SELECT f.*, a.apply_url, a.cover_letter_path FROM follow_ups f
            JOIN applications a ON f.application_id = a.id
            WHERE f.scheduled_date <= %s AND f.sent = 0 AND a.status = 'applied'
            ORDER BY f.scheduled_date ASC
        """, (now,))
    else:
        cursor.execute("""
            SELECT f.*, a.apply_url, a.cover_letter_path FROM follow_ups f
            JOIN applications a ON f.application_id = a.id
            WHERE f.scheduled_date <= ? AND f.sent = 0 AND a.status = 'applied'
            ORDER BY f.scheduled_date ASC
        """, (now,))
    rows = cursor.fetchall()
    _close(conn, cursor)
    return [dict(row) for row in rows]


def get_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}

    queries = [
        ("total_jobs_found", "SELECT COUNT(*) as count FROM jobs"),
        ("total_applied", "SELECT COUNT(*) as count FROM applications"),
        ("interviews", "SELECT COUNT(*) as count FROM applications WHERE status='interview'"),
        ("rejections", "SELECT COUNT(*) as count FROM applications WHERE status='rejected'"),
        ("offers", "SELECT COUNT(*) as count FROM applications WHERE status='offer'"),
        ("priority_jobs", "SELECT COUNT(*) as count FROM jobs WHERE priority_flag=1 AND status='found'"),
    ]

    for key, query in queries:
        cursor.execute(query)
        stats[key] = cursor.fetchone()["count"]

    now = datetime.now().isoformat()
    if _use_postgres():
        cursor.execute(
            "SELECT COUNT(*) as count FROM follow_ups WHERE sent=0 AND scheduled_date <= %s",
            (now,),
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) as count FROM follow_ups WHERE sent=0 AND scheduled_date <= ?",
            (now,),
        )
    stats["pending_followups"] = cursor.fetchone()["count"]

    _close(conn, cursor)
    return stats


def already_applied(company: str, title: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    pattern = f"%{title[:20]}%"
    if _use_postgres():
        cursor.execute("""
            SELECT COUNT(*) as count FROM applications
            WHERE LOWER(company) = LOWER(%s) AND LOWER(title) LIKE LOWER(%s)
        """, (company, pattern))
    else:
        cursor.execute("""
            SELECT COUNT(*) as count FROM applications
            WHERE LOWER(company) = LOWER(?) AND LOWER(title) LIKE LOWER(?)
        """, (company, pattern))
    count = cursor.fetchone()["count"]
    _close(conn, cursor)
    return count > 0


if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    print(f"Backend: {'PostgreSQL' if _use_postgres() else f'SQLite ({DB_PATH})'}")
