import html
import json
import streamlit as st
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from core.tracker import (
    init_database, get_stats, get_jobs, get_applications,
    get_pending_follow_ups, get_setting, save_setting,
    update_application_status, already_applied, mark_follow_up_sent,
    get_documents
)

st.set_page_config(
    page_title="Job Agent — Rakib",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* hide default streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

:root {
    --bg:       #1A1040;
    --surface:  #221550;
    --surface2: #2A1A60;
    --border:   rgba(212,175,55,0.15);
    --border2:  rgba(212,175,55,0.30);
    --gold:     #D4AF37;
    --gold2:    #F5D060;
    --gold3:    #8B7320;
    --text:     #F0EAD6;
    --muted:    rgba(240,234,214,0.45);
    --purple:   #4338CA;
    --purple2:  #6D5FD8;
}

html, body, .stApp { background: #1A1040 !important; }
.stApp * { font-family: 'Syne', sans-serif !important; }

[data-testid="stSidebar"] {
    background: #130B30 !important;
    border-right: 1px solid rgba(212,175,55,0.2) !important;
}
[data-testid="stSidebar"] * { color: #F0EAD6 !important; }

section[data-testid="stSidebar"] > div { background: #130B30 !important; }

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(212,175,55,0.15) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: rgba(240,234,214,0.5) !important;
    border-bottom: 2px solid transparent !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
}
.stTabs [aria-selected="true"] {
    color: #D4AF37 !important;
    border-bottom: 2px solid #D4AF37 !important;
    background: transparent !important;
}

.stSelectbox > div > div {
    background: #221550 !important;
    border: 1px solid rgba(212,175,55,0.2) !important;
    color: #F0EAD6 !important;
    border-radius: 8px !important;
}
.stMultiSelect > div > div {
    background: #221550 !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
    color: #F0EAD6 !important;
}
.stMultiSelect span {
    color: #F0EAD6 !important;
}
.stMultiSelect [data-baseweb="tag"] {
    background: rgba(212,175,55,0.2) !important;
    border: 1px solid rgba(212,175,55,0.4) !important;
}
.stMultiSelect [data-baseweb="tag"] span {
    color: #D4AF37 !important;
}
.stMultiSelect input {
    color: #F0EAD6 !important;
    background: transparent !important;
}
.stNumberInput > div > div > input {
    background: #221550 !important;
    color: #F0EAD6 !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
    border-radius: 8px !important;
}
.stNumberInput button {
    background: #221550 !important;
    color: #D4AF37 !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
}
[data-baseweb="select"] * {
    background: #221550 !important;
    color: #F0EAD6 !important;
}
[data-baseweb="menu"] {
    background: #221550 !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
}
[data-baseweb="option"]:hover {
    background: rgba(212,175,55,0.15) !important;
}

.stSlider > div > div > div { background: #D4AF37 !important; }
.stSlider > div > div > div > div { background: #D4AF37 !important; }

.stButton > button {
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 13px !important;
    letter-spacing: 0.3px !important;
}
.stButton > button:not([kind="secondary"]) {
    background: linear-gradient(135deg, #D4AF37, #F5D060) !important;
    color: #1A1040 !important;
    border: none !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #D4AF37, #F5D060) !important;
    color: #1A1040 !important;
    border: none !important;
    font-weight: 700 !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #F5D060, #D4AF37) !important;
    transform: translateY(-1px) !important;
}

.stMetric { background: #221550 !important; border: 1px solid rgba(212,175,55,0.2) !important; border-radius: 12px !important; padding: 16px !important; }
[data-testid="metric-container"] { background: #221550 !important; border: 1px solid rgba(212,175,55,0.2) !important; border-radius: 12px !important; padding: 14px !important; }
[data-testid="stMetricValue"] { color: #D4AF37 !important; font-family: 'Space Mono', monospace !important; font-size: 28px !important; }
[data-testid="stMetricLabel"] { color: rgba(240,234,214,0.6) !important; font-size: 11px !important; text-transform: uppercase !important; letter-spacing: 1px !important; }

.stToggle > label { color: #F0EAD6 !important; }

h1, h2, h3, h4, p, label, span, div { color: #F0EAD6; }
.stMarkdown p { color: #F0EAD6 !important; }

hr { border-color: rgba(212,175,55,0.15) !important; }

.stSuccess { background: rgba(212,175,55,0.1) !important; border: 1px solid rgba(212,175,55,0.3) !important; color: #F5D060 !important; border-radius: 8px !important; }
.stError { background: rgba(255,71,87,0.1) !important; border: 1px solid rgba(255,71,87,0.3) !important; border-radius: 8px !important; }
.stInfo { background: rgba(67,56,202,0.2) !important; border: 1px solid rgba(67,56,202,0.4) !important; border-radius: 8px !important; }
.stSpinner > div { border-top-color: #D4AF37 !important; }

::-webkit-scrollbar { width: 4px; background: #1A1040; }
::-webkit-scrollbar-thumb { background: rgba(212,175,55,0.3); border-radius: 4px; }

/* Multiselect dropdown menu */
[data-baseweb="popover"] {
    background: #221550 !important;
}
[data-baseweb="popover"] ul {
    background: #221550 !important;
}
[data-baseweb="popover"] li {
    background: #221550 !important;
    color: #F0EAD6 !important;
}
[data-baseweb="popover"] li:hover {
    background: rgba(212,175,55,0.15) !important;
}
[data-baseweb="popover"] li span {
    color: #F0EAD6 !important;
}

/* Number input — fix white background */
input[type="number"] {
    background: #221550 !important;
    color: #F0EAD6 !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
    border-radius: 8px !important;
    -webkit-text-fill-color: #F0EAD6 !important;
}
input[type="number"]:focus {
    border-color: #D4AF37 !important;
    box-shadow: 0 0 0 1px #D4AF37 !important;
}

/* Fix all input backgrounds globally in sidebar */
[data-testid="stSidebar"] input {
    background: #221550 !important;
    color: #F0EAD6 !important;
    -webkit-text-fill-color: #F0EAD6 !important;
}
[data-testid="stSidebar"] button[kind="secondary"] {
    background: #221550 !important;
    color: #D4AF37 !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
}
</style>
""", unsafe_allow_html=True)

init_database()

# Clean corrupted job records containing raw HTML
try:
    from core.tracker import get_connection as _gc
    _c = _gc()
    _cur = _c.cursor()
    _cur.execute("DELETE FROM jobs WHERE reasoning LIKE '<%' OR reasoning LIKE '%<div%' OR reasoning LIKE '%font-size%'")
    _cur.execute("DELETE FROM jobs WHERE company = 'Dry Ground AI'")
    # wipe HTML from reasoning
    _cur.execute("UPDATE jobs SET reasoning = '' WHERE reasoning LIKE '<%' OR reasoning LIKE '%font-size%' OR reasoning LIKE '%<div%'")
    # wipe HTML from description  
    _cur.execute("UPDATE jobs SET description = '' WHERE description LIKE '<%' OR description LIKE '%font-size%'")
    # delete jobs where title is empty or corrupted
    _cur.execute("DELETE FROM jobs WHERE title = '' OR title IS NULL")
    _c.commit()
    _cur.close()
    _c.close()
except Exception:
    pass

# ── HELPERS ─────────────────────────────────────────────────

def gold_badge(text, style=""):
    return f'<span style="background:rgba(212,175,55,0.15);color:#D4AF37;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;font-family:Space Mono,monospace;{style}">{text}</span>'

def score_badge(score):
    if score >= 80:
        color, bg = "#D4AF37", "rgba(212,175,55,0.15)"
    elif score >= 65:
        color, bg = "#A78BFA", "rgba(167,139,250,0.15)"
    else:
        color, bg = "rgba(240,234,214,0.4)", "rgba(240,234,214,0.08)"
    return f'<span style="background:{bg};color:{color};font-size:12px;font-weight:700;padding:4px 10px;border-radius:20px;font-family:Space Mono,monospace;">{score}%</span>'

def status_badge(status):
    styles = {
        "found":     ("rgba(240,234,214,0.4)", "rgba(240,234,214,0.08)"),
        "applied":   ("#7DD3FC", "rgba(125,211,252,0.1)"),
        "interview": ("#D4AF37", "rgba(212,175,55,0.15)"),
        "rejected":  ("#F87171", "rgba(248,113,113,0.1)"),
        "offer":     ("#34D399", "rgba(52,211,153,0.1)"),
    }
    color, bg = styles.get(status, styles["found"])
    return f'<span style="background:{bg};color:{color};font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;">{status.title()}</span>'

def platform_badge(platform):
    auto = platform in ["greenhouse", "lever", "linkedin", "indeed"]
    color = "#D4AF37" if auto else "rgba(240,234,214,0.4)"
    bg = "rgba(212,175,55,0.12)" if auto else "rgba(240,234,214,0.06)"
    label = f"⚡ {platform}" if auto else platform
    return f'<span style="background:{bg};color:{color};font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;font-family:Space Mono,monospace;text-transform:uppercase;">{label}</span>'

def render_job_card(job):
    priority = job.get("priority_flag", 0)
    border = "border-left: 3px solid #D4AF37;" if priority else "border-left: 3px solid rgba(212,175,55,0.2);"
    score = job.get("match_score", 0)
    platform = job.get("apply_platform", "direct")
    is_remote = job.get("is_remote", 0)
    location = "🌐 Remote" if is_remote else f"📍 {job.get('location', '')}"
    # Get reasoning and aggressively clean it
    _raw = job.get("reasoning", "") or ""
    # if it looks like HTML at all, just hide it entirely
    if "<" in _raw or "font-size" in _raw or "div style" in _raw or "&lt;" in _raw:
        reasoning_display = ""
    else:
        _reasoning_plain = re.sub(r"\s+", " ", _raw).strip()
        reasoning_display = _reasoning_plain[:200] + ("..." if len(_reasoning_plain) > 200 else "")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    salary = ""
    if salary_min and salary_max:
        salary = f'<span style="color:#D4AF37;font-size:12px;">💰 ${int(salary_min):,}–${int(salary_max):,}</span>'
    elif salary_min:
        salary = f'<span style="color:#D4AF37;font-size:12px;">💰 ${int(salary_min):,}+</span>'

    star = "✦ " if priority else ""

    st.markdown(f"""
    <div style="background:#221550;{border}border-radius:0 12px 12px 0;padding:16px 18px;margin-bottom:10px;border-top:1px solid rgba(212,175,55,0.1);border-right:1px solid rgba(212,175,55,0.1);border-bottom:1px solid rgba(212,175,55,0.1);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
            <div>
                <div style="font-size:15px;font-weight:700;color:#F0EAD6;margin-bottom:3px;">{star}{job.get('title','')}</div>
                <div style="font-size:13px;color:rgba(240,234,214,0.6);">{job.get('company','')}</div>
            </div>
            <div>{score_badge(score)}</div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:8px;">
            <span style="font-size:12px;color:rgba(240,234,214,0.5);">{location}</span>
            <span style="color:rgba(212,175,55,0.3);">|</span>
            {platform_badge(platform)}
            {f'<span style="color:rgba(212,175,55,0.3);">|</span>{salary}' if salary else ''}
        </div>
        {f'<div style="font-size:12px;color:rgba(240,234,214,0.45);margin-top:10px;line-height:1.6;border-top:1px solid rgba(212,175,55,0.08);padding-top:8px;">{reasoning_display}</div>' if reasoning_display else ''}
    </div>
    """, unsafe_allow_html=True)

def render_app_card(app):
    status = app.get("status", "applied")
    date = app.get("date_applied", "")[:10]
    followup = app.get("follow_up_date", "")[:10]
    platform = app.get("apply_platform", "direct")

    st.markdown(f"""
    <div style="background:#221550;border:1px solid rgba(212,175,55,0.15);border-radius:12px;padding:16px 18px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div>
                <div style="font-size:15px;font-weight:700;color:#F0EAD6;">{app.get('title','')}</div>
                <div style="font-size:13px;color:rgba(240,234,214,0.6);margin-top:2px;">{app.get('company','')}</div>
            </div>
            {status_badge(status)}
        </div>
        <div style="display:flex;gap:16px;margin-top:8px;flex-wrap:wrap;">
            <span style="font-size:11px;color:rgba(240,234,214,0.4);">Applied: {date}</span>
            <span style="font-size:11px;color:rgba(240,234,214,0.4);">Follow-up: {followup}</span>
            {platform_badge(platform)}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])
    with col2:
        options = ["applied", "interview", "rejected", "offer", "withdrawn"]
        new_status = st.selectbox(
            "Status",
            options,
            index=options.index(status) if status in options else 0,
            key=f"status_{app['id']}",
            label_visibility="collapsed"
        )
        if new_status != status:
            update_application_status(app["id"], new_status)
            st.rerun()


# ── SIDEBAR ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 0 16px;border-bottom:1px solid rgba(212,175,55,0.2);margin-bottom:20px;">
        <div style="font-size:22px;font-weight:800;color:#D4AF37;letter-spacing:-0.5px;">✦ Job Agent</div>
        <div style="font-size:11px;color:rgba(240,234,214,0.45);margin-top:4px;letter-spacing:0.5px;">AUTONOMOUS · INTELLIGENT</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p style="font-size:11px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Work Location</p>', unsafe_allow_html=True)
    location_options = ["Remote only", "Remote + Hybrid", "Remote + Hybrid + Onsite", "Any"]
    current_loc = get_setting("work_location") or "remote"
    loc_map = {"remote": 0, "hybrid": 1, "onsite": 2, "any": 3}
    selected_location = st.selectbox("Work Location", location_options,
                                      index=loc_map.get(current_loc, 0),
                                      label_visibility="collapsed")
    loc_save = {"Remote only": "remote", "Remote + Hybrid": "hybrid",
                "Remote + Hybrid + Onsite": "onsite", "Any": "any"}
    save_setting("work_location", loc_save[selected_location])

    st.markdown('<p style="font-size:11px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;margin:12px 0 8px;">Min Match Score</p>', unsafe_allow_html=True)
    min_score = st.slider("Score", 50, 95, int(get_setting("min_match_score") or 70), 5,
                           label_visibility="collapsed")
    save_setting("min_match_score", str(min_score))

    st.markdown('<p style="font-size:11px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;margin:12px 0 8px;">Job Type</p>', unsafe_allow_html=True)
    job_types = st.multiselect("Types", ["Internship", "Full-time", "Part-time", "Contract"],
                                default=["Internship", "Full-time"],
                                label_visibility="collapsed")

    show_salary = st.toggle("Only jobs with salary info", value=False)
    save_setting("show_no_salary", str(not show_salary).lower())
    min_salary = st.number_input("Minimum salary ($)", value=0, step=5000, min_value=0)
    save_setting("min_salary", str(min_salary))

    st.markdown('<div style="border-top:1px solid rgba(212,175,55,0.15);margin:20px 0 16px;"></div>', unsafe_allow_html=True)

    st.markdown('<p style="font-size:11px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">Run Agent</p>', unsafe_allow_html=True)

    if st.button("✦ Find & Score Jobs", use_container_width=True):
        with st.spinner("Discovering jobs..."):
            try:
                from core.job_finder import find_all_jobs
                from core.resume_parser import get_candidate_profile
                from core.job_scorer import score_all_jobs
                from core.tracker import save_job, already_applied
                from core.cover_letter import generate_and_save_cover_letter
                from apply.greenhouse import apply_greenhouse
                from apply.lever import apply_lever

                profile = get_candidate_profile()
                jobs = find_all_jobs(
                    max_jobs=int(get_setting("max_jobs_per_run") or 50),
                    work_location=get_setting("work_location") or "remote"
                )
                scored = score_all_jobs(jobs, profile, min_score=min_score)

                # save all scored jobs correctly
                jobs_by_id = {job.get("id", ""): job for job in jobs}
                for scored_job in scored:
                    original_job = jobs_by_id.get(scored_job.get("job_id", ""), scored_job)
                    scored_job_clean = {k: v for k, v in scored_job.items()}
                    save_job(original_job, scored_job_clean)

                # generate cover letters + resumes for top 15 jobs
                auto_applied = []
                hit_apply = []
                manual = []

                # generate cover letters for top 20 jobs (cost control)
                top_for_cover_letters = sorted(scored, key=lambda x: x.get("match_score", 0), reverse=True)[:20]
                for job in top_for_cover_letters:
                    if not already_applied(job.get("company", ""), job.get("job_title", "")):
                        try:
                            generate_and_save_cover_letter(job, profile)
                        except Exception as cl_err:
                            print(f"Cover letter error for {job.get('company')}: {cl_err}")

                # auto-apply to ALL scored jobs — no limit
                for job in scored:
                    company = job.get("company", "")
                    title = job.get("job_title", "")
                    platform = job.get("apply_platform", "direct")

                    if already_applied(company, title):
                        continue

                    if platform == "greenhouse":
                        try:
                            result = apply_greenhouse(
                                job=job, scored_job=job, candidate_profile=profile,
                                cover_letter_text=job.get("cover_letter_text", ""),
                                resume_path="data/base_resume.pdf"
                            )
                            if result.get("success"):
                                auto_applied.append(job)
                        except Exception as e:
                            print(f"Greenhouse error: {e}")

                    elif platform == "lever":
                        try:
                            result = apply_lever(
                                job=job, scored_job=job, candidate_profile=profile,
                                cover_letter_text=job.get("cover_letter_text", ""),
                                resume_path="data/base_resume.pdf"
                            )
                            if result.get("success"):
                                auto_applied.append(job)
                        except Exception as e:
                            print(f"Lever error: {e}")

                    elif platform == "linkedin":
                        hit_apply.append(job)
                    else:
                        manual.append(job)

                # send morning report email
                try:
                    from scheduler.runner import send_morning_report
                    send_morning_report(auto_applied, hit_apply[:10], manual[:10])
                except Exception as email_err:
                    print(f"Email report error: {email_err}")

                msg = f"✅ Found {len(scored)} jobs | "
                msg += f"Auto-applied: {len(auto_applied)} | "
                msg += f"Hit Apply: {len(hit_apply)} | "
                msg += f"Manual: {len(manual)} | "
                msg += f"Documents ready in Documents tab"
                st.success(msg)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("✉ Check Gmail Inbox", use_container_width=True):
        with st.spinner("Monitoring inbox..."):
            try:
                from gmail.notifier import process_inbox
                results = process_inbox()
                st.success(f"Processed {results['processed']} emails")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("⟳ Sync GitHub", use_container_width=True):
        with st.spinner("Syncing repos..."):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("sync", Path(__file__).parent.parent / "sync.py")
                sync_mod = importlib.util.load_from_spec(spec)
                spec.loader.exec_module(sync_mod)
                synced = sync_mod.sync_github_projects()
                st.success(f"Synced {len(synced)} repos!")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown('<div style="border-top:1px solid rgba(212,175,55,0.15);margin:20px 0 14px;"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:11px;color:rgba(240,234,214,0.35);line-height:1.8;">
        <span style="color:#D4AF37;font-weight:700;">Abdou Rakib Abente</span><br>
        github.com/Abdrakib<br>
        abdourakib.com
    </div>
    """, unsafe_allow_html=True)


# ── HEADER ──────────────────────────────────────────────────
st.markdown("""
<div style="padding:24px 0 20px;border-bottom:1px solid rgba(212,175,55,0.15);margin-bottom:24px;">
    <div style="font-size:30px;font-weight:800;color:#D4AF37;letter-spacing:-1px;">✦ Job Agent <span style="color:#F0EAD6;font-weight:400;">Dashboard</span></div>
    <div style="font-size:13px;color:rgba(240,234,214,0.45);margin-top:5px;">Autonomous discovery · Intelligent scoring · Auto-application</div>
</div>
""", unsafe_allow_html=True)

# ── STATS ───────────────────────────────────────────────────
stats = get_stats()
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
items = [
    (c1, "Jobs Found", stats.get("total_jobs_found", 0), "#D4AF37"),
    (c2, "Applied", stats.get("total_applied", 0), "#7DD3FC"),
    (c3, "Interviews", stats.get("interviews", 0), "#D4AF37"),
    (c4, "Offers", stats.get("offers", 0), "#34D399"),
    (c5, "Rejections", stats.get("rejections", 0), "#F87171"),
    (c6, "Follow-ups", stats.get("pending_followups", 0), "#A78BFA"),
    (c7, "Priority", stats.get("priority_jobs", 0), "#D4AF37"),
]
for col, label, val, color in items:
    with col:
        st.markdown(f"""
        <div style="background:#221550;border:1px solid rgba(212,175,55,0.18);border-radius:12px;padding:14px 12px;text-align:center;">
            <div style="font-size:26px;font-weight:700;color:{color};font-family:'Space Mono',monospace;">{val}</div>
            <div style="font-size:10px;color:rgba(240,234,214,0.45);text-transform:uppercase;letter-spacing:1px;margin-top:4px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ── TABS ────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["✦ Jobs", "📋 Applications", "⏰ Follow-ups", "📁 Documents", "🗂 Projects", "⚙ Settings"])

# ── TAB 1: JOBS ─────────────────────────────────────────────
with tab1:
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown('<div style="font-size:18px;font-weight:700;color:#D4AF37;margin-bottom:16px;">Discovered Jobs</div>', unsafe_allow_html=True)
    with col2:
        filter_status = st.selectbox("Status filter", ["All", "found", "applied", "interview", "rejected"],
                                      label_visibility="collapsed")
    with col3:
        location_filter = loc_save[selected_location]

    jobs = get_jobs(
        status=None if filter_status == "All" else filter_status,
        min_score=min_score,
        work_location="any",
        limit=100
    )

    if show_salary:
        jobs = [j for j in jobs if j.get("salary_min")]

    if not jobs:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:40px;color:rgba(212,175,55,0.3);margin-bottom:16px;">✦</div>
            <div style="font-size:18px;font-weight:700;color:#F0EAD6;margin-bottom:8px;">No jobs found yet</div>
            <div style="font-size:14px;color:rgba(240,234,214,0.45);">Click "Find & Score Jobs" in the sidebar to discover opportunities</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        priority = [j for j in jobs if j.get("priority_flag")]
        regular = [j for j in jobs if not j.get("priority_flag")]

        if priority:
            st.markdown(f'<div style="font-size:12px;color:#D4AF37;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:10px;">✦ Priority — {len(priority)} jobs</div>', unsafe_allow_html=True)
            for j in priority:
                render_job_card(j)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        if regular:
            st.markdown(f'<div style="font-size:12px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:10px;">All Matches — {len(regular)} jobs</div>', unsafe_allow_html=True)
            for j in regular:
                render_job_card(j)

# ── TAB 2: APPLICATIONS ─────────────────────────────────────
with tab2:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div style="font-size:18px;font-weight:700;color:#D4AF37;margin-bottom:16px;">Application Tracker</div>', unsafe_allow_html=True)
    with col2:
        app_filter = st.selectbox("Filter", ["All", "applied", "interview", "rejected", "offer"],
                                   label_visibility="collapsed")

    apps = get_applications(status=None if app_filter == "All" else app_filter)

    if not apps:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:40px;color:rgba(212,175,55,0.3);margin-bottom:16px;">📋</div>
            <div style="font-size:18px;font-weight:700;color:#F0EAD6;margin-bottom:8px;">No applications yet</div>
            <div style="font-size:14px;color:rgba(240,234,214,0.45);">Applications appear here once the agent starts applying</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for app in apps:
            render_app_card(app)

# ── TAB 3: FOLLOW-UPS ───────────────────────────────────────
with tab3:
    st.markdown('<div style="font-size:18px;font-weight:700;color:#D4AF37;margin-bottom:16px;">Pending Follow-ups</div>', unsafe_allow_html=True)
    followups = get_pending_follow_ups()

    if not followups:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:40px;color:rgba(212,175,55,0.3);margin-bottom:16px;">✓</div>
            <div style="font-size:18px;font-weight:700;color:#F0EAD6;margin-bottom:8px;">All clear</div>
            <div style="font-size:14px;color:rgba(240,234,214,0.45);">No follow-ups needed right now</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for fu in followups:
            due = fu.get("scheduled_date", "")[:10]
            st.markdown(f"""
            <div style="background:#221550;border:1px solid rgba(212,175,55,0.2);border-left:3px solid #D4AF37;border-radius:0 12px 12px 0;padding:14px 16px;margin-bottom:10px;">
                <div style="font-size:15px;font-weight:700;color:#F0EAD6;">{fu.get('title','')}</div>
                <div style="font-size:13px;color:rgba(240,234,214,0.6);margin-top:2px;">{fu.get('company','')}</div>
                <div style="font-size:12px;color:#D4AF37;margin-top:8px;">📅 Due: {due}</div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Send Follow-up", key=f"fu_{fu['id']}"):
                    st.info("Follow-up generation coming soon.")
            with col2:
                if st.button(f"Mark Done", key=f"done_{fu['id']}"):
                    mark_follow_up_sent(fu["id"])
                    st.rerun()

# ── TAB 4: DOCUMENTS ────────────────────────────────────────
with tab4:
    st.markdown('<div style="font-size:18px;font-weight:700;color:#D4AF37;margin-bottom:8px;">📁 Documents</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:rgba(240,234,214,0.5);margin-bottom:20px;">Tailored resume + cover letter for each job. Download and use to apply.</div>', unsafe_allow_html=True)

    from core.tracker import get_documents
    from core.resume_builder import build_resume_pdf

    docs = get_documents(min_score=int(get_setting("min_match_score") or 60), limit=50)

    if not docs:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:40px;color:rgba(212,175,55,0.3);margin-bottom:16px;">📁</div>
            <div style="font-size:18px;font-weight:700;color:#F0EAD6;margin-bottom:8px;">No documents yet</div>
            <div style="font-size:14px;color:rgba(240,234,214,0.45);">Run "Find & Score Jobs" to generate tailored resumes and cover letters</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        auto_platforms = ["greenhouse", "lever"]
        hit_platforms = ["linkedin"]

        for doc in docs:
            platform = doc.get("apply_platform", "direct")
            score = doc.get("match_score", 0)
            title = doc.get("title", "")
            company = doc.get("company", "")
            apply_url = doc.get("apply_url", "")
            cover_letter_text = doc.get("cover_letter_text", "")
            job_id = doc.get("id", "")

            if platform in auto_platforms:
                tier_color = "#34D399"
                tier_label = "✅ AUTO-APPLY"
            elif platform in hit_platforms:
                tier_color = "#F5D060"
                tier_label = "👆 HIT APPLY"
            else:
                tier_color = "#A78BFA"
                tier_label = "✍️ MANUAL"

            st.markdown(f"""
            <div style="background:#221550;border:1px solid rgba(212,175,55,0.15);border-radius:12px;padding:16px 18px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <div style="font-size:15px;font-weight:700;color:#F0EAD6;">{title}</div>
                        <div style="font-size:13px;color:rgba(240,234,214,0.6);margin-top:2px;">{company}</div>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center;">
                        <span style="background:rgba(212,175,55,0.15);color:#D4AF37;font-size:12px;font-weight:700;padding:3px 10px;border-radius:20px;">{score}%</span>
                        <span style="background:rgba(0,0,0,0.3);color:{tier_color};font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">{tier_label}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)

            with col1:
                if cover_letter_text:
                    st.download_button(
                        label="📝 Cover Letter",
                        data=cover_letter_text.encode("utf-8"),
                        file_name=f"cover_letter_{company.replace(' ','_')}_{title.replace(' ','_')[:20]}.txt",
                        mime="text/plain",
                        key=f"cl_{job_id}",
                        use_container_width=True
                    )
                else:
                    st.button("📝 No Cover Letter", disabled=True, key=f"cl_none_{job_id}", use_container_width=True)

            with col2:
                if st.button("📄 Download Resume", key=f"resume_{job_id}", use_container_width=True):
                    try:
                        from core.resume_parser import get_candidate_profile as _gcp
                        _profile = _gcp()
                        _scored = {
                            "job_title": title,
                            "company": company,
                            "best_projects": json.loads(doc.get("best_projects") or "[]"),
                            "match_score": score,
                        }
                        pdf_path = build_resume_pdf(_scored, _profile)
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                        st.download_button(
                            label="⬇️ Save PDF",
                            data=pdf_bytes,
                            file_name=f"resume_{company.replace(' ','_')}_{title.replace(' ','_')[:20]}.pdf",
                            mime="application/pdf",
                            key=f"pdf_dl_{job_id}",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error: {e}")

            with col3:
                if apply_url:
                    st.markdown(f"""
                    <a href="{apply_url}" target="_blank" style="display:block;text-align:center;
                    padding:8px;background:linear-gradient(135deg,#D4AF37,#F5D060);
                    color:#1A1040;font-weight:700;font-size:13px;border-radius:8px;
                    text-decoration:none;margin-top:1px;">🔗 Open Job</a>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ── TAB 5: PROJECTS ─────────────────────────────────────────
with tab5:
    st.markdown('<div style="font-size:18px;font-weight:700;color:#D4AF37;margin-bottom:16px;">Project Bank</div>', unsafe_allow_html=True)

    try:
        from core.project_bank import get_all_projects
        all_proj = get_all_projects()

        c1, c2, c3 = st.columns(3)
        for col, label, val in [(c1, "Dedicated Repos", all_proj["total_dedicated"]),
                                 (c2, "Mono-repo Projects", all_proj["total_mono"]),
                                 (c3, "Total Projects", all_proj["total"])]:
            with col:
                st.markdown(f"""
                <div style="background:#221550;border:1px solid rgba(212,175,55,0.2);border-radius:12px;padding:14px;text-align:center;margin-bottom:16px;">
                    <div style="font-size:28px;font-weight:700;color:#D4AF37;font-family:'Space Mono',monospace;">{val}</div>
                    <div style="font-size:11px;color:rgba(240,234,214,0.45);text-transform:uppercase;letter-spacing:1px;margin-top:4px;">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div style="font-size:12px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:12px;">Dedicated Repos</div>', unsafe_allow_html=True)

        for repo in all_proj["dedicated_repos"]:
            has_demo = bool(repo.get("live_demo") or repo.get("has_demo"))
            demo_tag = "🟢 Live" if has_demo else "⚪ No demo"
            demo_color = "#D4AF37" if has_demo else "rgba(240,234,214,0.3)"
            st.markdown(f"""
            <div style="background:#221550;border:1px solid rgba(212,175,55,0.15);border-radius:10px;padding:14px 16px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div style="flex:1;">
                        <div style="font-size:14px;font-weight:700;color:#F0EAD6;">{repo.get('name','')}</div>
                        <div style="font-size:11px;color:rgba(212,175,55,0.7);margin-top:2px;">{repo.get('domain','')}</div>
                        <div style="font-size:12px;color:rgba(240,234,214,0.45);margin-top:5px;line-height:1.5;">{(repo.get('description','') or '')[:110]}...</div>
                    </div>
                    <div style="text-align:right;margin-left:12px;">
                        <div style="font-size:11px;color:{demo_color};">{demo_tag}</div>
                        <div style="font-size:10px;color:rgba(240,234,214,0.3);margin-top:4px;">{repo.get('status','')}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading projects: {e}")

# ── TAB 6: SETTINGS ─────────────────────────────────────────
with tab6:
    st.markdown('<div style="font-size:18px;font-weight:700;color:#D4AF37;margin-bottom:20px;">Agent Settings</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div style="font-size:12px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Job Discovery</div>', unsafe_allow_html=True)
        max_jobs = st.number_input("Max jobs per run", value=int(get_setting("max_jobs_per_run") or 50),
                                    min_value=10, max_value=200, step=10)
        save_setting("max_jobs_per_run", str(max_jobs))

        follow_days = st.number_input("Follow-up after (days)", value=int(get_setting("follow_up_days") or 7),
                                       min_value=3, max_value=14)
        save_setting("follow_up_days", str(follow_days))

    with col2:
        st.markdown('<div style="font-size:12px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Auto-Apply</div>', unsafe_allow_html=True)
        auto_platforms = st.multiselect("Platforms", ["greenhouse", "lever", "linkedin", "indeed"],
                                         default=["greenhouse", "lever"])
        save_setting("auto_apply_platforms", ",".join(auto_platforms))

        email_notif = st.toggle("Gmail notifications", value=get_setting("email_notifications") == "true")
        save_setting("email_notifications", str(email_notif).lower())

    st.markdown('<div style="border-top:1px solid rgba(212,175,55,0.15);margin:24px 0 16px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;color:rgba(240,234,214,0.5);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Danger Zone</div>', unsafe_allow_html=True)
    if st.button("Clear all application data", type="secondary"):
        st.warning("Are you sure? This deletes all tracked applications.")
