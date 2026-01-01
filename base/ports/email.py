from typing import Any, Protocol

from exc import Result


class AbsEmailSender(Protocol):
    """An abstract interface for sending emails."""

    def send_mass_mail(
        self, datatuple: list[tuple[str, str, str | None, list[str]]]
    ) -> Result[int]:
        """Sends multiple emails at once.

        Each element of datatuple is a tuple of (subject, message, from_email, recipient_list).
        from_email can be None to use the default email address.

        Args:
            datatuple: A list of tuples, where each tuple contains the arguments for a single
                email.

        Returns:
            The number of successfully delivered emails.
        """
        ...

    def send_single_mail(  # noqa: PLR0913,PLR0917
        self,
        subject: str,
        body: str,
        from_email: str | None,
        to_emails: list[str],
        attachments: tuple[tuple[str, Any, str], ...] | None = None,
        is_html: bool = False,
    ) -> Result[bool]:
        """Sends a single email.

        Args:
            subject: The subject of the email.
            body: The body of the email.
            from_email: The sender's email address. If None, the default email address is used.
            to_emails: A list of recipient email addresses.
            attachments: A tuple of attachments. Each attachment is a tuple of
              (filename, content, mimetype).
            is_html: Whether the body content is HTML. If True, sets the email
              content type to HTML.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        ...
