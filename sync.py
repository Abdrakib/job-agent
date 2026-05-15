import requests
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "Abdrakib")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MONO_REPO = "AI_ML-Portfolio"
DATA_DIR = Path(__file__).parent / "data"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# ─── EXACT NAME OVERRIDES ───────────────────────────────────
# These always win — no keyword guessing for known repos.
# Add new repos here when you create them if auto-detection gets it wrong.
NAME_OVERRIDES = {
    "ai_datascience_agent": "AutoML / Data Science",
    "ai-datascience-agent": "AutoML / Data Science",
    "explainable_ml-pipeline-agent": "AutoML / Explainable AI",
    "explainable_ml_pipeline_agent": "AutoML / Explainable AI",
    "explainable-ml-pipeline-agent": "AutoML / Explainable AI",
    "ml-research-assistant": "AI Research Tools / Agentic AI",
    "visual-analyst-agent": "Computer Vision / Multimodal AI",
    "visual_analyst_agent": "Computer Vision / Multimodal AI",
    "brain-tumor-ai-app": "Medical AI / Computer Vision",
    "brain_tumor_ai_app": "Medical AI / Computer Vision",
    "credit-risk-predictor": "FinTech / Machine Learning",
    "credit_risk_predictor": "FinTech / Machine Learning",
    "gpt-from-scratch": "LLM Research / Deep Learning",
    "gpt_from_scratch": "LLM Research / Deep Learning",
    "speech-emotion-recognition": "Audio AI / Deep Learning",
    "speech_emotion_recognition": "Audio AI / Deep Learning",
    "ai-cs-tutor": "Education AI / NLP",
    "ai_cs_tutor": "Education AI / NLP",
    "rakib-ai-portfolio": "Portfolio / Frontend",
    "rakib_ai_portfolio": "Portfolio / Frontend",
    "ai_ml-portfolio": "ML / Deep Learning / Computer Vision / NLP",
    "ai_ml_portfolio": "ML / Deep Learning / Computer Vision / NLP",
    "mini_chatgbt_agent_with_connector-mcp-pluging": "Agentic AI / LLMs",
    "mini-chatgbt-agent-with-connector-mcp-pluging": "Agentic AI / LLMs",
}

# ─── TOPIC-BASED DOMAIN MAP ─────────────────────────────────
# If a repo has one of these GitHub topics, use this domain.
# Add topics to your repos on GitHub and sync picks them up automatically.
TOPIC_DOMAIN_MAP = {
    # Computer Vision
    "computer-vision": "Computer Vision",
    "object-detection": "Computer Vision",
    "image-classification": "Computer Vision",
    "opencv": "Computer Vision",
    "yolo": "Computer Vision",
    "grad-cam": "Medical AI / Computer Vision",
    "medical-imaging": "Medical AI / Computer Vision",
    "brain-tumor": "Medical AI / Computer Vision",
    # NLP / LLM
    "nlp": "NLP",
    "llm": "LLM / NLP",
    "transformers": "LLM / Deep Learning",
    "gpt2": "LLM Research / Deep Learning",
    "pretraining": "LLM Research / Deep Learning",
    "instruction-tuning": "LLM Research / Deep Learning",
    "arxiv": "AI Research Tools / Agentic AI",
    "rag": "NLP / RAG",
    "faiss": "NLP / RAG",
    "sentiment-analysis": "NLP",
    # Agentic AI
    "ai-agent": "Agentic AI",
    "tool-use": "Agentic AI / LLMs",
    "mcp": "Agentic AI / LLMs",
    "autonomous": "Agentic AI",
    # AutoML / MLOps
    "automl": "AutoML / Data Science",
    "shap": "AutoML / Explainable AI",
    "optuna": "AutoML / Explainable AI",
    "explainable-ai": "AutoML / Explainable AI",
    "mlops": "MLOps",
    # FinTech
    "fintech": "FinTech / Machine Learning",
    "credit-risk": "FinTech / Machine Learning",
    "fraud-detection": "FinTech / Machine Learning",
    "trading": "FinTech / Reinforcement Learning",
    "stock": "FinTech / Machine Learning",
    # Audio
    "audio": "Audio AI / Deep Learning",
    "speech": "Audio AI / Deep Learning",
    "emotion-recognition": "Audio AI / Deep Learning",
    "hubert": "Audio AI / Deep Learning",
    "audio-classification": "Audio AI / Deep Learning",
    # Reinforcement Learning — only explicit RL topics
    "reinforcement-learning": "Reinforcement Learning",
    "rl": "Reinforcement Learning",
    "gymnasium": "Reinforcement Learning",
    "ppo": "Reinforcement Learning",
    "dqn": "Reinforcement Learning",
    # Multimodal
    "multimodal": "Computer Vision / Multimodal AI",
    "google-gemini": "Computer Vision / Multimodal AI",
    # Deep Learning
    "deep-learning": "Deep Learning",
    "pytorch": "Deep Learning",
    "tensorflow": "Deep Learning",
    "neural-network": "Deep Learning",
    # Data Science
    "data-science": "Data Science",
    "data-analysis": "Data Science",
    "visualization": "Data Science",
    # Healthcare
    "healthcare": "Medical AI",
    "medical": "Medical AI",
    # Education
    "cs-education": "Education AI / NLP",
    "ai-tutor": "Education AI / NLP",
    # Full Stack / Web
    "fastapi": "Full Stack / Web",
    "react": "Full Stack / Web",
    "full-stack": "Full Stack / Web",
    # Portfolio
    "portfolio": "Portfolio / Frontend",
    "personal-website": "Portfolio / Frontend",
}

# ─── KEYWORD FALLBACK ───────────────────────────────────────
# Last resort if no topic match found.
# NOTE: "agent" is intentionally NOT in RL keywords.
KEYWORD_DOMAIN_MAP = {
    "Medical AI / Computer Vision": ["brain tumor", "mri", "pneumonia", "medical", "healthcare", "grad-cam"],
    "FinTech / Machine Learning": ["credit", "fraud", "stock", "trading", "finance", "fintech", "risk"],
    "Audio AI / Deep Learning": ["audio", "speech", "music", "sound", "emotion recognition", "hubert", "ravdess"],
    "Computer Vision": ["object detection", "face", "pose", "yolo", "opencv", "segmentation", "deepfake", "cartoonify"],
    "LLM Research / Deep Learning": ["gpt", "trained from scratch", "pretraining", "language model", "tinystories", "alpaca"],
    "AutoML / Explainable AI": ["shap", "explainab", "optuna", "automl", "hyperparameter"],
    "AutoML / Data Science": ["pipeline", "eda", "preprocessing", "data science", "csv", "ml pipeline"],
    "AI Research Tools / Agentic AI": ["research assistant", "arxiv", "paper", "leaderboard", "benchmark"],
    "Agentic AI / LLMs": ["tool use", "tool routing", "mcp", "connector", "plugin", "chatgpt", "mini chat"],
    "NLP / RAG": ["rag", "faiss", "retrieval", "semantic search", "vector"],
    "NLP": ["sentiment", "summariz", "text class", "fake news", "hate speech", "language translat", "recommendation"],
    "Reinforcement Learning": ["reinforcement learning", "reward", "policy gradient", "dqn", "ppo", "gymnasium"],
    "Deep Learning": ["neural network", "cnn", "rnn", "lstm", "backpropagation from scratch"],
    "Data Science": ["analytics", "visualization", "whatsapp", "rfm", "market basket", "customer segmentation"],
    "Full Stack / Web": ["fastapi", "react", "typescript", "vercel", "render", "deployed as full"],
    "Portfolio / Frontend": ["portfolio website", "personal website", "framer motion"],
    "Machine Learning": ["classification", "regression", "clustering", "decision tree", "random forest"],
}


def detect_domain(topics: list, description: str, name: str) -> str:
    """
    Three-layer domain detection:
    1. Exact name override (always wins)
    2. GitHub topic match
    3. Keyword fallback on description + name

    For new repos: add a specific GitHub topic and it auto-detects.
    For edge cases: add to NAME_OVERRIDES above.
    """
    name_lower = name.lower()

    # Layer 1 — exact name override
    for override_key, override_domain in NAME_OVERRIDES.items():
        if override_key in name_lower:
            return override_domain

    # Layer 2 — GitHub topic match (most reliable for new repos)
    for topic in topics:
        topic_lower = topic.lower()
        if topic_lower in TOPIC_DOMAIN_MAP:
            return TOPIC_DOMAIN_MAP[topic_lower]

    # Layer 3 — keyword fallback on description + name
    text = description.lower() + " " + name_lower
    for domain, keywords in KEYWORD_DOMAIN_MAP.items():
        if any(kw in text for kw in keywords):
            return domain

    return "Machine Learning"


def detect_stack(topics: list, language: str) -> list:
    """Build stack list from topics and language"""
    stack = []
    if language:
        stack.append(language)

    tech_map = {
        "pytorch": "PyTorch", "tensorflow": "TensorFlow", "keras": "Keras",
        "scikit-learn": "Scikit-learn", "pandas": "Pandas", "numpy": "NumPy",
        "fastapi": "FastAPI", "react": "React", "streamlit": "Streamlit",
        "gradio": "Gradio", "huggingface": "HuggingFace", "transformers": "Transformers",
        "opencv": "OpenCV", "yolo": "YOLO", "shap": "SHAP", "optuna": "Optuna",
        "xgboost": "XGBoost", "lightgbm": "LightGBM", "plotly": "Plotly",
        "typescript": "TypeScript", "docker": "Docker", "aws": "AWS",
        "qwen": "Qwen", "llama": "Llama", "claude-api": "Claude API",
        "google-gemini": "Gemini API", "faiss": "FAISS",
    }

    for topic in topics:
        for key, display in tech_map.items():
            if key in topic.lower() and display not in stack:
                stack.append(display)

    return stack[:8]


def detect_skills(topics: list, description: str) -> list:
    """Detect skills demonstrated"""
    skills = []
    text = " ".join(topics) + " " + description.lower()

    skill_map = {
        "LLM integration": ["llm", "gpt", "claude", "qwen", "llama", "language model"],
        "computer vision": ["vision", "yolo", "opencv", "cnn", "image"],
        "RAG pipeline": ["rag", "faiss", "retrieval", "semantic search"],
        "model deployment": ["deploy", "vercel", "render", "huggingface", "spaces", "zerogpu"],
        "AutoML pipeline": ["automl", "optuna", "shap", "pipeline", "eda"],
        "full-stack development": ["fastapi", "react", "typescript", "full-stack"],
        "deep learning": ["pytorch", "tensorflow", "neural", "cnn", "rnn"],
        "data analysis": ["pandas", "numpy", "visualization", "analytics"],
        "audio classification": ["audio", "speech", "hubert", "wav", "ravdess"],
        "reinforcement learning": ["reinforcement", "reward", "policy", "dqn", "ppo"],
        "agentic AI": ["agent", "tool use", "tool routing", "autonomous", "mcp"],
        "multimodal AI": ["multimodal", "gemini", "vision-language", "image understanding"],
    }

    for skill, keywords in skill_map.items():
        if any(kw in text for kw in keywords):
            skills.append(skill)

    return skills[:5]


def fetch_all_repos() -> list:
    """Fetch all public repos from GitHub"""
    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos"
    params = {"per_page": 100, "type": "public"}

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"GitHub API error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Failed to fetch repos: {e}")
        return []


def repo_to_project(repo: dict) -> dict:
    """Convert GitHub repo data to our project format"""
    topics = repo.get("topics", [])
    description = repo.get("description", "") or ""
    name = repo["name"]

    domain = detect_domain(topics, description, name)
    stack = detect_stack(topics, repo.get("language", ""))
    skills = detect_skills(topics, description)

    return {
        "name": name,
        "github_url": repo["html_url"],
        "live_demo": repo.get("homepage") or None,
        "domain": domain,
        "description": description,
        "stack": stack,
        "topics": topics,
        "skills_demonstrated": skills,
        "status": "complete" if not repo.get("archived") else "archived",
        "language": repo.get("language", "Python"),
        "last_updated": repo.get("updated_at", ""),
        "has_demo": bool(repo.get("homepage")),
        "stars": repo.get("stargazers_count", 0)
    }


def sync_github_projects():
    """Main sync — fetches all repos and updates repos.json"""
    print(f"Syncing GitHub repos for {GITHUB_USERNAME}...")

    repos = fetch_all_repos()
    print(f"Found {len(repos)} repos on GitHub")

    projects = []
    for repo in repos:
        if repo.get("fork"):
            continue

        project = repo_to_project(repo)
        projects.append(project)
        print(f"  Synced: {repo['name']} → {project['domain']}")

    # load existing repos.json to preserve manually entered data
    repos_path = DATA_DIR / "repos.json"
    existing_data = {"owner": GITHUB_USERNAME, "repositories": []}

    if repos_path.exists():
        with open(repos_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)

    existing_by_name = {r["name"]: r for r in existing_data.get("repositories", [])}

    # merge — GitHub data + preserve manual overrides
    merged = []
    for project in projects:
        name = project["name"]
        if name in existing_by_name:
            existing = existing_by_name[name]
            # preserve manually entered skills if they exist
            if existing.get("skills_demonstrated") and len(existing["skills_demonstrated"]) > len(project["skills_demonstrated"]):
                project["skills_demonstrated"] = existing["skills_demonstrated"]
            # preserve demo URL if GitHub homepage is empty
            if existing.get("live_demo") and not project["live_demo"]:
                project["live_demo"] = existing["live_demo"]
                project["has_demo"] = True

        merged.append(project)

    output = {
        "owner": GITHUB_USERNAME,
        "huggingface": "Abdourakib",
        "portfolio": "https://abdourakib.com",
        "github": f"https://github.com/{GITHUB_USERNAME}",
        "last_synced": datetime.now().isoformat(),
        "repositories": merged
    }

    with open(repos_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSync complete: {len(merged)} repos saved")
    print(f"Last synced: {output['last_synced']}")
    return merged


if __name__ == "__main__":
    synced = sync_github_projects()
    print(f"\nTotal: {len(synced)} repos")

    print("\nBy domain:")
    domains = {}
    for p in synced:
        d = p.get("domain", "Unknown")
        domains[d] = domains.get(d, 0) + 1
    for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        print(f"  {domain}: {count}")
