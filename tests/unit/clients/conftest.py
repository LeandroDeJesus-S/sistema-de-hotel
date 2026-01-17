import pytest
from base.ports.queue import TaskQueuer
from base.ports.rate_limiter import AbsRateLimiter
from clients.domain.ports import (
    AbsCaptchaVerifier,
    AbsClientRepository,
    AbsPasswordManager,
    AbsSessionManager,
    AbsTokenManager,
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


@pytest.fixture
def mock_task_queuer(mocker):
    return mocker.Mock(spec=TaskQueuer)


@pytest.fixture
def mock_token_manager(mocker):
    return mocker.Mock(spec=AbsTokenManager)


@pytest.fixture
def mock_rate_limiter(mocker):
    return mocker.Mock(spec=AbsRateLimiter)


@pytest.fixture
def clients_container(settings):
    from clients.container import ClientsContainer  # noqa: PLC0415
    clients_container = ClientsContainer()
    clients_container.config.from_dict(settings.__dict__)
    clients_container.wire(modules=['clients.views'])
