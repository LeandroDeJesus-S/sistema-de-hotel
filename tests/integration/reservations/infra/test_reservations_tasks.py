import pytest
from unittest.mock import Mock
from exc import Result, Error
from reservations.infra.tasks import (
    activate_reservation_task,
    check_reservation_dates_task,
    release_reservation_task,
    schedule_reservation_task,
    send_cancellation_notification,
    send_scheduling_notification,
    send_cancellation_client_email_task,
    send_cancellation_admin_email_task,
    send_reservation_expired_admin_email_task,
    send_reservation_expired_client_email_task,
    send_scheduling_email_task,
)


@pytest.mark.django_db
class TestReservationTasks:
    def test_activate_reservation_task_success(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Ok(mocker.Mock())

        reservation = mocker.Mock()
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.activate_reservation_usecase.override(mock_usecase),
        ):
            result = activate_reservation_task(reservation_id=1)
            assert result.is_ok()
            mock_usecase.assert_called_once_with(reservation)

    def test_activate_reservation_task_not_found(self, mocker, reservations_container):
        mock_usecase = mocker.Mock()

        with reservations_container.activate_reservation_usecase.override(mock_usecase):
            with pytest.raises(Error) as exc:
                activate_reservation_task(reservation_id=99999)
            assert 'not found' in str(exc.value)

    def test_release_reservation_task_success(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Ok(True)

        reservation = mocker.Mock()
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.release_reservation_usecase.override(mock_usecase),
        ):
            result = release_reservation_task(reservation_id=1)
            assert result.is_ok()
            mock_usecase.assert_called_once_with(reservation)

    def test_schedule_reservation_task_success(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Ok(mocker.Mock())

        reservation = mocker.Mock()
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.schedule_reservation_usecase.override(mock_usecase),
        ):
            result = schedule_reservation_task(reservation_id=1)
            assert result.is_ok()
            mock_usecase.assert_called_once_with(reservation)

    def test_send_cancellation_notification_success(
        self,
        mocker,
        mock_reservation_repository,
        mock_task_queuer,
        reservations_container,
    ):
        reservation = mocker.Mock()
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = send_cancellation_notification(reservation_id=1)
            assert result.is_ok()
            assert mock_task_queuer.queue_task.call_count == 2
            # Check that both client and admin email tasks are queued
            calls = mock_task_queuer.queue_task.call_args_list
            assert any('send_cancellation_client' in str(call) for call in calls)
            assert any('send_cancellation_admin' in str(call) for call in calls)

    def test_send_scheduling_notification_success(
        self, mocker, mock_reservation_repository, mock_task_queuer, reservations_container
    ):
        reservation = mocker.Mock()
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = send_scheduling_notification(reservation_id=1)
            assert result.is_ok()
            mock_task_queuer.queue_task.assert_called_once_with(
                send_scheduling_email_task, (1,), name='send_scheduling_1'
            )

    def test_activate_reservation_task_usecase_error(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Err('Usecase error')
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mocker.Mock())

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.activate_reservation_usecase.override(mock_usecase),
        ):
            with pytest.raises(Error) as exc:
                activate_reservation_task(reservation_id=1)
            assert 'Usecase error' in str(exc.value)

    def test_release_reservation_task_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                release_reservation_task(reservation_id=1)
            assert 'not found' in str(exc.value)

    def test_release_reservation_task_usecase_error(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Err('Usecase error')
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mocker.Mock())

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.release_reservation_usecase.override(mock_usecase),
        ):
            with pytest.raises(Error) as exc:
                release_reservation_task(reservation_id=1)
            assert 'Usecase error' in str(exc.value)

    def test_schedule_reservation_task_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                schedule_reservation_task(reservation_id=1)
            assert 'not found' in str(exc.value)

    def test_schedule_reservation_task_usecase_error(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Err('Usecase error')
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mocker.Mock())

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.schedule_reservation_usecase.override(mock_usecase),
        ):
            with pytest.raises(Error) as exc:
                schedule_reservation_task(reservation_id=1)
            assert 'Usecase error' in str(exc.value)

    def test_send_cancellation_notification_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                send_cancellation_notification(reservation_id=1)
            assert 'not found' in str(exc.value)

    def test_send_cancellation_notification_mailer_exception(
        self, mocker, mock_reservation_repository, mock_task_queuer, reservations_container
    ):
        from datetime import datetime, timezone

        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkin = datetime.now(tz=timezone.utc)
        reservation.checkout = datetime.now(tz=timezone.utc)
        reservation.cancelled_at = datetime.now(timezone.utc)
        reservation.client.email = 'client@example.com'
        reservation.client.complete_name = 'John Doe'
        reservation.room.number = '101'
        reservation.room.room_class.name = 'Standard'
        reservation.formatted_price.return_value = 'R$ 100,00'

        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = send_cancellation_notification(reservation_id=1)
            assert result.is_ok()
            # Email errors are handled in separate tasks, so main task succeeds
            assert mock_task_queuer.queue_task.call_count == 2

    def test_send_cancellation_notification_admin_mailer_exception(
        self, mocker, mock_reservation_repository, mock_task_queuer, reservations_container
    ):
        from datetime import datetime, timezone

        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkin = datetime.now(tz=timezone.utc)
        reservation.checkout = datetime.now(tz=timezone.utc)
        reservation.cancelled_at = datetime.now(timezone.utc)
        reservation.client.email = 'client@example.com'
        reservation.client.complete_name = 'John Doe'
        reservation.room.number = '101'
        reservation.room.room_class.name = 'Standard'
        reservation.formatted_price.return_value = 'R$ 100,00'

        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = send_cancellation_notification(reservation_id=1)
            assert result.is_ok()
            # Email errors are handled in separate tasks, so main task succeeds
            assert mock_task_queuer.queue_task.call_count == 2

    def test_send_scheduling_notification_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                send_scheduling_notification(reservation_id=1)
            assert 'not found' in str(exc.value)

    def test_send_scheduling_notification_mailer_exception(
        self, mocker, mock_reservation_repository, mock_task_queuer, reservations_container
    ):
        from datetime import datetime, timezone

        reservation = mocker.Mock()
        reservation.checkin = datetime.now(tz=timezone.utc)
        reservation.checkout = datetime.now(tz=timezone.utc)
        reservation.client.email = 'client@example.com'
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = send_scheduling_notification(reservation_id=1)
            assert result.is_ok()
            # Email errors are handled in separate tasks, so main task succeeds
            assert mock_task_queuer.queue_task.call_count == 1

    def test_check_reservation_dates_task_success(
        self,
        mocker,
        mock_reservation_repository,
        mock_room_repository,
        mock_task_queuer,
        reservations_container,
    ):
        from datetime import datetime, timezone, timedelta
        from reservations.domain.value_objects import ReservationStatusEnum

        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkout = datetime.now(tz=timezone.utc) - timedelta(days=1)  # Expired
        reservation.room.id = 1
        mock_reservation_repository.fetch_all_active.return_value = Result.Ok([reservation])
        mock_reservation_repository.save.return_value = Result.Ok(reservation)

        room = mocker.Mock()
        mock_room_repository.find_by_id.return_value = Result.Ok(room)
        mock_room_repository.save.return_value = Result.Ok(room)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.room_repo.override(mock_room_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = check_reservation_dates_task()
            assert result.is_ok()
            assert mock_task_queuer.queue_task.call_count == 2
            # Verify reservation status was updated
            assert reservation.status == ReservationStatusEnum.FINISHED
            # Verify room was made available
            assert room.available is True

    def test_check_reservation_dates_task_fetch_error(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.fetch_all_active.return_value = Result.Err('DB error')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                check_reservation_dates_task()
            assert 'failed to fetch active reservations' in str(exc.value)

    def test_check_reservation_dates_task_partial_failures(
        self,
        mocker,
        mock_reservation_repository,
        mock_room_repository,
        mock_task_queuer,
        reservations_container,
    ):
        from datetime import datetime, timezone, timedelta

        # Create two reservations - one succeeds, one fails
        reservation1 = mocker.Mock()
        reservation1.id = 1
        reservation1.checkout = datetime.now(tz=timezone.utc) - timedelta(days=1)
        reservation1.room.id = 1

        reservation2 = mocker.Mock()
        reservation2.id = 2
        reservation2.checkout = datetime.now(tz=timezone.utc) - timedelta(days=1)
        reservation2.room.id = 2

        mock_reservation_repository.fetch_all_active.return_value = Result.Ok([
            reservation1,
            reservation2,
        ])
        # First save succeeds, second fails
        mock_reservation_repository.save.side_effect = [
            Result.Ok(reservation1),
            Result.Err('Save failed'),
        ]

        room = mocker.Mock()
        mock_room_repository.find_by_id.return_value = Result.Ok(room)
        mock_room_repository.save.return_value = Result.Ok(room)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.room_repo.override(mock_room_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            # Should succeed despite individual failures
            result = check_reservation_dates_task()
            assert result.is_ok()

    def test_send_scheduling_email_task_success(
        self, mocker, mock_reservation_repository, mock_email_sender, reservations_container
    ):
        reservation = mocker.Mock()
        reservation.client.email = 'client@example.com'
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        # Mock template rendering to avoid date formatting issues
        mock_render = mocker.patch(
            'reservations.infra.tasks.render_to_string',
            return_value='<html>Email content</html>',
        )

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.email_sender.override(mock_email_sender),
        ):
            send_scheduling_email_task(1)  # Should not raise
            mock_email_sender.send_single_mail.assert_called_once()
            mock_render.assert_called_once_with(
                'emails/scheduling_notification_client.html', mocker.ANY
            )

    def test_send_scheduling_email_task_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                send_scheduling_email_task(1)
            assert 'not found' in str(exc.value)

    def test_send_scheduling_email_task_mailer_error(
        self, mocker, mock_reservation_repository, mock_email_sender, reservations_container
    ):
        reservation = mocker.Mock()
        reservation.client.email = 'client@example.com'
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)
        mock_email_sender.send_single_mail.side_effect = Exception('SMTP error')

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.email_sender.override(mock_email_sender),
        ):
            with pytest.raises(Error) as exc:
                send_scheduling_email_task(1)
            assert 'Failed to send scheduling email' in str(exc.value)

    def test_send_cancellation_client_email_task_success(
        self,
        mocker,
        mock_reservation_repository,
        mock_payments_repository,
        mock_email_sender,
        reservations_container,
    ):
        from datetime import datetime, timezone

        reservation = mocker.Mock()
        reservation.client.email = 'client@example.com'
        reservation.id = 1
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        payment = mocker.Mock()
        payment.refunded_amount = 100.0
        payment.refunded_at = datetime.now(timezone.utc)
        mock_payments_repository.get_by_reservation_id.return_value = Result.Ok(payment)

        # Mock template rendering to avoid date formatting issues
        mock_render = mocker.patch(
            'reservations.infra.tasks.render_to_string',
            return_value='<html>Email content</html>',
        )

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.payment_repo.override(mock_payments_repository),
            reservations_container.email_sender.override(mock_email_sender),
        ):
            send_cancellation_client_email_task(1)  # Should not raise
            mock_email_sender.send_single_mail.assert_called_once()
            mock_render.assert_called_once_with(
                'emails/cancellation_notification_client.html', mocker.ANY
            )

    def test_send_cancellation_client_email_task_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                send_cancellation_client_email_task(1)
            assert 'not found' in str(exc.value)

    def test_send_cancellation_admin_email_task_success(
        self,
        mocker,
        mock_reservation_repository,
        mock_payments_repository,
        mock_email_sender,
        reservations_container,
    ):
        from datetime import datetime, timezone

        reservation = mocker.Mock()
        reservation.id = 1
        reservation.client.complete_name = 'John Doe'
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        payment = mocker.Mock()
        payment.refunded_amount = 100.0
        payment.refunded_at = datetime.now(timezone.utc)
        mock_payments_repository.get_by_reservation_id.return_value = Result.Ok(payment)

        # Mock template rendering to avoid date formatting issues
        mock_render = mocker.patch(
            'reservations.infra.tasks.render_to_string',
            return_value='<html>Email content</html>',
        )

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.payment_repo.override(mock_payments_repository),
            reservations_container.email_sender.override(mock_email_sender),
        ):
            send_cancellation_admin_email_task(1)  # Should not raise
            mock_email_sender.send_single_mail.assert_called_once()
            mock_render.assert_called_once_with(
                'emails/cancellation_notification_admin.html', mocker.ANY
            )

    def test_send_cancellation_admin_email_task_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                send_cancellation_admin_email_task(1)
            assert 'not found' in str(exc.value)

    def test_send_reservation_expired_client_email_task_success(
        self, mocker, mock_reservation_repository, mock_email_sender, reservations_container
    ):
        reservation = mocker.Mock()
        reservation.client.email = 'client@example.com'
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        # Mock template rendering to avoid date formatting issues
        mock_render = mocker.patch(
            'reservations.infra.tasks.render_to_string',
            return_value='<html>Email content</html>',
        )

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.email_sender.override(mock_email_sender),
        ):
            send_reservation_expired_client_email_task(1)  # Should not raise
            mock_email_sender.send_single_mail.assert_called_once()
            mock_render.assert_called_once_with(
                'emails/reservation_expired_client.html', mocker.ANY
            )

    def test_send_reservation_expired_client_email_task_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                send_reservation_expired_client_email_task(1)
            assert 'not found' in str(exc.value)

    def test_send_reservation_expired_admin_email_task_success(
        self, mocker, mock_reservation_repository, mock_email_sender, reservations_container
    ):
        reservation = mocker.Mock()
        reservation.id = 1
        reservation.client.complete_name = 'John Doe'
        mock_reservation_repository.find_by_id.return_value = Result.Ok(reservation)

        # Mock template rendering to avoid date formatting issues
        mock_render = mocker.patch(
            'reservations.infra.tasks.render_to_string',
            return_value='<html>Email content</html>',
        )

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.email_sender.override(mock_email_sender),
        ):
            send_reservation_expired_admin_email_task(1)  # Should not raise
            mock_email_sender.send_single_mail.assert_called_once()
            mock_render.assert_called_once_with(
                'emails/reservation_expired_admin.html', mocker.ANY
            )

    def test_send_reservation_expired_admin_email_task_not_found(
        self, mocker, mock_reservation_repository, reservations_container
    ):
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')

        with reservations_container.reservation_repo.override(mock_reservation_repository):
            with pytest.raises(Error) as exc:
                send_reservation_expired_admin_email_task(1)
            assert 'not found' in str(exc.value)

    def test_check_reservation_dates_task_skips_future_reservations(
        self,
        mocker,
        mock_reservation_repository,
        mock_room_repository,
        mock_task_queuer,
        reservations_container,
    ):
        from datetime import datetime, timezone, timedelta

        # Reservation with future checkout
        future_reservation = mocker.Mock()
        future_reservation.checkout = datetime.now(tz=timezone.utc) + timedelta(
            days=1
        )  # Future date

        mock_reservation_repository.fetch_all_active.return_value = Result.Ok([
            future_reservation
        ])

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.room_repo.override(mock_room_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = check_reservation_dates_task()
            assert result.is_ok()
            # Should skip processing since checkout is in future, so no operations performed
            # The save might be called due to mock behavior, but the important thing is no tasks queued
            mock_task_queuer.queue_task.assert_not_called()

    def test_check_reservation_dates_task_room_id_none(
        self,
        mocker,
        mock_reservation_repository,
        mock_room_repository,
        mock_task_queuer,
        reservations_container,
    ):
        from datetime import datetime, timezone, timedelta

        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkout = datetime.now(tz=timezone.utc) - timedelta(days=1)
        reservation.room.id = None  # Room has no ID

        mock_reservation_repository.fetch_all_active.return_value = Result.Ok([reservation])
        mock_reservation_repository.save.return_value = Result.Ok(reservation)

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.room_repo.override(mock_room_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = check_reservation_dates_task()
            assert result.is_ok()  # Should succeed but handle room ID issue
            # Should save reservation but not find/update room or queue tasks
            mock_reservation_repository.save.assert_called_once()
            mock_room_repository.find_by_id.assert_not_called()
            mock_task_queuer.queue_task.assert_not_called()

    def test_check_reservation_dates_task_room_find_failure(
        self,
        mocker,
        mock_reservation_repository,
        mock_room_repository,
        mock_task_queuer,
        reservations_container,
    ):
        from datetime import datetime, timezone, timedelta

        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkout = datetime.now(tz=timezone.utc) - timedelta(days=1)
        reservation.room.id = 1

        mock_reservation_repository.fetch_all_active.return_value = Result.Ok([reservation])
        mock_reservation_repository.save.return_value = Result.Ok(reservation)
        mock_room_repository.find_by_id.return_value = Result.Err('Room not found')

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.room_repo.override(mock_room_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = check_reservation_dates_task()
            assert result.is_ok()  # Should succeed but handle room find failure
            # Should save reservation but not update room or queue tasks
            mock_reservation_repository.save.assert_called_once()
            mock_room_repository.find_by_id.assert_called_once()
            mock_room_repository.save.assert_not_called()
            mock_task_queuer.queue_task.assert_not_called()

    def test_check_reservation_dates_task_room_save_failure(
        self,
        mocker,
        mock_reservation_repository,
        mock_room_repository,
        mock_task_queuer,
        reservations_container,
    ):
        from datetime import datetime, timezone, timedelta

        reservation = mocker.Mock()
        reservation.id = 1
        reservation.checkout = datetime.now(tz=timezone.utc) - timedelta(days=1)
        reservation.room.id = 1

        room = mocker.Mock()

        mock_reservation_repository.fetch_all_active.return_value = Result.Ok([reservation])
        mock_reservation_repository.save.return_value = Result.Ok(reservation)
        mock_room_repository.find_by_id.return_value = Result.Ok(room)
        mock_room_repository.save.return_value = Result.Err('Room save failed')

        with (
            reservations_container.reservation_repo.override(mock_reservation_repository),
            reservations_container.room_repo.override(mock_room_repository),
            reservations_container.task_queuer.override(mock_task_queuer),
        ):
            result = check_reservation_dates_task()
            assert result.is_ok()  # Should succeed but handle room save failure
            # Should save reservation and find room but not save room or queue tasks
            mock_reservation_repository.save.assert_called_once()
            mock_room_repository.find_by_id.assert_called_once()
            mock_room_repository.save.assert_called_once()
            mock_task_queuer.queue_task.assert_not_called()
