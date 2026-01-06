import pytest
from unittest.mock import Mock

from django.urls import reverse

from base.dtos import RedirectResultDTO, TemplateRenderResultDTO
from exc import Result
from payments.domain.dtos import CheckoutResultDTO
from payments.infra.presenters import (
    checkout_get_presenter,
    checkout_post_presenter,
    payment_cancel_get_presenter,
    payment_success_get_presenter,
)


@pytest.mark.django_db
class TestPresenters:
    def test_checkout_get_presenter_error(self, rf, mocker):
        """Should redirect to rooms with error message when result is error."""
        request = rf.get('/')
        result = Result.Err('Some error')

        mock_messages = mocker.patch('payments.infra.presenters.messages')
        mock_redirect = mocker.patch('payments.infra.presenters.redirect')
        mock_redirect.return_value = Mock()

        response = checkout_get_presenter(request, result)

        assert response.is_ok()
        mock_messages.error.assert_called_once_with(request, 'Failed to render checkout page')
        mock_redirect.assert_called_once_with('rooms')

    def test_checkout_get_presenter_template_render(self, rf, mocker):
        """Should render template when result is TemplateRenderResultDTO."""
        request = rf.get('/')
        dto = TemplateRenderResultDTO.safe_create(
            template_name='checkout.html', context={'key': 'value'}
        ).unwrap()
        result = Result.Ok(dto)

        mock_render = mocker.patch('payments.infra.presenters.render')
        mock_render.return_value = Mock()

        response = checkout_get_presenter(request, result)

        assert response.is_ok()
        mock_render.assert_called_once_with(request, 'checkout.html', {'key': 'value'})

    def test_checkout_get_presenter_redirect_dto(self, rf, mocker):
        """Should redirect when result is RedirectResultDTO."""
        request = rf.get('/')
        dto = RedirectResultDTO.safe_create(url='rooms', code=302).unwrap()
        result = Result.Ok(dto)

        mock_redirect = mocker.patch('payments.infra.presenters.redirect')
        mock_redirect.return_value = Mock()

        response = checkout_get_presenter(request, result)

        assert response.is_ok()
        mock_redirect.assert_called_once_with('rooms', permanent=False)

    def test_checkout_post_presenter_success(self, rf, mocker):
        """Should redirect to session URL on success."""
        request = rf.post('/')
        dto = CheckoutResultDTO.safe_create(
            client_id='client_123', session_id='session_123', session_url='http://checkout.com'
        ).unwrap()
        result = Result.Ok(dto)

        mock_redirect = mocker.patch('payments.infra.presenters.redirect')
        mock_redirect.return_value = Mock()

        response = checkout_post_presenter(request, result)

        assert response.is_ok()
        mock_redirect.assert_called_once_with('http://checkout.com')

    def test_checkout_post_presenter_error(self, rf, mocker):
        """Should redirect back with error message on failure."""
        request = rf.post('/')
        request.META = {'HTTP_REFERER': 'http://referer.com'}
        result = Result.Err('Payment failed')

        mock_messages = mocker.patch('payments.infra.presenters.messages')
        mock_redirect = mocker.patch('payments.infra.presenters.redirect')
        mock_redirect.return_value = Mock()

        response = checkout_post_presenter(request, result)

        assert response.is_ok()
        mock_messages.error.assert_called_once()
        mock_redirect.assert_called_once_with('http://referer.com')

    def test_payment_success_get_presenter_error(self, rf, mocker):
        """Should redirect to rooms with error message when result is error."""
        request = rf.get('/')
        result = Result.Err('Some error')

        mock_messages = mocker.patch('payments.infra.presenters.messages')
        mock_redirect = mocker.patch('payments.infra.presenters.redirect')
        mock_redirect.return_value = Mock()

        response = payment_success_get_presenter(request, result)

        # Note: This function doesn't return Result, returns HttpResponse directly
        mock_messages.error.assert_called_once()
        mock_redirect.assert_called_once_with(reverse('rooms'))

    def test_payment_success_get_presenter_template_render(self, rf, mocker):
        """Should render template when result is TemplateRenderResultDTO."""
        request = rf.get('/')
        dto = TemplateRenderResultDTO.safe_create(
            template_name='success.html', context={'payment': 'data'}
        ).unwrap()
        result = Result.Ok(dto)

        mock_render = mocker.patch('payments.infra.presenters.render')
        mock_render.return_value = Mock()

        response = payment_success_get_presenter(request, result)

        mock_render.assert_called_once_with(request, 'success.html', {'payment': 'data'})

    def test_payment_success_get_presenter_redirect_dto(self, rf, mocker):
        """Should redirect when result is RedirectResultDTO."""
        request = rf.get('/')
        dto = RedirectResultDTO.safe_create(url='rooms', code=302).unwrap()
        result = Result.Ok(dto)

        mock_redirect = mocker.patch('payments.infra.presenters.redirect')
        mock_redirect.return_value = Mock()

        response = payment_success_get_presenter(request, result)

        mock_redirect.assert_called_once_with('rooms', permanent=False)

    def test_payment_cancel_get_presenter_error(self, rf, mocker):
        """Should redirect to rooms with error message when result is error."""
        request = rf.get('/')
        result = Result.Err('Some error')

        mock_messages = mocker.patch('payments.infra.presenters.messages')
        mock_redirect = mocker.patch('payments.infra.presenters.redirect')
        mock_redirect.return_value = Mock()

        response = payment_cancel_get_presenter(request, result)

        mock_messages.error.assert_called_once_with(request, 'Failed to render cancel page')
        mock_redirect.assert_called_once_with(reverse('rooms'))

    def test_payment_cancel_get_presenter_template_render(self, rf, mocker):
        """Should render template when result is TemplateRenderResultDTO."""
        request = rf.get('/')
        dto = TemplateRenderResultDTO.safe_create(
            template_name='cancel.html', context={'reservation': 'data'}
        ).unwrap()
        result = Result.Ok(dto)

        mock_render = mocker.patch('payments.infra.presenters.render')
        mock_render.return_value = Mock()

        response = payment_cancel_get_presenter(request, result)

        mock_render.assert_called_once_with(request, 'cancel.html', {'reservation': 'data'})

    def test_payment_cancel_get_presenter_redirect_dto(self, rf, mocker):
        """Should redirect when result is RedirectResultDTO."""
        request = rf.get('/')
        dto = RedirectResultDTO.safe_create(url='rooms', code=302).unwrap()
        result = Result.Ok(dto)

        mock_redirect = mocker.patch('payments.infra.presenters.redirect')
        mock_redirect.return_value = Mock()

        response = payment_cancel_get_presenter(request, result)

        mock_redirect.assert_called_once_with('rooms', permanent=False)

    def test_checkout_get_presenter_invalid_dto(self, rf):
        """Should crash on invalid DTO (edge case - code assumes valid DTO)."""
        request = rf.get('/')
        # Pass a non-DTO result
        result = Result.Ok('invalid')

        with pytest.raises(AttributeError):
            checkout_get_presenter(request, result)

    def test_checkout_post_presenter_invalid_result(self, rf):
        """Should crash on invalid result (edge case - code assumes valid DTO)."""
        request = rf.post('/')
        result = Result.Ok('not a dto')

        with pytest.raises(AttributeError):
            checkout_post_presenter(request, result)
