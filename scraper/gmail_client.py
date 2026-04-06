"""gmail_client.py — fetch unread supermarket leaflet PDFs from Gmail."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Sender addresses to look for leaflet emails from
DEFAULT_SENDERS = [
    "letak@tesco.cz",
    "newsletter@albert.cz",
    "letak@billa.cz",
    "letak@penny.cz",
    "letak@lidl.cz",
    "letak@kaufland.cz",
]


def _get_credentials(
    credentials_path: str | Path = "credentials.json",
    token_path: str | Path = "token.json",
) -> Credentials:
    """Load or refresh OAuth2 credentials, running the first-time flow if needed."""
    credentials_path = Path(credentials_path)
    token_path = Path(token_path)

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


def fetch_leaflet_pdfs(
    credentials_path: str | Path = "credentials.json",
    token_path: str | Path = "token.json",
    senders: list[str] | None = None,
    output_dir: str | Path | None = None,
) -> list[Path]:
    """Fetch unread leaflet PDF attachments from Gmail.

    Downloads PDFs from unread emails sent by the configured supermarket
    addresses, saves them to *output_dir* (a temp dir if None), marks the
    emails as read, and returns the list of saved file paths.

    Parameters
    ----------
    credentials_path:
        Path to the OAuth2 client secrets file.
    token_path:
        Path to the cached token file.
    senders:
        Sender email addresses to search. Defaults to DEFAULT_SENDERS.
    output_dir:
        Directory to save downloaded PDFs. A temporary directory is used
        when not specified.

    Returns
    -------
    list[Path]
        Paths to the downloaded PDF files.
    """
    if senders is None:
        senders = DEFAULT_SENDERS

    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="najdi-slevu-"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    creds = _get_credentials(credentials_path, token_path)
    service = build("gmail", "v1", credentials=creds)

    # Build Gmail query: unread messages from any of the sender addresses
    from_clauses = " OR ".join(f"from:{s}" for s in senders)
    query = f"is:unread has:attachment ({from_clauses})"

    messages_response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=50)
        .execute()
    )
    messages = messages_response.get("messages", [])

    saved_paths: list[Path] = []

    for msg_stub in messages:
        msg_id = msg_stub["id"]
        message = (
            service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        )

        pdf_found = False
        for part in _iter_parts(message.get("payload", {})):
            filename = part.get("filename", "")
            if not filename.lower().endswith(".pdf"):
                continue

            attachment_id = part.get("body", {}).get("attachmentId")
            if not attachment_id:
                # Data may be inline
                data = part.get("body", {}).get("data", "")
            else:
                att = (
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=msg_id, id=attachment_id)
                    .execute()
                )
                data = att.get("data", "")

            if not data:
                continue

            pdf_bytes = base64.urlsafe_b64decode(data)
            out_path = output_dir / f"{msg_id}_{filename}"
            out_path.write_bytes(pdf_bytes)
            saved_paths.append(out_path)
            pdf_found = True

        if pdf_found:
            # Mark email as read
            service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()

    return saved_paths


def _iter_parts(payload: dict) -> list[dict]:
    """Recursively collect all message parts from a Gmail payload."""
    parts = []
    if "parts" in payload:
        for part in payload["parts"]:
            parts.extend(_iter_parts(part))
    else:
        parts.append(payload)
    return parts
