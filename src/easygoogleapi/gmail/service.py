"""Gmail API wrapper."""

import base64
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any

from .._base import BaseService
from .models import Label, Message, MessageList, Thread


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
        from_name: str | None = None,
        reply_to: str | None = None,
    ) -> Message:
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
                    "attachment",
                    filename=attachment_path.name,
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
        if from_name:
            message["from"] = formataddr((from_name, ""))
        if reply_to:
            message["reply-to"] = reply_to

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        request = self._resource.users().messages().send(
            userId="me", body={"raw": raw}
        )
        result = self._execute_request(request)
        return Message.from_api_response(result)

    def list_messages(
        self,
        query: str | None = None,
        label_ids: list[str] | None = None,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> MessageList:
        """List messages matching criteria."""
        kwargs: dict[str, Any] = {"userId": "me", "maxResults": max_results}
        if query:
            kwargs["q"] = query
        if label_ids:
            kwargs["labelIds"] = label_ids
        if page_token:
            kwargs["pageToken"] = page_token

        request = self._resource.users().messages().list(**kwargs)
        result = self._execute_request(request)
        return MessageList.from_api_response(result)

    def get_message(
        self, message_id: str, format: str = "full"
    ) -> Message:
        """Get a specific message by ID."""
        request = self._resource.users().messages().get(
            userId="me", id=message_id, format=format
        )
        result = self._execute_request(request)
        return Message.from_api_response(result)

    def list_labels(self) -> list[Label]:
        """List all labels."""
        request = self._resource.users().labels().list(userId="me")
        result = self._execute_request(request)
        return [Label.from_api_response(l) for l in result.get("labels", [])]

    def trash_message(self, message_id: str) -> Message:
        """Move a message to trash."""
        request = self._resource.users().messages().trash(
            userId="me", id=message_id
        )
        result = self._execute_request(request)
        return Message.from_api_response(result)

    def modify_message(
        self,
        message_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> Message:
        """Modify labels on a message."""
        body: dict[str, Any] = {}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels
        request = self._resource.users().messages().modify(
            userId="me", id=message_id, body=body
        )
        result = self._execute_request(request)
        return Message.from_api_response(result)

    def get_thread(
        self, thread_id: str, format: str = "full"
    ) -> Thread:
        """Get a thread (all messages in a conversation)."""
        request = self._resource.users().threads().get(
            userId="me", id=thread_id, format=format
        )
        result = self._execute_request(request)
        return Thread.from_api_response(result)
