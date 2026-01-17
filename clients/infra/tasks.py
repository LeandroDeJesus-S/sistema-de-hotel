from dependency_injector.wiring import Provide, inject
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

from base.ports.email import AbsEmailSender
from clients.container import ClientsContainer
from clients.domain.ports import AbsClientRepository
from exc import Result


@inject
def send_password_change_email_task(
    client_id: int,
    token: str,
    domain: str,
    email_sender: AbsEmailSender = Provide[ClientsContainer.email_sender],
    repo: AbsClientRepository = Provide[ClientsContainer.client_repo],
) -> None:
    """
    Send password change email with magic link.
    """
    try:
        client_result = repo.get_by_id(client_id)
        if client_result.is_err():
            raise Result.Err(f'Client with id {client_id} not found.').unwrap_err()

        client = client_result.unwrap()

        # Build the link
        path = reverse(
            'update_perfil_password_confirm',
            kwargs={'pk': client.id, 'token': token},
        )

        protocol = 'https' if settings.SECURE_SSL_REDIRECT else 'http'
        magic_link = f'{protocol}://{domain}{path}'

        html_body = render_to_string(
            'emails/password_change_link.html',
            {
                'client': client,
                'magic_link': magic_link,
            },
        )
        email_sender.send_single_mail(
            subject='Password Change Request',
            body=html_body,
            from_email=None,
            to_emails=[str(client.email)],
            is_html=True,
        )

    except Exception as e:
        raise Result.Err('Failed to send password change email', src_error=e).unwrap_err()
