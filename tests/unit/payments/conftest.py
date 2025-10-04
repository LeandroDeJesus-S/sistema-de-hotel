import pytest

@pytest.fixture
def mock_payment_creator(mocker):
    mock_creator = mocker.patch('payments.views.Checkout.payment_creator_cls')
    mock_creator.return_value.session.redirect_url = 'http://stripepayment-hostedpage.url'
    return mock_creator