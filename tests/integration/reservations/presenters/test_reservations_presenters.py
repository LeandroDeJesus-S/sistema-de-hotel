import pytest
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse

from base.dtos import MessageDTO, RedirectResultDTO, TemplateRenderResultDTO
from exc import Result
from reservations.infra.presenters import (
    cancel_reservation_get_presenter,
    cancel_reservation_post_presenter,
    reserve_get_presenter,
    reserve_post_presenter,
)


@pytest.mark.django_db
class TestReserveGetPresenter:
    def test_should_render_template_with_room_pk(self, request_with_messages):
        """Should render the template and add room_pk to context."""
        # Arrange
        room_id = 1
        dto = TemplateRenderResultDTO(
            template_name='reserve.html',
            context={'some_data': 'value'},
            messages=[MessageDTO(typ='info', msg='Hello')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = reserve_get_presenter(request_with_messages, result, room_id)

        # Assert
        assert response_result.is_ok()
        response = response_result.unwrap()
        assert response.status_code == 200
        assert isinstance(response, HttpResponse)

        # Verify messages
        messages = list(request_with_messages._messages)
        assert len(messages) == 1
        assert messages[0].message == 'Hello'
        assert messages[0].level_tag == 'alert-info'

    def test_should_redirect(self, request_with_messages):
        """Should redirect to the specified URL."""
        # Arrange
        room_id = 1
        dto = RedirectResultDTO(
            url='home',
            messages=[MessageDTO(typ='success', msg='Redirecting')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = reserve_get_presenter(request_with_messages, result, room_id)

        # Assert
        assert response_result.is_ok()
        response = response_result.unwrap()
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == reverse('home')

        messages = list(request_with_messages._messages)
        assert len(messages) == 1
        assert messages[0].message == 'Redirecting'


@pytest.mark.django_db
class TestReservePostPresenter:
    def test_should_render_template(self, request_with_messages):
        """Should render the template and handle messages."""
        # Arrange
        dto = TemplateRenderResultDTO(
            template_name='reserve.html',
            context={'data': 123, 'room_pk': 1},
            messages=[MessageDTO(typ='success', msg='Success Message')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = reserve_post_presenter(request_with_messages, result)

        # Assert
        assert response_result.is_ok()
        response = response_result.unwrap()
        assert response.status_code == 200
        assert isinstance(response, HttpResponse)

        # Verify messages
        messages = list(request_with_messages._messages)
        assert len(messages) == 1
        assert messages[0].message == 'Success Message'
        assert messages[0].level_tag == 'alert-success'

    def test_should_redirect(self, request_with_messages):
        """Should redirect to the specified URL and handle messages."""
        # Arrange
        dto = RedirectResultDTO(
            url='home',
            messages=[MessageDTO(typ='error', msg='Error Message')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = reserve_post_presenter(request_with_messages, result)

        # Assert
        assert response_result.is_ok()
        response = response_result.unwrap()
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == reverse('home')

        # Verify messages
        messages = list(request_with_messages._messages)
        assert len(messages) == 1
        assert messages[0].message == 'Error Message'
        assert messages[0].level_tag == 'alert-danger'


@pytest.mark.django_db
class TestCancelReservationGetPresenter:
    def test_should_render_template(self, request_with_messages):
        """Should render the template and handle messages."""
        # Arrange
        dto = TemplateRenderResultDTO(
            template_name='cancel_reservation.html',
            context={},
            messages=[MessageDTO(typ='warning', msg='Warning Message')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = cancel_reservation_get_presenter(request_with_messages, result)

        # Assert
        assert response_result.is_ok()
        response = response_result.unwrap()
        assert response.status_code == 200
        assert isinstance(response, HttpResponse)

        # Verify messages
        messages = list(request_with_messages._messages)
        assert len(messages) == 1
        assert messages[0].message == 'Warning Message'
        assert messages[0].level_tag == 'alert-warning'

    def test_should_redirect(self, request_with_messages):
        """Should redirect to the specified URL and handle messages."""
        # Arrange
        dto = RedirectResultDTO(
            url='home',
            messages=[MessageDTO(typ='info', msg='Info Message')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = cancel_reservation_get_presenter(request_with_messages, result)

        # Assert
        assert response_result.is_ok()
        response = response_result.unwrap()
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == reverse('home')

        # Verify messages
        messages = list(request_with_messages._messages)
        assert len(messages) == 1
        assert messages[0].message == 'Info Message'


@pytest.mark.django_db
class TestCancelReservationPostPresenter:
    def test_should_render_template(self, request_with_messages):
        """Should render the template and handle messages."""
        # Arrange
        dto = TemplateRenderResultDTO(
            template_name='cancel_reservation.html',
            context={},
            messages=[MessageDTO(typ='success', msg='Success')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = cancel_reservation_post_presenter(request_with_messages, result)

        # Assert
        assert response_result.is_ok()
        response = response_result.unwrap()
        assert response.status_code == 200
        assert isinstance(response, HttpResponse)

        # Verify messages
        messages = list(request_with_messages._messages)
        assert len(messages) == 1
        assert messages[0].message == 'Success'

    def test_should_redirect(self, request_with_messages):
        """Should redirect to the specified URL and handle messages."""
        # Arrange
        dto = RedirectResultDTO(
            url='home',
            messages=[MessageDTO(typ='error', msg='Failed')]
        )
        result = Result.Ok(dto)

        # Act
        response_result = cancel_reservation_post_presenter(request_with_messages, result)

        # Assert
        assert response_result.is_ok()
        response = response_result.unwrap()
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == reverse('home')

        # Verify messages
        messages = list(request_with_messages._messages)
        assert len(messages) == 1
        assert messages[0].message == 'Failed'
