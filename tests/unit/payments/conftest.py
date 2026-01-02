import pytest
from payments.domain.ports import (
    AbsSessionBasedPayment,
    AbsPaymentsRepository,
    WebhookEvent,
    PaymentWebhookHandler,
)


@pytest.fixture
def mock_session_based_payment(mocker):
    """Mock fixture for AbsSessionBasedPayment port."""
    return mocker.Mock(spec=AbsSessionBasedPayment)


@pytest.fixture
def mock_payments_repository(mocker):
    """Mock fixture for AbsPaymentsRepository port."""
    return mocker.Mock(spec=AbsPaymentsRepository)


@pytest.fixture
def mock_webhook_event(mocker):
    """Mock fixture for WebhookEvent port (generic, mocked as-is)."""
    return mocker.Mock(spec=WebhookEvent)


@pytest.fixture
def mock_payment_webhook_handler(mocker):
    """Mock fixture for PaymentWebhookHandler port (generic, mocked as-is)."""
    return mocker.Mock(spec=PaymentWebhookHandler)
