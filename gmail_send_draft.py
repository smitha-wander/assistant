"""
Send a Gmail draft by subject line using the Gmail API.

Usage:
    python gmail_send_draft.py "Daily Briefing - Tuesday, May 5, 2026"

First run will open a browser for OAuth authentication and save a token.json.
"""

import sys
import os
import json
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


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


def find_draft_by_subject(service, subject):
    results = service.users().drafts().list(userId="me", q=f"subject:{subject}").execute()
    drafts = results.get("drafts", [])
    if not drafts:
        return None
    # Fetch full draft details to confirm subject match
    for draft in drafts:
        full = service.users().drafts().get(userId="me", id=draft["id"], format="metadata").execute()
        headers = full["message"].get("payload", {}).get("headers", [])
        for h in headers:
            if h["name"].lower() == "subject" and subject.lower() in h["value"].lower():
                return draft["id"]
    return None


def send_draft(service, draft_id):
    result = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python gmail_send_draft.py \"<email subject>\"")
        sys.exit(1)

    subject = sys.argv[1]
    print(f"Looking for draft with subject: {subject}")

    service = get_gmail_service()
    draft_id = find_draft_by_subject(service, subject)

    if not draft_id:
        print(f"No draft found matching subject: {subject}")
        sys.exit(1)

    print(f"Found draft (id: {draft_id}). Sending...")
    result = send_draft(service, draft_id)
    print(f"Sent! Message ID: {result.get('id')}")


if __name__ == "__main__":
    main()
