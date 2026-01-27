"""Gmail API wrapper."""

import base64
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from .._base import BaseService


class GmailService(BaseService):
    """Wrapper for Gmail API operations."""

    def send(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html: bool = False,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[str | Path] | None = None,
    ) -> dict[str, Any]:
        """Send an email."""
        if isinstance(to, list):
            to = ", ".join(to)

        if attachments:
            message = MIMEMultipart()
            message.attach(
                MIMEText(body, "html" if html else "plain")
            )
            for attachment_path in attachments:
                attachment_path = Path(attachment_path)
                with open(attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment_path.name}",
                )
                message.attach(part)
        else:
            message = MIMEText(body, "html" if html else "plain")

        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc if isinstance(cc, str) else ", ".join(cc)
        if bcc:
            message["bcc"] = bcc if isinstance(bcc, str) else ", ".join(bcc)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        request = self._resource.users().messages().send(
            userId="me", body={"raw": raw}
        )
        return self._execute_request(request)

    def list_messages(
        self,
        query: str | None = None,
        label_ids: list[str] | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """List messages matching criteria."""
        kwargs: dict[str, Any] = {"userId": "me", "maxResults": max_results}
        if query:
            kwargs["q"] = query
        if label_ids:
            kwargs["labelIds"] = label_ids

        request = self._resource.users().messages().list(**kwargs)
        result = self._execute_request(request)
        return result.get("messages", [])

    def get_message(
        self, message_id: str, format: str = "full"
    ) -> dict[str, Any]:
        """Get a specific message by ID."""
        request = self._resource.users().messages().get(
            userId="me", id=message_id, format=format
        )
        return self._execute_request(request)

    def list_labels(self) -> list[dict[str, Any]]:
        """List all labels."""
        request = self._resource.users().labels().list(userId="me")
        result = self._execute_request(request)
        return result.get("labels", [])

    def trash_message(self, message_id: str) -> dict[str, Any]:
        """Move a message to trash."""
        request = self._resource.users().messages().trash(
            userId="me", id=message_id
        )
        return self._execute_request(request)
