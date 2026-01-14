import pytest
from datetime import datetime
from exc import Result
from utils.adapters.email import DjangoEmailSender
from utils.adapters.image_validators import (
    MaxDimensionsImageValidator,
    MaxSizeImageValidator,
    DjangoImageAdapter,
    validate_benefit_icon,
    validate_service_logo,
)
from utils.adapters.queue import DjangoQTaskQueuer
from utils.adapters.unit_of_work import UnitOfWork
from django.core.exceptions import ValidationError

@pytest.mark.django_db
class TestDjangoEmailSender:
    def test_send_mass_mail_success(self, mocker):
        sender = DjangoEmailSender()
        mocker.patch("utils.adapters.email.send_mass_mail", return_value=5)

        datatuple = [("Subject", "Message", "from@example.com", ["to@example.com"])]
        result = sender.send_mass_mail(datatuple)

        assert result.is_ok()
        assert result.unwrap() == 5

    def test_send_single_mail_success(self, mocker):
        sender = DjangoEmailSender()
        mock_email = mocker.Mock()
        mock_email.send.return_value = 1
        mocker.patch("utils.adapters.email.EmailMessage", return_value=mock_email)

        result = sender.send_single_mail(
            subject="Test",
            body="Body",
            from_email="from@example.com",
            to_emails=["to@example.com"]
        )

        assert result.is_ok()
        assert result.unwrap() is True
        mock_email.send.assert_called_once()

    def test_send_single_mail_html_and_attachments(self, mocker):
        sender = DjangoEmailSender()
        mock_email = mocker.Mock()
        mock_email.send.return_value = 1
        mocker.patch("utils.adapters.email.EmailMessage", return_value=mock_email)

        result = sender.send_single_mail(
            subject="Test",
            body="<p>Body</p>",
            from_email="from@example.com",
            to_emails=["to@example.com"],
            is_html=True,
            attachments=(("file.txt", b"content", "text/plain"),)
        )

        assert result.is_ok()
        assert mock_email.content_subtype == "html"
        mock_email.attach.assert_called_once_with("file.txt", b"content", "text/plain")


class TestImageValidators:
    def test_max_dimensions_success(self, mocker):
        validator = MaxDimensionsImageValidator(max_width=100, max_height=100)
        image = mocker.Mock(spec=DjangoImageAdapter)
        image.width = 50
        image.height = 50
        result = validator(image)
        assert result.is_ok()

    def test_max_dimensions_failure(self, mocker):
        validator = MaxDimensionsImageValidator(max_width=100, max_height=100)
        image = mocker.Mock(spec=DjangoImageAdapter)
        image.width = 150
        image.height = 50

        result = validator(image)
        assert result.is_err()
        assert "exceed maximum allowed" in result.unwrap_err().msg

    def test_max_dimensions_exception(self, mocker):
        validator = MaxDimensionsImageValidator(
            max_width=100, max_height=100,
            raise_exception=True, exception_class=ValidationError
        )
        image = mocker.Mock(spec=DjangoImageAdapter)
        image.width = 150
        image.height = 50

        with pytest.raises(ValidationError):
            validator(image)

    def test_max_size_success(self, mocker):
        validator = MaxSizeImageValidator(max_size=1) # 1MB
        image = mocker.Mock(spec=DjangoImageAdapter)
        image.size = 500000 # 0.5MB

        result = validator(image)
        assert result.is_ok()

    def test_max_size_failure(self, mocker):
        validator = MaxSizeImageValidator(max_size=1)
        image = mocker.Mock(spec=DjangoImageAdapter)
        image.size = 2000000 # 2MB

        result = validator(image)
        assert result.is_err()
        assert "exceeds maximum allowed" in result.unwrap_err().msg

    def test_max_size_custom_message(self, mocker):
        validator = MaxSizeImageValidator(max_size=1, error_message="Size {size} > {max_size}")
        image = mocker.Mock(spec=DjangoImageAdapter)
        image.size = 2000000
        result = validator(image)
        assert result.is_err()
        assert result.unwrap_err().msg == "Size 2000000 > 1"

    def test_max_size_exception(self, mocker):
        validator = MaxSizeImageValidator(
            max_size=1, raise_exception=True, exception_class=ValidationError
        )
        image = mocker.Mock(spec=DjangoImageAdapter)
        image.size = 2000000
        with pytest.raises(ValidationError):
            validator(image)

    def test_validate_benefit_icon_success(self, mocker):
        image = mocker.Mock()
        image.width = 64
        image.height = 64
        image.size = 1000
        # Should not raise
        validate_benefit_icon(image)

    def test_validate_benefit_icon_fail_dimensions(self, mocker):
        image = mocker.Mock()
        image.width = 65
        image.height = 64
        image.size = 1000
        with pytest.raises(ValidationError):
            validate_benefit_icon(image)

    def test_validate_benefit_icon_fail_size(self, mocker):
        image = mocker.Mock()
        image.width = 64
        image.height = 64
        image.size = 6 * 1000000 # 6MB > 5MB limit
        with pytest.raises(ValidationError):
            validate_benefit_icon(image)

    def test_validate_service_logo_success(self, mocker):
        image = mocker.Mock()
        image.size = 1000
        # Should not raise
        validate_service_logo(image)

    def test_validate_service_logo_fail_size(self, mocker):
        image = mocker.Mock()
        image.size = 6 * 1000000 # 6MB > 5MB limit
        with pytest.raises(ValidationError):
            validate_service_logo(image)

class TestDjangoQTaskQueuer:
    def test_schedule_task(self, mocker):
        queuer = DjangoQTaskQueuer()
        mocker.patch("utils.adapters.queue.schedule")
        run_at = datetime.now()
        queuer.schedule_task("func", run_at, ("arg",), name="task1")
        from utils.adapters.queue import schedule
        schedule.assert_called_once()

    def test_queue_task(self, mocker):
        queuer = DjangoQTaskQueuer()
        mocker.patch("utils.adapters.queue.async_task")
        queuer.queue_task("func", ("arg",), name="group1")
        from utils.adapters.queue import async_task
        async_task.assert_called_once()


class TestUnitOfWork:
    def test_context_manager(self, mocker):
        mock_transaction = mocker.patch("utils.adapters.unit_of_work.transaction")
        uow = UnitOfWork()
        with uow:
            mock_transaction.set_autocommit.assert_called_with(False)
        mock_transaction.set_autocommit.assert_called_with(True)

    def test_commit(self, mocker):
        mock_transaction = mocker.patch("utils.adapters.unit_of_work.transaction")
        uow = UnitOfWork()
        uow.commit()
        mock_transaction.commit.assert_called_once()

    def test_rollback(self, mocker):
        mock_transaction = mocker.patch("utils.adapters.unit_of_work.transaction")
        uow = UnitOfWork()
        uow.rollback()
        mock_transaction.rollback.assert_called_once()

from utils.adapters.pdf import ReportLabPDFReceiptGenerator
class TestReportLabPDFReceiptGenerator:
    def test_generate_success(self, mocker):
        generator = ReportLabPDFReceiptGenerator()
        payment_entity = mocker.Mock()

        # Mock payment model structure
        payment_model = mocker.Mock()
        hotel = mocker.Mock()
        hotel.name = "Hotel Test"
        hotel.logo = None
        payment_model.reservation.room.hotel = hotel
        payment_model.reservation.room.room_class = "Standard"
        payment_model.reservation.room.number = "101"
        payment_model.reservation.formatted_price.return_value = "R$ 200,00"
        payment_model.reservation.client.complete_name = "John Doe"
        payment_model.reservation.checkin.strftime.return_value = "01/01/2023"
        payment_model.reservation.checkout.strftime.return_value = "05/01/2023"
        payment_model.created_at.strftime.return_value = "12:00:00 01/01/2023"
        payment_model.status = "Paid"

        mocker.patch("utils.adapters.pdf.entity_to_model", return_value=Result.Ok(payment_model))

        # Mock canvas
        mock_canvas = mocker.Mock()
        mocker.patch("utils.adapters.pdf.canvas.Canvas", return_value=mock_canvas)

        result = generator.generate(payment_entity)

        assert result.is_ok()
        mock_canvas.save.assert_called_once()

    def test_generate_success_with_logo(self, mocker):
        generator = ReportLabPDFReceiptGenerator()
        payment_entity = mocker.Mock()

        payment_model = mocker.Mock()
        hotel = mocker.Mock()
        hotel.name = "Hotel with Logo"
        hotel.logo.path = "/path/to/logo.png"
        payment_model.reservation.room.hotel = hotel
        payment_model.reservation.room.room_class = "Standard"
        payment_model.reservation.room.number = "101"
        payment_model.reservation.formatted_price.return_value = "R$ 200,00"
        payment_model.reservation.client.complete_name = "John Doe"
        payment_model.reservation.checkin.strftime.return_value = "01/01/2023"
        payment_model.reservation.checkout.strftime.return_value = "05/01/2023"
        payment_model.created_at.strftime.return_value = "12:00:00 01/01/2023"
        payment_model.status = "Paid"

        mocker.patch("utils.adapters.pdf.entity_to_model", return_value=Result.Ok(payment_model))
        mock_canvas = mocker.Mock()
        mocker.patch("utils.adapters.pdf.canvas.Canvas", return_value=mock_canvas)

        result = generator.generate(payment_entity)
        assert result.is_ok()
        mock_canvas.drawInlineImage.assert_called_once()

    def test_generate_conversion_error(self, mocker):
        generator = ReportLabPDFReceiptGenerator()
        payment_entity = mocker.Mock()

        mocker.patch("utils.adapters.pdf.entity_to_model", return_value=Result.Err("Conversion error"))

        result = generator.generate(payment_entity)
        assert result.is_err()
        assert "Failed to convert payment entity" in result.unwrap_err().msg

    def test_generate_exception(self, mocker):
        generator = ReportLabPDFReceiptGenerator()
        payment_entity = mocker.Mock()

        payment_model = mocker.Mock()
        # Mock the path to trigger exception when accessing hotel
        # payment_model.reservation.room.hotel
        mock_room = mocker.Mock()
        type(mock_room).hotel = mocker.PropertyMock(side_effect=Exception("DB Error"))
        payment_model.reservation.room = mock_room

        mocker.patch("utils.adapters.pdf.entity_to_model", return_value=Result.Ok(payment_model))

        result = generator.generate(payment_entity)
        assert result.is_err()
        assert "Failed to generate PDF" in result.unwrap_err().msg
