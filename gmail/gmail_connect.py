import os
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
TOKEN_FILE = DATA_DIR / "gmail_token.pickle"
CREDENTIALS_FILE = DATA_DIR / "gmail_credentials.json"

# Scopes we need from Gmail
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send"
]

# Gmail labels we create for job applications
JOB_LABELS = {
    "PARENT": "Job Applications",
    "INTERVIEW": "Job Applications/Interview Requests",
    "CONFIRMATION": "Job Applications/Confirmations",
    "REJECTION": "Job Applications/Rejections",
    "FOLLOW_UP": "Job Applications/Follow Up Needed",
    "HUMAN_REPLY": "Job Applications/Human Replies"
}

# Label colors
LABEL_COLORS = {}


def get_gmail_service():
    """
    Authenticate with Gmail and return service object.
    First run opens browser for OAuth consent.
    Subsequent runs use saved token.
    """
    creds = None

    # load saved token if exists
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    # refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing Gmail token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at {CREDENTIALS_FILE}\n"
                    "Download from Google Cloud Console and save as gmail_credentials.json"
                )
            print("Opening browser for Gmail authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=8080)

        # save token for next time
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        print("Gmail token saved.")

    service = build("gmail", "v1", credentials=creds)
    print("Gmail connected successfully.")
    return service


def get_or_create_label(service, label_name: str, colors: dict = None) -> str:
    """Get existing label ID or create new label. Returns label ID."""
    # get all existing labels
    results = service.users().labels().list(userId="me").execute()
    existing = {l["name"]: l["id"] for l in results.get("labels", [])}

    if label_name in existing:
        return existing[label_name]

    # create new label
    label_body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }
    if colors:
        label_body["color"] = colors

    created = service.users().labels().create(
        userId="me", body=label_body
    ).execute()

    print(f"  Created label: {label_name}")
    return created["id"]


def setup_job_labels(service) -> dict:
    """
    Create all job application labels in Gmail.
    Returns dict of label_key -> label_id
    """
    print("Setting up Gmail labels...")
    label_ids = {}

    for key, label_name in JOB_LABELS.items():
        color = LABEL_COLORS.get(key)
        label_id = get_or_create_label(service, label_name, color)
        label_ids[key] = label_id

    print(f"Labels ready: {len(label_ids)} labels configured")
    return label_ids


def apply_label(service, message_id: str, label_id: str):
    """Apply a label to a Gmail message"""
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]}
    ).execute()


def get_recent_emails(service, max_results: int = 50, query: str = "") -> list:
    """Fetch recent emails matching a query"""
    if not query:
        query = "in:inbox newer_than:1d"

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        email = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()
        emails.append(email)

    return emails


def extract_email_content(email: dict) -> dict:
    """Extract readable content from Gmail message object"""
    headers = {h["name"]: h["value"] for h in email["payload"]["headers"]}

    # get body text
    body = ""
    payload = email["payload"]

    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                import base64
                data = part["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                break
    else:
        import base64
        data = payload["body"].get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return {
        "id": email["id"],
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body": body[:2000],
        "snippet": email.get("snippet", "")
    }


if __name__ == "__main__":
    print("Testing Gmail connection...")
    service = get_gmail_service()
    label_ids = setup_job_labels(service)
    print("\nAll labels created:")
    for key, lid in label_ids.items():
        print(f"  {key}: {JOB_LABELS[key]} (id: {lid})")
    print("\nGmail setup complete.")
