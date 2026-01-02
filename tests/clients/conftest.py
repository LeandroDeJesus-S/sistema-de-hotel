import pytest
from clients.domain.ports import (
    AbsCaptchaVerifier,
    AbsClientRepository,
    AbsPasswordManager,
    AbsSessionManager,
)

@pytest.fixture
def mock_client_repository(mocker):
    return mocker.Mock(spec=AbsClientRepository)


@pytest.fixture
def mock_password_manager(mocker):
    return mocker.Mock(spec=AbsPasswordManager)


@pytest.fixture
def mock_captcha_verifier(mocker):
    return mocker.Mock(spec=AbsCaptchaVerifier)


@pytest.fixture
def mock_session_manager(mocker):
    return mocker.Mock(spec=AbsSessionManager)
