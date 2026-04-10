"""gmail_client.py — fetch unread supermarket leaflet PDFs from Gmail."""

from __future__ import annotations

import base64
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

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

# HTTP status codes considered transient (safe to retry once)
_TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}


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


def _retry_once(fn, *args, **kwargs):
    """Call *fn* with *args*/*kwargs*, retrying once on transient HTTP errors.

    Sleeps 2 seconds before the retry. Non-transient errors are re-raised
    immediately.
    """
    try:
        return fn(*args, **kwargs)
    except HttpError as exc:
        if exc.status_code in _TRANSIENT_HTTP_CODES:
            logger.warning(
                "Transient HTTP %d from Gmail API — retrying in 2 s …",
                exc.status_code,
            )
            time.sleep(2)
            return fn(*args, **kwargs)
        raise


def _extract_sender(message: dict) -> Optional[str]:
    """Return the 'From' header value from a Gmail message, or None."""
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == "from":
            return h.get("value", "").lower()
    return None


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

    Transient Gmail API errors (429, 5xx) are retried once. Non-PDF
    attachments are skipped. Senders that produced zero downloaded PDFs are
    logged as a warning.

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

    messages_response = _retry_once(
        service.users().messages().list(userId="me", q=query, maxResults=50).execute
    )
    messages = messages_response.get("messages", [])
    logger.info("Found %d unread leaflet message(s).", len(messages))

    saved_paths: list[Path] = []
    # Track which senders produced at least one downloaded PDF
    senders_with_pdf: set[str] = set()

    for msg_stub in messages:
        msg_id = msg_stub["id"]
        try:
            message = _retry_once(
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute
            )
        except HttpError as exc:
            logger.error("Failed to fetch message %s: %s", msg_id, exc)
            continue

        sender = _extract_sender(message)

        pdf_found = False
        for part in _iter_parts(message.get("payload", {})):
            filename = part.get("filename", "")
            if not filename:
                continue  # Skip parts with no filename
            if not filename.lower().endswith(".pdf"):
                logger.debug(
                    "Skipping non-PDF attachment '%s' in message %s", filename, msg_id
                )
                continue

            attachment_id = part.get("body", {}).get("attachmentId")
            if not attachment_id:
                # Data may be inline
                data = part.get("body", {}).get("data", "")
            else:
                try:
                    att = _retry_once(
                        service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=msg_id, id=attachment_id)
                        .execute
                    )
                    data = att.get("data", "")
                except HttpError as exc:
                    logger.error(
                        "Failed to fetch attachment %s from message %s: %s",
                        attachment_id,
                        msg_id,
                        exc,
                    )
                    continue

            if not data:
                logger.warning(
                    "Empty attachment data for '%s' in message %s — skipping",
                    filename,
                    msg_id,
                )
                continue

            try:
                pdf_bytes = base64.urlsafe_b64decode(data)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to decode attachment '%s' in message %s: %s",
                    filename,
                    msg_id,
                    exc,
                )
                continue

            out_path = output_dir / f"{msg_id}_{filename}"
            out_path.write_bytes(pdf_bytes)
            saved_paths.append(out_path)
            pdf_found = True
            if sender:
                senders_with_pdf.add(sender)

        if pdf_found:
            # Mark email as read
            try:
                _retry_once(
                    service.users()
                    .messages()
                    .modify(
                        userId="me",
                        id=msg_id,
                        body={"removeLabelIds": ["UNREAD"]},
                    )
                    .execute
                )
            except HttpError as exc:
                logger.warning(
                    "Could not mark message %s as read: %s", msg_id, exc
                )

    # Warn about senders that produced no PDFs despite having matching messages
    if messages:
        for s in senders:
            matched = any(s in found for found in senders_with_pdf)
            if not matched:
                logger.warning(
                    "Sender %s matched query but produced zero downloadable PDFs.", s
                )

    logger.info("Downloaded %d PDF(s) total.", len(saved_paths))
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
