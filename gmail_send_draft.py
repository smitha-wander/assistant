"""
Find today's Daily Briefing draft and send it, with a recipient safety check.

Usage:
    python3 gmail_send_draft.py

Automatically searches for a draft with today's date in the subject line,
e.g. "Daily Briefing - Tuesday, May 5, 2026". Only sends if the draft is
addressed to smitha@wander.com.
"""

import os
import sys
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.json")
ALLOWED_RECIPIENT = "smitha@wander.com"


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def get_todays_subject():
    today = datetime.now()
    return f"Daily Briefing - {today.strftime('%A, %B %-d, %Y')}"


def find_draft(service, subject):
    results = service.users().drafts().list(userId="me", q=f"subject:{subject}").execute()
    drafts = results.get("drafts", [])
    for draft in drafts:
        full = service.users().drafts().get(userId="me", id=draft["id"], format="metadata").execute()
        headers = full["message"].get("payload", {}).get("headers", [])
        header_map = {h["name"].lower(): h["value"] for h in headers}
        subject_match = subject.lower() in header_map.get("subject", "").lower()
        recipient = header_map.get("to", "")
        if not subject_match:
            continue
        if ALLOWED_RECIPIENT.lower() not in recipient.lower():
            print(f"Blocked: draft recipient '{recipient}' is not {ALLOWED_RECIPIENT}. Skipping.")
            return None
        return draft["id"]
    return None


def main():
    subject = get_todays_subject()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Looking for draft: {subject}")

    service = get_gmail_service()
    draft_id = find_draft(service, subject)

    if not draft_id:
        print("No matching draft found. Nothing sent.")
        sys.exit(0)

    result = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
    print(f"Sent! Message ID: {result.get('id')}")


if __name__ == "__main__":
    main()
