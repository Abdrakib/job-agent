from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(__file__).parent.parent / "generated_resumes"
OUTPUT_DIR.mkdir(exist_ok=True)

CANDIDATE = {
    "name": "Abdou Rakib Abente",
    "contacts": "+1(267)-344-5217 | Rakibabente8@gmail.com | github.com/Abdrakib | huggingface.co/Abdourakib | abdourakib.com | linkedin.com/in/rakib-abente",
    "summary": "AI/ML Engineer specializing in LLMs, Generative AI, agentic AI systems, and end-to-end ML pipelines. Built and deployed production-grade AI agents and 50+ ML projects spanning NLP, computer vision, and predictive modeling. Proficient in Python, PyTorch, scikit-learn, and FastAPI.",
    "education": "Associate Degree in Computer Science — Community College of Philadelphia, Philadelphia, PA | 2023 – May 2026",
    "experience": [
        {
            "title": "Machine Learning Intern",
            "company": "Buildawn Labs",
            "duration": "Nov 2025 – Jan 2026 · Remote",
            "bullets": [
                "Built and evaluated ML models for computer vision, reinforcement learning, and LLM-based applications",
                "Developed data preprocessing pipelines and contributed to end-to-end ML workflows"
            ]
        }
    ],
    "skills": {
        "Languages": "Python, SQL, Java",
        "ML/AI": "PyTorch, TensorFlow, Scikit-learn, XGBoost, LightGBM, Pandas, NumPy, SHAP, Optuna",
        "Specializations": "LLMs, Generative AI, Agentic AI, RAG Systems, NLP, Computer Vision, Deep Learning, Transformers",
        "Tools": "Git, FastAPI, Gradio, Streamlit, HuggingFace, Plotly, boto3, AWS S3, Gemini API, Jupyter, Colab, VS Code, React"
    },
    "training": "Andrew Ng ML Specialization (Coursera) · Data Science & ML (Udemy, 44h)",
    "languages": "English (Fluent) · French (Fluent)"
}

# Project data matching original resume exactly
PROJECTS_MASTER = {
    "Explainable_ML-Pipeline-Agent": {
        "stack": "Qwen 2.5, Python, Gradio, SHAP, Optuna, scikit-learn, AWS S3",
        "link": "huggingface.co/spaces/Abdourakib/explainable-ml-pipeline-analysis-agent",
        "bullets": [
            "Built autonomous ML pipeline agent on any CSV: EDA, preprocessing, model training, SHAP explainability, Optuna hyperparameter tuning, and HTML report generation",
            "Integrated AWS S3 (boto3) for cloud storage of generated reports; deployed on HuggingFace Spaces with ZeroGPU"
        ]
    },
    "visual-analyst-agent": {
        "stack": "Gemini 2.5 Flash, Streamlit, Plotly, Pandas",
        "link": "huggingface.co/spaces/Abdourakib/visual-analyst-agent",
        "bullets": [
            "Multimodal AI agent that analyzes chart/dashboard images: detects visual type, extracts structured data, generates business insights, redraws interactive Plotly charts, supports follow-up Q&A, and exports HTML reports"
        ]
    },
    "gpt-from-scratch": {
        "stack": "PyTorch, Transformers",
        "link": "huggingface.co/Abdourakib/tinystories-gpt2-124m",
        "bullets": [
            "Trained 124M parameter GPT-2 on TinyStories; fine-tuned with Alpaca instruction dataset using AdamW and cosine LR scheduling; published to HuggingFace"
        ]
    },
    "ai-cs-tutor": {
        "stack": "RAG, FAISS, Semantic Search, Gradio",
        "link": "HuggingFace Spaces",
        "bullets": [
            "RAG-based AI tutor using FAISS vector search; retrieves relevant course content before generating answers"
        ]
    },
    "brain-tumor-ai-app": {
        "stack": "TensorFlow/Keras, FastAPI, React",
        "link": "github.com/Abdrakib/brain-tumor-ai-app",
        "bullets": [
            "CNN-based MRI classifier with Grad-CAM interpretability; deployed as full-stack app with FastAPI + React"
        ]
    },
    "Speech-emotion-recognition": {
        "stack": "MFCC, Scikit-learn, HuBERT, Gradio",
        "link": "huggingface.co/spaces/Abdourakib/Speech-emotion-demo",
        "bullets": [
            "Built emotion recognition system with HuBERT fine-tuning on RAVDESS; implemented full audio preprocessing pipeline with Gradio demo"
        ]
    },
    "ml-research-assistant": {
        "stack": "Python, Gradio, Qwen2.5-7B, HuggingFace ZeroGPU",
        "link": "huggingface.co/spaces/Abdourakib/ml-research-assistant",
        "bullets": [
            "AI-powered research tool with ArXiv search, LLM leaderboard, model benchmarks, paper finder, and live AI news feed; routes queries across 17 specialized tools"
        ]
    },
    "ai_datascience_agent": {
        "stack": "Claude API, Python, Streamlit, SHAP, Optuna",
        "link": "github.com/Abdrakib/ai_datascience_agent",
        "bullets": [
            "Claude-powered AI agent that acts as a junior ML engineer — drop in any CSV, describe your goal, get a full ML pipeline with tuning, SHAP explainability, and a shareable report"
        ]
    },
    "credit-risk-predictor": {
        "stack": "FastAPI, scikit-learn, HTML/CSS/JS",
        "link": "credit-risk-predictor-mpt9.onrender.com",
        "bullets": [
            "End-to-end ML web app predicting customer credit default risk with risk visualization, explainability panel, and REST API; deployed on Render"
        ]
    }
}


def build_styles():
    return {
        "name": ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=16,
                               textColor=colors.black, spaceAfter=3, alignment=TA_CENTER),
        "contact": ParagraphStyle("contact", fontName="Helvetica", fontSize=8,
                                  textColor=colors.HexColor("#333333"), spaceAfter=0, alignment=TA_CENTER),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=9,
                                  textColor=colors.black, spaceBefore=6, spaceAfter=2),
        "job_header": ParagraphStyle("job_header", fontName="Helvetica-Bold", fontSize=9,
                                     textColor=colors.black, spaceAfter=0),
        "job_meta": ParagraphStyle("job_meta", fontName="Helvetica-Oblique", fontSize=8.5,
                                   textColor=colors.HexColor("#555555"), spaceAfter=1),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=8.5,
                                 textColor=colors.HexColor("#222222"), spaceAfter=1.5,
                                 leftIndent=10),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.5,
                               textColor=colors.HexColor("#222222"), spaceAfter=2),
        "proj_header": ParagraphStyle("proj_header", fontName="Helvetica-Bold", fontSize=8.5,
                                      textColor=colors.black, spaceAfter=0),
        "proj_link": ParagraphStyle("proj_link", fontName="Helvetica", fontSize=8,
                                    textColor=colors.HexColor("#0066CC"), spaceAfter=0),
        "skills": ParagraphStyle("skills", fontName="Helvetica", fontSize=8.5,
                                 textColor=colors.HexColor("#222222"), spaceAfter=1.5),
    }


def divider():
    return HRFlowable(width="100%", thickness=0.5,
                      color=colors.HexColor("#AAAAAA"),
                      spaceAfter=3, spaceBefore=1)


def pick_projects(scored_job: dict) -> list:
    """Pick 4-5 best projects for this job from master list"""
    best = scored_job.get("best_projects", [])
    selected = []

    # try to match scorer picks to master list
    for pick in best:
        pick_name = pick.get("name", "").lower().replace("_", "-").replace(" ", "-")
        for proj_key in PROJECTS_MASTER:
            proj_lower = proj_key.lower().replace("_", "-")
            if pick_name in proj_lower or proj_lower in pick_name:
                if proj_key not in selected:
                    selected.append(proj_key)
                break

    # fill up to 5 with defaults if needed
    defaults = list(PROJECTS_MASTER.keys())
    for d in defaults:
        if len(selected) >= 5:
            break
        if d not in selected:
            selected.append(d)

    return selected[:5]


def build_resume_pdf(scored_job: dict, candidate_profile: dict, output_filename: str = None) -> str:
    """Build a tailored one-page PDF resume matching Rakib's original format"""

    if not output_filename:
        company = scored_job.get("company", "company").replace(" ", "_").replace("/", "_")
        title = scored_job.get("job_title", "role").replace(" ", "_").replace("/", "_")[:25]
        timestamp = datetime.now().strftime("%m%d")
        output_filename = f"resume_{company}_{title}_{timestamp}.pdf"

    output_path = OUTPUT_DIR / output_filename
    styles = build_styles()
    story = []

    # ── NAME ────────────────────────────────────────────────
    story.append(Paragraph(CANDIDATE["name"], styles["name"]))
    story.append(Paragraph(CANDIDATE["contacts"], styles["contact"]))
    story.append(Spacer(1, 3))

    # ── SUMMARY ─────────────────────────────────────────────
    story.append(Paragraph("SUMMARY", styles["section"]))
    story.append(divider())
    story.append(Paragraph(CANDIDATE["summary"], styles["body"]))

    # ── EDUCATION ───────────────────────────────────────────
    story.append(Paragraph("EDUCATION", styles["section"]))
    story.append(divider())
    story.append(Paragraph(
        "<b>Associate Degree in Computer Science</b> — Community College of Philadelphia, Philadelphia, PA",
        styles["body"]
    ))
    story.append(Paragraph("2023 – May 2026", styles["job_meta"]))

    # ── EXPERIENCE ──────────────────────────────────────────
    story.append(Paragraph("EXPERIENCE", styles["section"]))
    story.append(divider())
    for exp in CANDIDATE["experience"]:
        story.append(Paragraph(
            f'<b>{exp["title"]}</b> | {exp["company"]}',
            styles["job_header"]
        ))
        story.append(Paragraph(exp["duration"], styles["job_meta"]))
        for b in exp["bullets"]:
            story.append(Paragraph(f"• {b}", styles["bullet"]))

    # ── PROJECTS ────────────────────────────────────────────
    story.append(Paragraph("PROJECTS", styles["section"]))
    story.append(divider())

    selected_keys = pick_projects(scored_job)

    for key in selected_keys:
        proj = PROJECTS_MASTER[key]
        stack = proj["stack"]
        link = proj["link"]
        bullets = proj["bullets"]

        # project title line — matches original format exactly
        story.append(Paragraph(
            f'<b>{key}</b> | <font size="8">{stack}</font> — '
            f'<font color="#0066CC" size="8">{link}</font>',
            styles["proj_header"]
        ))
        for b in bullets:
            story.append(Paragraph(f"• {b}", styles["bullet"]))

    # additional line
    story.append(Paragraph(
        "Additional: Consumer Credit Risk Prediction · 50+ ML projects on GitHub",
        styles["body"]
    ))

    # ── TECHNICAL SKILLS ────────────────────────────────────
    story.append(Paragraph("TECHNICAL SKILLS", styles["section"]))
    story.append(divider())
    for cat, val in CANDIDATE["skills"].items():
        story.append(Paragraph(f"<b>{cat}:</b> {val}", styles["skills"]))

    # ── TRAINING & LANGUAGES ────────────────────────────────
    story.append(Paragraph("TRAINING & LANGUAGES", styles["section"]))
    story.append(divider())
    story.append(Paragraph(f"Training: {CANDIDATE['training']}", styles["skills"]))
    story.append(Paragraph(f"Spoken: {CANDIDATE['languages']}", styles["skills"]))

    # ── BUILD ───────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch
    )
    doc.build(story)
    print(f"Resume built: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    from core.job_finder import find_all_jobs
    from core.resume_parser import get_candidate_profile
    from core.job_scorer import score_all_jobs

    print("Loading profile...")
    profile = get_candidate_profile()

    print("Finding jobs...")
    jobs = find_all_jobs(max_jobs=5)

    print("Scoring...")
    scored = score_all_jobs(jobs, profile, min_score=60)

    if scored:
        top = scored[0]
        print(f"\nBuilding resume for: {top['job_title']} at {top['company']}")
        path = build_resume_pdf(top, profile)
        print(f"Saved to: {path}")
    else:
        print("No jobs found.")
