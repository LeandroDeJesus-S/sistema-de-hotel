import pytest
from unittest.mock import Mock
from exc import Result, Error
from reservations.infra.tasks import (
    activate_reservation_task,
    release_reservation_task,
    schedule_reservation_task,
    send_cancellation_notification,
    send_scheduling_notification
)

@pytest.mark.django_db
class TestReservationTasks:
    def test_activate_reservation_task_success(self, mocker, mock_reservation_repository, reservations_container):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Ok(mocker.Mock())

        reservation = mocker.Mock()
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.activate_reservation_usecase.override(mock_usecase):

            result = activate_reservation_task(reservation_id=1)
            assert result.is_ok()
            mock_usecase.assert_called_once_with(reservation)

    def test_activate_reservation_task_not_found(self, mocker, mock_reservation_repository, reservations_container):
        mock_reservation_repository.find_by_id.return_value = Result.Err("Not found")

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                activate_reservation_task(reservation_id=1)
            assert "not found" in str(exc.value)

    def test_release_reservation_task_success(self, mocker, mock_reservation_repository, reservations_container):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Ok(True)

        reservation = mocker.Mock()
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.release_reservation_usecase.override(mock_usecase):

            result = release_reservation_task(reservation_id=1)
            assert result.is_ok()
            mock_usecase.assert_called_once_with(reservation)

    def test_schedule_reservation_task_success(self, mocker, mock_reservation_repository, reservations_container):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Ok(mocker.Mock())

        reservation = mocker.Mock()
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.schedule_reservation_usecase.override(mock_usecase):

            result = schedule_reservation_task(reservation_id=1)
            assert result.is_ok()
            mock_usecase.assert_called_once_with(reservation)

    def test_send_cancellation_notification_success(self, mocker, mock_reservation_repository, mock_payments_repository, mock_email_sender, reservations_container, client_entity):
        from datetime import date, datetime, timezone
        from decimal import Decimal

        # Use real objects where possible to avoid template rendering issues with Mocks
        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkin = date.today()
        reservation.checkout = date.today()
        reservation.cancelled_at = datetime.now(timezone.utc)
        reservation.client = client_entity
        reservation.room.number = "101"
        reservation.room.room_class.name = "Standard"
        reservation.formatted_price.return_value = "R$ 100,00"

        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        payment = mocker.Mock()
        payment.refunded_amount = 100.0
        payment.refunded_at = datetime.now(timezone.utc)
        mock_payments_repository.get_by_reservation_id.return_value = Result.Ok(payment)

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.payment_repo.override(mock_payments_repository), \
             reservations_container.email_sender.override(mock_email_sender):

            result = send_cancellation_notification(reservation_id=1)
            assert result.is_ok()
            assert mock_email_sender.send_single_mail.call_count >= 1

    def test_send_scheduling_notification_success(self, mocker, mock_reservation_repository, mock_email_sender, reservations_container):
        from datetime import date
        reservation = mocker.Mock()
        reservation.checkin = date.today()
        reservation.checkout = date.today()
        reservation.client.email = "client@example.com"
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.email_sender.override(mock_email_sender):

            result = send_scheduling_notification(reservation_id=1)
            assert result.is_ok()
            mock_email_sender.send_single_mail.assert_called_once()

    def test_activate_reservation_task_usecase_error(self, mocker, mock_reservation_repository, reservations_container):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Err("Usecase error")
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mocker.Mock())

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.activate_reservation_usecase.override(mock_usecase):

            with pytest.raises(Error) as exc:
                activate_reservation_task(reservation_id=1)
            assert "Usecase error" in str(exc.value)

    def test_release_reservation_task_not_found(self, mocker, mock_reservation_repository, reservations_container):
        mock_reservation_repository.find_by_id.return_value = Result.Err("Not found")

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                release_reservation_task(reservation_id=1)
            assert "not found" in str(exc.value)

    def test_release_reservation_task_usecase_error(self, mocker, mock_reservation_repository, reservations_container):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Err("Usecase error")
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mocker.Mock())

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.release_reservation_usecase.override(mock_usecase):

            with pytest.raises(Error) as exc:
                release_reservation_task(reservation_id=1)
            assert "Usecase error" in str(exc.value)

    def test_schedule_reservation_task_not_found(self, mocker, mock_reservation_repository, reservations_container):
        mock_reservation_repository.find_by_id.return_value = Result.Err("Not found")

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                schedule_reservation_task(reservation_id=1)
            assert "not found" in str(exc.value)

    def test_schedule_reservation_task_usecase_error(self, mocker, mock_reservation_repository, reservations_container):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Err("Usecase error")
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mocker.Mock())

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.schedule_reservation_usecase.override(mock_usecase):

            with pytest.raises(Error) as exc:
                schedule_reservation_task(reservation_id=1)
            assert "Usecase error" in str(exc.value)

    def test_send_cancellation_notification_not_found(self, mocker, mock_reservation_repository, reservations_container):
        mock_reservation_repository.find_by_id.return_value = Result.Err("Not found")

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            result = send_cancellation_notification(reservation_id=1)
            assert result.is_err()
            assert "not found" in result.unwrap_err().msg

    def test_send_cancellation_notification_mailer_exception(self, mocker, mock_reservation_repository, mock_email_sender, reservations_container):
        from datetime import date, datetime, timezone
        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkin = date.today()
        reservation.checkout = date.today()
        reservation.cancelled_at = datetime.now(timezone.utc)
        reservation.client.email = "client@example.com"
        reservation.client.complete_name = "John Doe"
        reservation.room.number = "101"
        reservation.room.room_class.name = "Standard"
        reservation.formatted_price.return_value = "R$ 100,00"

        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)
        mock_email_sender.send_single_mail.side_effect = Exception("Mailer error")

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.email_sender.override(mock_email_sender):

            result = send_cancellation_notification(reservation_id=1)
            assert result.is_err()
            assert "Failed to send client notification email" in result.unwrap_err().msg

    def test_send_cancellation_notification_admin_mailer_exception(self, mocker, mock_reservation_repository, mock_email_sender, reservations_container):
        from datetime import date, datetime, timezone
        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkin = date.today()
        reservation.checkout = date.today()
        reservation.cancelled_at = datetime.now(timezone.utc)
        reservation.client.email = "client@example.com"
        reservation.client.complete_name = "John Doe"
        reservation.room.number = "101"
        reservation.room.room_class.name = "Standard"
        reservation.formatted_price.return_value = "R$ 100,00"

        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)
        # First call success (client), second call fail (admin)
        mock_email_sender.send_single_mail.side_effect = [Result.Ok(True), Exception("Admin mailer error")]

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.email_sender.override(mock_email_sender):

            result = send_cancellation_notification(reservation_id=1)
            assert result.is_err()
            assert "Failed to send admin notification email" in result.unwrap_err().msg

    def test_send_scheduling_notification_not_found(self, mocker, mock_reservation_repository, reservations_container):
        mock_reservation_repository.find_by_id.return_value = Result.Err("Not found")

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            result = send_scheduling_notification(reservation_id=1)
            assert result.is_err()
            assert "not found" in result.unwrap_err().msg

    def test_send_scheduling_notification_mailer_exception(self, mocker, mock_reservation_repository, mock_email_sender, reservations_container):
        from datetime import date
        reservation = mocker.Mock()
        reservation.checkin = date.today()
        reservation.checkout = date.today()
        reservation.client.email = "client@example.com"
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)
        mock_email_sender.send_single_mail.side_effect = Exception("Mailer error")

        with reservations_container.reservation_repo.override(mock_reservation_repository), \
             reservations_container.email_sender.override(mock_email_sender):

            result = send_scheduling_notification(reservation_id=1)
            assert result.is_err()
            assert "Failed to send client notification email" in result.unwrap_err().msg
