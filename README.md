# 🤖 Job Agent — Autonomous AI Job Application System

An intelligent agent that autonomously discovers, scores, and applies to AI/ML jobs — built with Claude AI, Python, and Streamlit.

---

## What It Does

- **Discovers** 100+ relevant jobs daily via JSearch API across LinkedIn, Indeed, Glassdoor and 50+ job boards
- **Scores** each job against your resume and skills using Claude AI (0-100 match score)
- **Builds** a tailored resume per job — dynamically selects the best projects from your portfolio
- **Writes** human-sounding cover letters in 2 passes — draft then humanization
- **Applies** automatically to Greenhouse and Lever companies via their public APIs
- **Monitors** Gmail inbox — classifies replies, sends notifications for interview requests
- **Tracks** every application in SQLite with status updates and follow-up scheduling
- **Dashboard** — Gold + Royal Indigo Streamlit UI with filters and real-time stats
- **Location-aware** — searches globally for remote, Philadelphia metro for hybrid/onsite

---

## Architecture

```
job_agent/
├── core/
│   ├── job_finder.py        # JSearch API — location-aware discovery
│   ├── job_scorer.py        # Claude AI scoring engine
│   ├── cover_letter.py      # 2-pass human cover letter generation
│   ├── resume_builder.py    # Dynamic PDF resume per job
│   ├── project_bank.py      # 45+ project portfolio management
│   ├── resume_parser.py     # PDF resume parsing with Claude
│   └── tracker.py           # SQLite application database
├── apply/
│   ├── greenhouse.py        # Greenhouse public API auto-apply
│   └── lever.py             # Lever public API auto-apply
├── gmail/
│   ├── gmail_connect.py     # Gmail OAuth2 + label management
│   └── notifier.py          # Inbox monitoring + notifications
├── dashboard/
│   └── app.py               # Streamlit dashboard
├── scheduler/
│   └── runner.py            # APScheduler 24/7 automation
├── sync.py                  # GitHub repo sync
├── requirements.txt
├── Procfile                 # Railway deployment
└── .env.example
```

---

## How It Works

### 1. Job Discovery
The agent runs 14 targeted search queries across JSearch API which aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter, Monster and more. It filters by work location preference — remote jobs search globally, hybrid/onsite jobs search the Philadelphia metro area only (within ~40 min drive).

### 2. AI Scoring
Claude reads each job description and scores it against your candidate profile — resume, skills, and 45+ portfolio projects. Returns a 0-100 match score, recommendation (APPLY/SKIP/PRIORITY), best projects to highlight, and the ideal cover letter angle.

### 3. Dynamic Resume
For each job above the score threshold, the agent picks the 4-5 most relevant projects from your portfolio and builds a tailored one-page PDF resume. A computer vision role gets your CV projects. An NLP role gets your LLM projects. Never the same resume twice.

### 4. Cover Letter Generation
Two-pass generation. Pass 1 writes the letter using your real story and the job's strategic angle. Pass 2 reads the draft and rewrites any sentence that sounds AI-generated. The result uses contractions, specific facts, and your voice.

### 5. Auto-Apply
- **Greenhouse companies** — applied via public Greenhouse API. No browser needed.
- **Lever companies** — applied via public Lever API. No browser needed.
- **Other platforms** — agent fills the form, you click submit.

### 6. Gmail Monitoring
Connects to Gmail via OAuth2. Creates labeled folders (Interview Requests, Confirmations, Rejections, Follow Up Needed). Classifies every incoming email and sends you a notification for anything important. Schedules follow-up emails after 7 days of no response.

### 7. Dashboard
Full Streamlit UI with Gold + Royal Indigo theme. Filter jobs by location, match score, salary, and status. Track every application. Update statuses. View your entire project bank. Run the agent with one click.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Brain | Claude API (Anthropic) — Sonnet |
| Job Discovery | JSearch API via RapidAPI |
| Resume PDF | ReportLab |
| Email | Gmail API (OAuth2) |
| Database | SQLite |
| Dashboard | Streamlit |
| Auto-apply | Greenhouse API + Lever API |
| Scheduling | APScheduler |
| Notifications | Twilio SMS + Gmail |
| Deployment | Railway |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Abdrakib/job-agent
cd job-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# fill in your API keys in .env
```

### 3. Set up Gmail

- Go to console.cloud.google.com
- Create a project, enable Gmail API
- Create OAuth2 credentials (Desktop App)
- Download JSON, save as `data/gmail_credentials.json`

### 4. Initialize database

```bash
python -m core.tracker
```

### 5. Add your resume

```bash
# copy your resume PDF to:
data/base_resume.pdf
```

### 6. Run dashboard

```bash
python -m streamlit run dashboard/app.py
```

### 7. Run full pipeline once

```bash
python -m scheduler.runner --run-now
```

### 8. Start 24/7 scheduler

```bash
python -m scheduler.runner --schedule
```

---

## Environment Variables

```bash
# Anthropic
ANTHROPIC_API_KEY=your_key_here

# RapidAPI JSearch
RAPIDAPI_KEY=your_key_here

# GitHub
GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_token

# Gmail OAuth
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REDIRECT_URI=http://localhost:8080

# Twilio SMS
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
YOUR_PHONE_NUMBER=+1xxxxxxxxxx

# Settings
MAX_JOBS_PER_RUN=100
MIN_MATCH_SCORE=70
FOLLOW_UP_DAYS=7
```

---

## Deployment on Railway

```bash
# 1. Push to GitHub
git add .
git commit -m "deploy"
git push

# 2. Go to railway.app
# 3. New Project → Deploy from GitHub
# 4. Add environment variables from .env
# 5. Done — runs 24/7 automatically
```

Monthly cost: ~$5 (Railway) + Claude API (~$2) = **~$7/month**

---

## Scheduler

When deployed, the agent runs automatically:

| Time | Action |
|---|---|
| 8:00 AM daily | Full run — discover, score, apply |
| Every 2 hours | Check Gmail inbox |
| Midnight | Sync GitHub repos |

---

## Built By

**Abdou Rakib Abente** — AI/ML Engineer

- GitHub: [github.com/Abdrakib](https://github.com/Abdrakib)
- HuggingFace: [Abdourakib](https://huggingface.co/Abdourakib)
- Portfolio: [abdourakib.com](https://abdourakib.com)
- LinkedIn: [linkedin.com/in/rakib-abente](https://linkedin.com/in/rakib-abente)

---

## License

MIT
