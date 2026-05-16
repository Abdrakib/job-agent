import fitz  # pymupdf
import anthropic
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from PDF resume"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


def parse_resume_with_claude(raw_text: str) -> dict:
    """Send raw resume text to Claude and get back structured data."""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": f"""Parse this resume and return ONLY a JSON object with no extra text or markdown.

Resume:
{raw_text}

Return this exact JSON structure:
{{
    "name": "full name",
    "email": "email address",
    "phone": "phone number",
    "github": "github URL",
    "huggingface": "huggingface URL",
    "portfolio": "portfolio URL",
    "linkedin": "linkedin URL",
    "summary": "professional summary",
    "education": [
        {{
            "degree": "degree name",
            "school": "school name",
            "location": "city, state",
            "graduation": "graduation date"
        }}
    ],
    "experience": [
        {{
            "title": "job title",
            "company": "company name",
            "duration": "date range",
            "location": "location",
            "bullets": ["bullet 1", "bullet 2"]
        }}
    ],
    "skills": {{
        "languages": ["Python", "SQL"],
        "ml_ai": ["PyTorch", "TensorFlow"],
        "specializations": ["LLMs", "Computer Vision"],
        "tools": ["FastAPI", "Gradio"]
    }},
    "certifications": ["cert 1", "cert 2"],
    "languages_spoken": ["English", "French"]
}}"""
            }
        ]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)


def _hardcoded_profile() -> dict:
    """
    Hardcoded candidate profile for Abdou Rakib Abente.
    Used when base_resume.pdf is not available (e.g. on Railway).
    Keep this up to date if your resume changes.
    """
    return {
        "name": "Abdou Rakib Abente",
        "email": "Rakibabente8@gmail.com",
        "phone": "",
        "github": "https://github.com/Abdrakib",
        "huggingface": "https://huggingface.co/Abdourakib",
        "portfolio": "https://abdourakib.com",
        "linkedin": "",
        "summary": (
            "AI/ML Engineer and recent Computer Science graduate (Community College of Philadelphia, May 2026) "
            "with hands-on experience in LLMs, computer vision, reinforcement learning, and autonomous agents. "
            "Built 50+ ML projects deployed on HuggingFace and GitHub. Completed ML internship at Buildawn Labs "
            "working on computer vision, LLMs, and RL. Passionate about building production-ready AI systems."
        ),
        "education": [
            {
                "degree": "Associate of Science in Computer Science",
                "school": "Community College of Philadelphia",
                "location": "Philadelphia, PA",
                "graduation": "May 2026"
            }
        ],
        "experience": [
            {
                "title": "Machine Learning Intern",
                "company": "Buildawn Labs",
                "duration": "Nov 2025 – Jan 2026",
                "location": "Remote",
                "bullets": [
                    "Developed computer vision pipelines for real-time object detection",
                    "Fine-tuned LLMs for domain-specific tasks using LoRA and PEFT",
                    "Implemented reinforcement learning agents for sequential decision-making",
                    "Deployed models to production using FastAPI and Docker"
                ]
            },
            {
                "title": "Direct Support Professional",
                "company": "Current Employer",
                "duration": "2024 – Present",
                "location": "Philadelphia, PA",
                "bullets": [
                    "Provide individualized support and care coordination",
                    "Demonstrate reliability, communication, and accountability"
                ]
            }
        ],
        "skills": {
            "languages": ["Python", "SQL", "JavaScript", "Java", "C++"],
            "ml_ai": [
                "PyTorch", "TensorFlow", "Scikit-learn", "HuggingFace Transformers",
                "LangChain", "OpenAI API", "Anthropic Claude API", "PEFT", "LoRA",
                "Optuna", "SHAP", "XGBoost", "LightGBM"
            ],
            "specializations": [
                "Large Language Models", "Computer Vision", "Reinforcement Learning",
                "Natural Language Processing", "Autonomous Agents", "RAG",
                "Generative AI", "Fine-tuning", "Model Deployment"
            ],
            "tools": [
                "FastAPI", "Gradio", "Streamlit", "Docker", "Git", "AWS S3",
                "HuggingFace Spaces", "ZeroGPU", "Jupyter", "VS Code", "Cursor"
            ]
        },
        "certifications": [],
        "languages_spoken": ["English", "French", "Wolof"],
        "raw_text": "",
        "total_projects": 50,
        "github_username": "Abdrakib",
        "huggingface_username": "Abdourakib"
    }


def get_candidate_profile() -> dict:
    """
    Main function — returns the full candidate profile.
    Tries to parse base_resume.pdf if it exists.
    Falls back to hardcoded profile (used on Railway / production).
    """
    pdf_path = DATA_DIR / "base_resume.pdf"

    if pdf_path.exists():
        print("Found base_resume.pdf — parsing with Claude...")
        try:
            raw_text = extract_text_from_pdf(pdf_path)
            parsed = parse_resume_with_claude(raw_text)
            parsed["raw_text"] = raw_text
            parsed["total_projects"] = 50
            parsed["github_username"] = "Abdrakib"
            parsed["huggingface_username"] = "Abdourakib"
            print(f"Resume parsed successfully for: {parsed.get('name', 'Unknown')}")
            return parsed
        except Exception as e:
            print(f"PDF parsing failed ({e}), falling back to hardcoded profile...")

    print("Using hardcoded candidate profile (no PDF found)")
    return _hardcoded_profile()


if __name__ == "__main__":
    profile = get_candidate_profile()
    print("\n--- CANDIDATE PROFILE ---")
    print(f"Name: {profile['name']}")
    print(f"Email: {profile['email']}")
    print(f"GitHub: {profile['github']}")
    print(f"Education: {profile['education'][0]['degree']} at {profile['education'][0]['school']}")
    print(f"ML Skills: {', '.join(profile['skills']['ml_ai'][:5])}")
    print(f"Experience: {profile['experience'][0]['title']} at {profile['experience'][0]['company']}")
    print(f"Total projects: {profile['total_projects']}")
    print("\nFull profile ready for agent use.")
