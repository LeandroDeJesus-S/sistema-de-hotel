import pytest
from http import HTTPStatus
from unittest.mock import Mock, call
from django.test import RequestFactory
from django.http import HttpResponse

from base.dtos import TemplateRenderResultDTO, RedirectResultDTO, MessageDTO
from clients.infra.presenters import (
    signup_post_presenter,
    signin_post_presenter,
    password_change_post_presenter,
)
from exc import Result

class TestPresenters:
    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    @pytest.fixture
    def mock_render(self, mocker):
        return mocker.patch('clients.infra.presenters.render')

    @pytest.fixture
    def mock_redirect(self, mocker):
        return mocker.patch('clients.infra.presenters.redirect')

    @pytest.fixture
    def mock_reverse(self, mocker):
        return mocker.patch('clients.infra.presenters.reverse', return_value='/mocked-url')

    @pytest.fixture
    def mock_messages(self, mocker):
        return mocker.patch('clients.infra.presenters.messages')

    def test_signup_post_presenter_render(self, request_factory, mock_render, mock_messages):
        """Should render signup template with errors when DTO is TemplateRenderResultDTO."""
        # Arrange
        request = request_factory.post('/signup')
        dto = TemplateRenderResultDTO(
            template_name='signup.html',
            context={'foo': 'bar'},
            messages=[MessageDTO(typ='error', msg='Error msg')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = signup_post_presenter(request, result)

        # Assert
        assert response_result.is_ok()
        mock_messages.error.assert_called_once_with(request, 'Error msg')
        mock_render.assert_called_once_with(request, 'signup.html', {'foo': 'bar'})

    def test_signup_post_presenter_redirect(self, request_factory, mock_redirect, mock_reverse, mock_messages):
        """Should redirect when DTO is RedirectResultDTO."""
        # Arrange
        request = request_factory.post('/signup')
        dto = RedirectResultDTO(
            url='success_url',
            args=(1,),
            messages=[MessageDTO(typ='success', msg='Success msg')],
            code=HTTPStatus.FOUND
        )
        result = Result.Ok(dto)

        # Act
        response_result = signup_post_presenter(request, result)

        # Assert
        assert response_result.is_ok()
        mock_messages.success.assert_called_once_with(request, 'Success msg')
        mock_reverse.assert_called_once_with('success_url', args=(1,))
        mock_redirect.assert_called_once_with('/mocked-url', permanent=False)

    def test_signin_post_presenter_render(self, request_factory, mock_render, mock_messages):
        """Should render signin template with errors when DTO is TemplateRenderResultDTO."""
        # Arrange
        request = request_factory.post('/signin')
        dto = TemplateRenderResultDTO(
            template_name='signin.html',
            context={'foo': 'bar'},
            messages=[MessageDTO(typ='error', msg='Error msg')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = signin_post_presenter(request, result)

        # Assert
        assert response_result.is_ok()
        mock_messages.error.assert_called_once_with(request, 'Error msg')
        mock_render.assert_called_once_with(request, 'signin.html', {'foo': 'bar'})

    def test_signin_post_presenter_redirect(self, request_factory, mock_redirect, mock_reverse, mock_messages):
        """Should redirect when DTO is RedirectResultDTO."""
        # Arrange
        request = request_factory.post('/signin')
        dto = RedirectResultDTO(
            url='success_url',
            args=(),
            messages=[MessageDTO(typ='success', msg='Success msg')],
            code=HTTPStatus.PERMANENT_REDIRECT
        )
        result = Result.Ok(dto)

        # Act
        response_result = signin_post_presenter(request, result)

        # Assert
        assert response_result.is_ok()
        mock_messages.success.assert_called_once_with(request, 'Success msg')
        mock_reverse.assert_called_once_with('success_url', args=())
        mock_redirect.assert_called_once_with('/mocked-url', permanent=True)

    def test_password_change_post_presenter(self, request_factory, mock_redirect, mock_reverse, mock_messages):
        """Should redirect with messages for password change."""
        # Arrange
        request = request_factory.post('/password_change')
        dto = RedirectResultDTO(
            url='profile_url',
            args=(1,),
            messages=[MessageDTO(typ='info', msg='Info msg')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = password_change_post_presenter(request, result)

        # Assert
        assert response_result.is_ok()
        mock_messages.info.assert_called_once_with(request, 'Info msg')
        mock_reverse.assert_called_once_with('profile_url', args=(1,))
        mock_redirect.assert_called_once_with('/mocked-url', permanent=False)
