import anthropic
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import date

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

RAKIB_VOICE = """
REAL FACTS ABOUT THIS CANDIDATE (use these to make the letter feel authentic):
- Built 50+ ML projects not for a class or bootcamp — because he genuinely could not stop building
- Trained a 124M parameter GPT-2 completely from scratch on TinyStories just to understand how transformers work internally
- Spent 30+ hours debugging a ZeroGPU/Gradio version conflict to get his Explainable ML Pipeline deployed — he does not give up
- ML internship at Buildawn Labs: remote, working on computer vision, LLMs, and reinforcement learning
- He deploys everything — FastAPI, React, Vercel, Render, HuggingFace Spaces — he ships, not just notebooks
- Associate degree, not a bachelor's — he owns this and compensates with output and practical evidence
- Graduating May 2026 from Community College of Philadelphia
- Thinks in systems — builds agents, not scripts: AutoML agents, research agents, trading agents, visual analyst agents
- GitHub: github.com/Abdrakib | HuggingFace: Abdourakib | Portfolio: abdourakib.com
- Speaks English and French fluently
"""


def generate_cover_letter(scored_job: dict, candidate_profile: dict) -> str:
    """Two-pass cover letter generation."""
    best_projects = scored_job.get("best_projects", [])
    cover_letter_angle = scored_job.get("cover_letter_angle", "")

    project_details = ""
    for p in best_projects:
        project_details += f"- {p['name']}: {p['reason']}\n"

    candidate_skills = candidate_profile.get("skills", {})
    skills_flat = ", ".join(
        candidate_skills.get("ml_ai", []) +
        candidate_skills.get("specializations", [])[:3]
    )

    prompt_pass1 = f"""Write a cover letter body AS Abdou Rakib Abente for this job. You are writing in his voice.

{RAKIB_VOICE}

JOB:
Title: {scored_job.get('job_title')}
Company: {scored_job.get('company')}
Location: {scored_job.get('location')} | Remote: {scored_job.get('is_remote')}
Description: {scored_job.get('job_description', '')[:1000]}

STRATEGIC ANGLE TO USE:
{cover_letter_angle}

PROJECTS TO REFERENCE (pick the 2 most relevant, tell a story — don't list):
{project_details}

TONE RULES:
- Write like a smart confident person talking, not a formal applicant
- Use contractions: I've, I'm, I'd, that's, it's, don't, can't
- Vary sentence length — mix short punchy sentences with longer ones
- One sentence may start with "And" or "But"
- No bullet points — pure prose
- BANNED WORDS: passionate, excited, thrilled, leverage, synergy, impactful, robust, innovative, utilize, spearhead, driven, motivated
- BANNED PHRASES: "I am writing to", "I believe I would be", "I am confident that", "perfect fit", "quick learner"
- Never start the letter with "I"

CONTENT RULES:
- Paragraph 1: open with a specific concrete achievement or fact. Hook them in 2-3 sentences.
- Paragraph 2: short story about 1-2 projects — what problem, what you built, what result. If there is a potential concern (degree, experience), address it in one direct sentence and immediately pivot to evidence.
- Paragraph 3: one specific sentence on why THIS company, then a direct ask.

Length: exactly 3 paragraphs, under 380 words.
Output: ONLY the letter body — no greeting, no sign-off, no subject line."""

    r1 = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt_pass1}]
    )
    draft = r1.content[0].text.strip()

    prompt_pass2 = f"""Read this cover letter draft. Find any sentences that sound like AI wrote them and rewrite only those.

DRAFT:
{draft}

A sentence sounds AI-written if it:
- Is perfectly structured with no personality or roughness
- Uses vague positive language with no specifics
- Could apply to any candidate anywhere
- Is overly formal in a way no human would speak

REWRITING RULES:
- Only touch sentences that fail the test
- Keep all specific facts, project names, and numbers exactly
- Keep the same 3-paragraph structure
- Do not add new content or remove paragraphs

Return ONLY the final letter body. No commentary."""

    r2 = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt_pass2}]
    )
    return r2.content[0].text.strip()


def format_full_cover_letter(body: str, candidate_profile: dict, scored_job: dict) -> str:
    name = candidate_profile.get("name", "Abdou Rakib Abente")
    email = candidate_profile.get("email", "Rakibabente8@gmail.com")
    phone = candidate_profile.get("phone", "+1(267)-344-5217")
    company = scored_job.get("company", "")
    job_title = scored_job.get("job_title", "")
    today = date.today().strftime("%B %d, %Y")

    header = f"""{name}
{email} | {phone} | github.com/Abdrakib | abdourakib.com

{today}

Hiring Manager
{company}

Re: {job_title}

Dear Hiring Manager,

"""
    footer = f"""

I'd welcome the chance to talk. You can reach me at {email} or {phone}.

Sincerely,
{name}"""

    return header + body + footer


def generate_and_save_cover_letter(
    scored_job: dict,
    candidate_profile: dict,
    output_dir: str = "generated_resumes"
) -> str:
    """Generate cover letter, save to file AND save text to database."""
    from core.tracker import save_cover_letter
    from core.resume_builder import build_resume_pdf

    Path(output_dir).mkdir(exist_ok=True)

    company = scored_job.get("company", "company").replace(" ", "_").replace("/", "_")
    title = scored_job.get("job_title", "role").replace(" ", "_").replace("/", "_")[:30]
    filename = f"{output_dir}/cover_letter_{company}_{title}.txt"

    print(f"  Writing cover letter for {scored_job.get('job_title')} at {scored_job.get('company')}...")

    body = generate_cover_letter(scored_job, candidate_profile)
    full = format_full_cover_letter(body, candidate_profile, scored_job)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(full)

    resume_path = None
    try:
        resume_path = build_resume_pdf(scored_job, candidate_profile)
    except Exception as e:
        print(f"  Resume build failed: {e}")

    job_id = scored_job.get("job_id", "")
    if job_id:
        save_cover_letter(job_id, full, resume_path)
        print(f"  Saved to DB for job_id: {job_id}")

    print(f"  Cover letter saved: {filename}")
    return full
