from dotenv import load_dotenv
from gmail.gmail_connect import (
    get_gmail_service,
    setup_job_labels,
    apply_label,
    get_recent_emails,
    extract_email_content,
    JOB_LABELS,
)

load_dotenv()

# Email classification types
EMAIL_TYPES = {
    "INTERVIEW_REQUEST": "Company wants to schedule an interview or call",
    "HUMAN_REPLY": "A real human replied (not automated)",
    "CONFIRMATION": "Automated application confirmation",
    "REJECTION": "Application rejected",
    "FOLLOW_UP_NEEDED": "No reply in 7+ days, follow up recommended",
    "IRRELEVANT": "Not related to job applications",
}


def classify_email(email_content: dict) -> dict:
    """Classify email using keywords — no API needed"""
    subject = email_content.get("subject", "").lower()
    body = email_content.get("body", "").lower()
    sender = email_content.get("from", "").lower()
    text = subject + " " + body

    # Interview signals
    if any(w in text for w in ["interview", "schedule", "call", "meet", "zoom", "teams", "calendly"]):
        return {"type": "INTERVIEW_REQUEST", "confidence": 85,
                "company": sender.split("@")[-1].split(".")[0],
                "role": "", "action_needed": "Schedule the interview", "urgent": True}

    # Rejection signals
    if any(w in text for w in ["unfortunately", "not moving forward", "other candidates",
                                "position has been filled", "not selected", "regret to inform"]):
        return {"type": "REJECTION", "confidence": 90,
                "company": sender.split("@")[-1].split(".")[0],
                "role": "", "action_needed": "Note rejection, keep applying", "urgent": False}

    # Confirmation signals
    if any(w in text for w in ["received your application", "thank you for applying",
                                "application received", "we received", "successfully submitted"]):
        return {"type": "CONFIRMATION", "confidence": 85,
                "company": sender.split("@")[-1].split(".")[0],
                "role": "", "action_needed": "Wait for response", "urgent": False}

    # Human reply signals
    if any(w in text for w in ["wanted to reach out", "following up", "saw your application",
                                "impressed", "would love to"]):
        return {"type": "HUMAN_REPLY", "confidence": 75,
                "company": sender.split("@")[-1].split(".")[0],
                "role": "", "action_needed": "Reply promptly", "urgent": True}

    return {"type": "IRRELEVANT", "confidence": 95,
            "company": "", "role": "", "action_needed": "", "urgent": False}


def send_notification(subject: str, message: str, service):
    """Send email notification to yourself via Gmail"""
    import base64
    from email.mime.text import MIMEText

    msg = MIMEText(message)
    msg["to"] = "Rakibabente8@gmail.com"
    msg["from"] = "Rakibabente8@gmail.com"
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId="me",
        body={"raw": raw}
    ).execute()
    print(f"Notification sent: {subject}")


def build_sms_message(classification: dict, email_content: dict) -> str:
    """Build a concise SMS message based on email classification"""
    email_type = classification.get("type")
    company = classification.get("company", "Unknown Company")
    role = classification.get("role", "Unknown Role")
    action = classification.get("action_needed", "Check your email")

    if email_type == "INTERVIEW_REQUEST":
        return (
            f"🎉 INTERVIEW REQUEST\n"
            f"Company: {company}\n"
            f"Role: {role}\n"
            f"Action: {action}\n"
            f"Check Gmail: Job Applications/Interview Requests"
        )
    elif email_type == "HUMAN_REPLY":
        return (
            f"💬 HUMAN REPLY\n"
            f"From: {company}\n"
            f"Subject: {email_content['subject'][:50]}\n"
            f"Action: {action}"
        )
    elif email_type == "REJECTION":
        return (
            f"❌ Rejection from {company}\n"
            f"Role: {role}\n"
            f"Moved to rejections folder."
        )
    return None


def process_inbox(notify_types: list = None) -> dict:
    """
    Main function — reads inbox, classifies emails, applies labels, sends email notifications.
    notify_types: which email types trigger a self-email. Default: interview + human reply only.
    """
    if notify_types is None:
        notify_types = ["INTERVIEW_REQUEST", "HUMAN_REPLY"]

    print("Connecting to Gmail...")
    service = get_gmail_service()
    label_ids = setup_job_labels(service)

    print("Fetching recent emails...")
    emails = get_recent_emails(service, max_results=20)
    print(f"Found {len(emails)} emails to process\n")

    results = {
        "processed": 0,
        "interview_requests": 0,
        "human_replies": 0,
        "confirmations": 0,
        "rejections": 0,
        "notifications_sent": 0,
        "errors": 0,
    }

    for email in emails:
        try:
            content = extract_email_content(email)
            print(f"Processing: {content['subject'][:60]}...")

            # keyword-based classification
            classification = classify_email(content)
            email_type = classification.get("type", "IRRELEVANT")
            confidence = classification.get("confidence", 0)

            print(f"  Type: {email_type} (confidence: {confidence}%)")

            # apply Gmail label
            label_map = {
                "INTERVIEW_REQUEST": "INTERVIEW",
                "HUMAN_REPLY": "HUMAN_REPLY",
                "CONFIRMATION": "CONFIRMATION",
                "REJECTION": "REJECTION",
                "FOLLOW_UP_NEEDED": "FOLLOW_UP",
            }

            if email_type in label_map and confidence >= 70:
                label_key = label_map[email_type]
                label_id = label_ids.get(label_key)
                if label_id:
                    apply_label(service, content["id"], label_id)
                    print(f"  Labeled: {JOB_LABELS[label_key]}")

            # email self for important matches
            if email_type in notify_types and confidence >= 75:
                body = build_sms_message(classification, content)
                if body:
                    subject = f"[Job Agent] {email_type.replace('_', ' ')}"
                    try:
                        send_notification(subject, body, service)
                        results["notifications_sent"] += 1
                    except Exception as e:
                        print(f"  Notification failed: {e}")

            # update counts
            type_counts = {
                "INTERVIEW_REQUEST": "interview_requests",
                "HUMAN_REPLY": "human_replies",
                "CONFIRMATION": "confirmations",
                "REJECTION": "rejections",
            }
            if email_type in type_counts:
                results[type_counts[email_type]] += 1

            results["processed"] += 1

        except Exception as e:
            print(f"  Error processing email: {e}")
            results["errors"] += 1

    print(f"\n--- INBOX PROCESSING COMPLETE ---")
    print(f"Processed: {results['processed']} emails")
    print(f"Interview Requests: {results['interview_requests']}")
    print(f"Human Replies: {results['human_replies']}")
    print(f"Confirmations: {results['confirmations']}")
    print(f"Rejections: {results['rejections']}")
    print(f"Notifications sent: {results['notifications_sent']}")

    return results


def send_test_sms():
    """Send a test self-email via Gmail to verify notifications work."""
    message = (
        "✅ Job Agent Active\n"
        "Your job application agent is connected and monitoring your inbox.\n"
        "You'll receive alerts for interview requests and important replies."
    )
    print("Sending test notification...")
    service = get_gmail_service()
    try:
        send_notification("Job Agent: test", message, service)
        print("Test notification sent successfully! Check your inbox.")
    except Exception as e:
        print(f"Notification failed: {e}")


if __name__ == "__main__":
    print("Testing email notification...")
    send_test_sms()

    print("\nTesting Gmail inbox monitoring...")
    results = process_inbox()
