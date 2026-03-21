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
from .._pagination import PageIterator
from .models import Draft, Label, Message, MessageList, Thread


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

        message: MIMEBase
        if attachments:
            msg_mp = MIMEMultipart()
            msg_mp.attach(
                MIMEText(body, "html" if html else "plain")
            )
            for attachment_path in attachments:
                attachment_path = Path(attachment_path)
                with open(attachment_path, "rb") as f:
                    part = MIMEBase(
                        "application", "octet-stream"
                    )
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment_path.name,
                )
                msg_mp.attach(part)
            message = msg_mp
        else:
            message = MIMEText(
                body, "html" if html else "plain"
            )

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
    ) -> PageIterator[Message]:
        """List messages with automatic pagination.

        Returns a ``PageIterator`` that yields ``Message`` objects::

            for msg in google.gmail.list_messages(query="is:unread"):
                print(msg.id)
        """
        def fetch_page(page_token: str | None) -> dict[str, Any]:
            kwargs: dict[str, Any] = {"userId": "me", "maxResults": max_results}
            if query:
                kwargs["q"] = query
            if label_ids:
                kwargs["labelIds"] = label_ids
            if page_token:
                kwargs["pageToken"] = page_token
            request = (
                self._resource.users().messages().list(**kwargs)
            )
            result: dict[str, Any] = (
                self._execute_request(request)
            )
            return result

        return PageIterator(
            fetch_page,
            items_key="messages",
            model_class=Message,
        )

    def list_messages_page(
        self,
        query: str | None = None,
        label_ids: list[str] | None = None,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> MessageList:
        """List a single page of messages."""
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
        return [
            Label.from_api_response(lbl)
            for lbl in result.get("labels", [])
        ]

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

    # ------------------------------------------------------------------
    # Drafts
    # ------------------------------------------------------------------

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
    ) -> Draft:
        """Create a new draft email."""
        message = MIMEText(body, "html" if html else "plain")
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        request = self._resource.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        )
        result = self._execute_request(request)
        return Draft.from_api_response(result)

    def list_drafts(self, max_results: int = 100) -> list[Draft]:
        """List drafts in the mailbox."""
        request = self._resource.users().drafts().list(
            userId="me", maxResults=max_results
        )
        result = self._execute_request(request)
        return [
            Draft.from_api_response(d)
            for d in result.get("drafts", [])
        ]

    def send_draft(self, draft_id: str) -> Message:
        """Send an existing draft."""
        request = self._resource.users().drafts().send(
            userId="me", body={"id": draft_id}
        )
        result = self._execute_request(request)
        return Message.from_api_response(result)

    # ------------------------------------------------------------------
    # Attachments / Convenience
    # ------------------------------------------------------------------

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Get the raw data of a message attachment."""
        request = self._resource.users().messages().attachments().get(
            userId="me", messageId=message_id, id=attachment_id
        )
        result = self._execute_request(request)
        data = result.get("data", "")
        return base64.urlsafe_b64decode(data)

    def mark_read(self, message_id: str) -> Message:
        """Mark a message as read by removing the UNREAD label."""
        return self.modify_message(message_id, remove_labels=["UNREAD"])

    def mark_unread(self, message_id: str) -> Message:
        """Mark a message as unread by adding the UNREAD label."""
        return self.modify_message(message_id, add_labels=["UNREAD"])

    def reply(
        self,
        message_id: str,
        body: str,
        html: bool = False,
    ) -> Message:
        """Reply to a message, preserving the thread.

        Fetches the original message to extract the thread ID, subject,
        and sender, then sends a reply within the same thread.
        """
        original = self.get_message(message_id)
        thread_id = original.thread_id

        # Extract headers from the original message payload
        headers = {
            h["name"].lower(): h["value"]
            for h in original.payload.get("headers", [])
        }
        original_subject = headers.get("subject", "")
        reply_to = headers.get("reply-to") or headers.get("from", "")

        subject = original_subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        message = MIMEText(body, "html" if html else "plain")
        message["to"] = reply_to
        message["subject"] = subject
        message["In-Reply-To"] = headers.get("message-id", "")
        message["References"] = headers.get("message-id", "")

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        request = self._resource.users().messages().send(
            userId="me", body={"raw": raw, "threadId": thread_id}
        )
        result = self._execute_request(request)
        return Message.from_api_response(result)
