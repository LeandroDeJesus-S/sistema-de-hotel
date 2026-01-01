from typing import Any

from django.core.mail import EmailMessage, send_mass_mail

from base.ports.email import AbsEmailSender
from exc import Result


class DjangoEmailSender(AbsEmailSender):
    """An adapter that uses Django's email functionality to send emails."""

    def send_mass_mail(  # noqa: PLR6301
        self, datatuple: list[tuple[str, str, str | None, list[str]]]
    ) -> Result[int]:
        """Sends multiple emails at once using Django's send_mass_mail.

        Each element of datatuple is a tuple of (subject, message, from_email, recipient_list).
        from_email can be None to use the default email address.

        Args:
            datatuple: A list of tuples, where each tuple contains the arguments for a single
                email.

        Returns:
            The number of successfully delivered emails.
        """
        sent_emails: int = send_mass_mail(datatuple, fail_silently=False)
        return Result.Ok(sent_emails)

    def send_single_mail(  # noqa: PLR6301,PLR0913,PLR0917
        self,
        subject: str,
        body: str,
        from_email: str | None,
        to_emails: list[str],
        attachments: tuple[tuple[str, Any, str], ...] | None = None,
        is_html: bool = False,
    ) -> Result[bool]:
        """Sends a single email using Django's EmailMessage.

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
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=to_emails,
        )
        if is_html:
            email.content_subtype = 'html'
        if attachments:
            for attachment in attachments:
                email.attach(*attachment)
        return Result.Ok(email.send(fail_silently=False) == 1)
