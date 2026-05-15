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
    """
    Send raw resume text to Claude and get back structured data.
    This becomes the candidate DNA used across all applications.
    """
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

    # clean up any accidental markdown
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def get_candidate_profile() -> dict:
    """
    Main function — returns the full candidate profile.
    Combines parsed resume + metadata for the agent to use.
    """
    pdf_path = DATA_DIR / "base_resume.pdf"

    if not pdf_path.exists():
        raise FileNotFoundError(f"Resume not found at {pdf_path}")

    print("Extracting text from resume...")
    raw_text = extract_text_from_pdf(pdf_path)

    print("Parsing resume with Claude...")
    parsed = parse_resume_with_claude(raw_text)

    # add extra metadata the agent needs
    parsed["raw_text"] = raw_text
    parsed["total_projects"] = 45
    parsed["github_username"] = "Abdrakib"
    parsed["huggingface_username"] = "Abdourakib"

    print(f"Resume parsed successfully for: {parsed.get('name', 'Unknown')}")
    return parsed


if __name__ == "__main__":
    profile = get_candidate_profile()
    print("\n--- CANDIDATE PROFILE ---")
    print(f"Name: {profile['name']}")
    print(f"Email: {profile['email']}")
    print(f"Phone: {profile['phone']}")
    print(f"Education: {profile['education'][0]['degree']} at {profile['education'][0]['school']}")
    print(f"Skills: {', '.join(profile['skills']['ml_ai'][:5])}")
    print(f"Experience: {profile['experience'][0]['title']} at {profile['experience'][0]['company']}")
    print("\nFull profile ready for agent use.")
