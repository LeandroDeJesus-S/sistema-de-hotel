from unittest.mock import MagicMock

import pytest

from utils.adapters.email import DjangoEmailSender


@pytest.fixture
def email_sender():
    return DjangoEmailSender()


def test_send_mass_mail(email_sender, mocker):
    """
    Should call send_mass_mail with correct arguments.
    """
    mock_send_mass_mail = mocker.patch('utils.adapters.email.send_mass_mail', return_value=1)
    datatuple = [
        ('Subject 1', 'Message 1', 'from@example.com', ['to1@example.com']),
        ('Subject 2', 'Message 2', 'from@example.com', ['to2@example.com']),
    ]

    result = email_sender.send_mass_mail(datatuple)

    mock_send_mass_mail.assert_called_once_with(datatuple, fail_silently=False)
    assert result.unwrap() == 1


def test_send_single_mail(email_sender, mocker):
    """
    Should call EmailMessage with correct arguments and send it.
    """
    mock_email_message = MagicMock()
    mocker.patch('utils.adapters.email.EmailMessage', return_value=mock_email_message)
    mock_email_message.send.return_value = 1

    subject = 'Test Subject'
    body = 'Test Body'
    from_email = 'from@example.com'
    to_emails = ['to@example.com']

    result = email_sender.send_single_mail(subject, body, from_email, to_emails)

    mock_email_message.send.assert_called_once_with(fail_silently=False)
    assert result.unwrap() is True


def test_send_single_mail_html(email_sender, mocker):
    """
    Should set content_subtype to 'html' when is_html=True.
    """
    mock_email_message = MagicMock()
    mocker.patch('utils.adapters.email.EmailMessage', return_value=mock_email_message)
    mock_email_message.send.return_value = 1

    subject = 'Test Subject'
    body = '<p>Test HTML Body</p>'
    from_email = 'from@example.com'
    to_emails = ['to@example.com']

    result = email_sender.send_single_mail(subject, body, from_email, to_emails, is_html=True)

    assert mock_email_message.content_subtype == 'html'
    mock_email_message.send.assert_called_once_with(fail_silently=False)
    assert result.unwrap() is True
