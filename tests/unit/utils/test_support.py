import pytest
from datetime import date, datetime, time, timedelta
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from PIL import Image

from base.entity import BaseEntity
from exc import Result
from reservations.domain.entities import Reservation as ReservationEntity
from utils.support import (
    captcha_required,
    entity_to_model,
    get_available_dates_message,
    model_to_entity,
    model_validate,
    models_to_entities,
    resize_image,
    update_changed_fields,
    verify_captcha,
)


class TestResizeImage:
    """Tests for the resize_image function."""

    def test_resize_with_width_only(self, mocker):
        """Should resize image calculating height automatically when h is None."""
        mock_img = Mock(spec=Image.Image)
        mock_img.size = (200, 100)  # original: w=200, h=100

        mocker.patch('utils.support.Image.open', return_value=mock_img)
        mocker.patch.object(mock_img, 'resize', return_value=mock_img)
        mocker.patch.object(mock_img, 'save')
        mocker.patch.object(mock_img, 'close')

        resize_image('path/to/image.jpg', 100)

        # h should be round(100 * 100 / 200) = 50
        # But min(100, 50) = 50
        mock_img.resize.assert_called_once_with((100, 50), Image.Resampling.NEAREST)
        mock_img.save.assert_called_once_with('path/to/image.jpg', optimize=True, quality=70)
        assert mock_img.close.call_count == 2  # img.close() and resized.close()

    def test_resize_with_width_and_height(self, mocker):
        """Should resize image with both width and height provided."""
        mock_img = Mock(spec=Image.Image)
        mock_img.size = (200, 100)

        mocker.patch('utils.support.Image.open', return_value=mock_img)
        mocker.patch.object(mock_img, 'resize', return_value=mock_img)
        mocker.patch.object(mock_img, 'save')
        mocker.patch.object(mock_img, 'close')

        resize_image('path/to/image.jpg', 150, 75)

        mock_img.resize.assert_called_once_with((150, 75), Image.Resampling.NEAREST)
        mock_img.save.assert_called_once_with('path/to/image.jpg', optimize=True, quality=70)
        assert mock_img.close.call_count == 2  # img.close() and resized.close()

    def test_resize_height_capped_to_original(self, mocker):
        """Should cap height to original height when calculated height exceeds original."""
        mock_img = Mock(spec=Image.Image)
        mock_img.size = (100, 50)  # original: w=100, h=50

        mocker.patch('utils.support.Image.open', return_value=mock_img)
        mocker.patch.object(mock_img, 'resize')
        mocker.patch.object(mock_img, 'save')
        mocker.patch.object(mock_img, 'close')

        resize_image('path/to/image.jpg', 200)  # w=200, calculated h=100, but cap to 50

        mock_img.resize.assert_called_once_with((200, 50), Image.Resampling.NEAREST)


class TestVerifyCaptcha:
    """Tests for the verify_captcha function."""

    def test_successful_verification_high_score(self, mocker):
        """Should return True when captcha verification succeeds with high score."""
        mock_response = Mock()
        mock_response.json.return_value = {'success': True, 'score': 0.9}

        mocker.patch('utils.support.requests.post', return_value=mock_response)
        mocker.patch('utils.support.settings.CAPTCHA_MIN_SCORE', 0.5)
        mocker.patch('utils.support.settings.G_RECAPTCHA_KEY_SECRET', 'secret_key')

        result = verify_captcha('test_response')

        assert result is True

    def test_successful_verification_minimum_score(self, mocker):
        """Should return True when captcha score equals minimum score."""
        mock_response = Mock()
        mock_response.json.return_value = {'success': True, 'score': 0.5}

        mocker.patch('utils.support.requests.post', return_value=mock_response)
        mocker.patch('utils.support.settings.CAPTCHA_MIN_SCORE', 0.5)
        mocker.patch('utils.support.settings.G_RECAPTCHA_KEY_SECRET', 'secret_key')

        result = verify_captcha('test_response')

        assert result is True

    def test_failed_verification_low_score(self, mocker):
        """Should return False when captcha score is below minimum."""
        mock_response = Mock()
        mock_response.json.return_value = {'success': True, 'score': 0.3}

        mocker.patch('utils.support.requests.post', return_value=mock_response)
        mocker.patch('utils.support.settings.CAPTCHA_MIN_SCORE', 0.5)
        mocker.patch('utils.support.settings.G_RECAPTCHA_KEY_SECRET', 'secret_key')

        result = verify_captcha('test_response')

        assert result is False

    def test_failed_verification_success_false(self, mocker):
        """Should return False when captcha response success is False."""
        mock_response = Mock()
        mock_response.json.return_value = {'success': False, 'score': 0.9}

        mocker.patch('utils.support.requests.post', return_value=mock_response)
        mocker.patch('utils.support.settings.CAPTCHA_MIN_SCORE', 0.5)
        mocker.patch('utils.support.settings.G_RECAPTCHA_KEY_SECRET', 'secret_key')

        result = verify_captcha('test_response')

        assert result is False

    def test_timeout_exception(self, mocker):
        """Should return False when requests timeout occurs."""
        from requests import Timeout

        mocker.patch('utils.support.requests.post', side_effect=Timeout)
        mocker.patch('utils.support.settings.CAPTCHA_MIN_SCORE', 0.5)
        mocker.patch('utils.support.settings.G_RECAPTCHA_KEY_SECRET', 'secret_key')

        result = verify_captcha('test_response')

        assert result is False


class TestCaptchaRequired:
    """Tests for the captcha_required decorator."""

    def test_successful_captcha_allows_function_execution(self, mocker):
        """Should execute decorated function when captcha is valid."""
        mocker.patch('utils.support.verify_captcha', return_value=True)

        @captcha_required('redirect_url')
        def test_func(request):
            return 'success'

        mock_request = Mock()
        mock_request.POST.get.return_value = 'captcha_response'

        result = test_func(mock_request)

        assert result == 'success'

    def test_invalid_captcha_redirects(self, mocker):
        """Should redirect when captcha is invalid."""
        mocker.patch('utils.support.verify_captcha', return_value=False)
        mocker.patch('utils.support.messages.error')
        mock_redirect = mocker.patch('utils.support.redirect')

        @captcha_required('redirect_url', 'error_message')
        def test_func(request):
            return 'success'

        mock_request = Mock()
        mock_request.POST.get.return_value = 'captcha_response'

        test_func(mock_request)

        mock_redirect.assert_called_once_with('redirect_url', **{})

    def test_invalid_captcha_with_params(self, mocker):
        """Should redirect with kwargs when params are provided."""
        mocker.patch('utils.support.verify_captcha', return_value=False)
        mocker.patch('utils.support.messages.error')
        mock_redirect = mocker.patch('utils.support.redirect')

        @captcha_required('redirect_url', 'error_message', ('param1', 'param2'))
        def test_func(request, param1=None, param2=None):
            return 'success'

        mock_request = Mock()
        mock_request.POST.get.return_value = 'captcha_response'

        test_func(mock_request, param1='value1', param2='value2')

        mock_redirect.assert_called_once_with('redirect_url', param1='value1', param2='value2')

    def test_invalid_params_raises_typeerror(self):
        """Should raise TypeError when params is not a tuple."""
        with pytest.raises(TypeError, match='params must be a tuple'):

            @captcha_required('redirect_url', params='not_a_tuple')
            def test_func(request):
                return 'success'


class TestUpdateChangedFields:
    """Tests for the update_changed_fields function."""

    def test_updates_changed_fields_and_saves(self, mocker):
        """Should update only changed fields and save model."""
        mock_model = Mock()
        mock_model.field1 = 'old_value'
        mock_model.field2 = 'same_value'

        # Mock hasattr to return True for both fields
        mocker.patch(
            'utils.support.hasattr', side_effect=lambda obj, attr: attr in ['field1', 'field2']
        )
        # Mock getattr
        mocker.patch(
            'utils.support.getattr', side_effect=lambda obj, attr: getattr(mock_model, attr)
        )

        update_data = {'field1': 'new_value', 'field2': 'same_value'}

        result = update_changed_fields(mock_model, update_data)

        assert result == ['field1']
        mock_model.full_clean.assert_called_once()
        mock_model.save.assert_called_once_with(update_fields=['field1'])

    def test_no_changes_returns_empty_list(self, mocker):
        """Should return empty list when no fields changed."""
        mock_model = Mock()
        mock_model.field1 = 'value'

        mocker.patch('utils.support.hasattr', return_value=True)
        mocker.patch('utils.support.getattr', return_value='value')

        update_data = {'field1': 'value'}

        result = update_changed_fields(mock_model, update_data)

        assert result == []
        mock_model.full_clean.assert_not_called()
        mock_model.save.assert_not_called()

    def test_validation_error_during_full_clean(self, mocker):
        """Should raise ValidationError when full_clean fails."""
        mock_model = Mock()
        mock_model.field1 = 'old_value'
        mock_model.full_clean.side_effect = ValidationError('Invalid')

        mocker.patch('utils.support.hasattr', return_value=True)
        mocker.patch('utils.support.getattr', return_value='old_value')

        update_data = {'field1': 'new_value'}

        with pytest.raises(ValidationError):
            update_changed_fields(mock_model, update_data)

    def test_false_value_does_not_update_field(self, mocker):
        """Should not update field when new value is falsy."""
        mock_model = Mock()
        mock_model.field1 = 'old_value'

        mocker.patch('utils.support.hasattr', return_value=True)
        mocker.patch('utils.support.getattr', return_value='old_value')

        update_data = {'field1': ''}  # falsy value

        result = update_changed_fields(mock_model, update_data)

        assert result == []


class TestModelToEntity:
    """Tests for the model_to_entity function."""

    def test_successful_conversion_simple_fields(self, mocker):
        """Should convert model with simple fields to entity."""
        # Mock entity class
        mock_entity_cls = Mock()
        mock_entity_cls.safe_validate.return_value = Result.Ok('entity_instance')

        # Mock model with _meta
        mock_model = Mock()
        mock_meta = Mock()
        mock_field1 = Mock()
        mock_field1.name = 'field1'
        mock_field1.get_internal_type.return_value = 'CharField'
        mock_field2 = Mock()
        mock_field2.name = 'field2'
        mock_field2.get_internal_type.return_value = 'IntegerField'
        mock_meta.concrete_fields = [mock_field1, mock_field2]
        mock_meta.many_to_many = []
        mock_model._meta = mock_meta

        # Mock getattr for field values
        mocker.patch(
            'utils.support.getattr',
            side_effect=lambda obj, name: {'field1': 'value1', 'field2': 42}[name],
        )

        result = model_to_entity(mock_model, mock_entity_cls)

        assert result.is_ok()
        assert result.unwrap() == 'entity_instance'
        mock_entity_cls.safe_validate.assert_called_once_with({
            'field1': 'value1',
            'field2': 42,
        })

    def test_none_charfield_converts_to_empty_string(self, mocker):
        """Should convert None CharField/TextField values to empty strings."""
        mock_entity_cls = Mock()
        mock_entity_cls.safe_validate.return_value = Result.Ok('entity_instance')

        mock_model = Mock()
        mock_meta = Mock()
        mock_field = Mock()
        mock_field.name = 'field1'
        mock_field.get_internal_type.return_value = 'CharField'
        mock_meta.concrete_fields = [mock_field]
        mock_meta.many_to_many = []
        mock_model._meta = mock_meta

        mocker.patch('utils.support.getattr', return_value=None)

        result = model_to_entity(mock_model, mock_entity_cls)

        mock_entity_cls.safe_validate.assert_called_once_with({'field1': ''})

    def test_datetime_with_midnight_time_converts_to_date(self, mocker):
        """Should convert datetime with midnight time to date only."""
        mock_entity_cls = Mock()
        mock_entity_cls.safe_validate.return_value = Result.Ok('entity_instance')

        mock_model = Mock()
        mock_meta = Mock()
        mock_field = Mock()
        mock_field.name = 'field1'
        mock_field.get_internal_type.return_value = 'DateTimeField'
        mock_meta.concrete_fields = [mock_field]
        mock_meta.many_to_many = []
        mock_model._meta = mock_meta

        midnight_datetime = datetime(2023, 1, 1, 0, 0, 0)
        mocker.patch('utils.support.getattr', return_value=midnight_datetime)

        result = model_to_entity(mock_model, mock_entity_cls)

        mock_entity_cls.safe_validate.assert_called_once_with({'field1': date(2023, 1, 1)})

    def test_image_field_file_converts_to_name(self, mocker):
        """Should convert ImageFieldFile to its name."""
        mock_entity_cls = Mock()
        mock_entity_cls.safe_validate.return_value = Result.Ok('entity_instance')

        mock_model = Mock()
        mock_meta = Mock()
        mock_field = Mock()
        mock_field.name = 'field1'
        mock_meta.concrete_fields = [mock_field]
        mock_meta.many_to_many = []
        mock_model._meta = mock_meta

        mock_image_file = Mock(spec=ImageFieldFile)
        mock_image_file.name = 'image.jpg'
        mocker.patch('utils.support.getattr', return_value=mock_image_file)
        mocker.patch(
            'utils.support.isinstance',
            side_effect=lambda obj, cls: isinstance(obj, ImageFieldFile)
            if cls == ImageFieldFile
            else False,
        )

        result = model_to_entity(mock_model, mock_entity_cls)

        mock_entity_cls.safe_validate.assert_called_once_with({'field1': 'image.jpg'})

    def test_none_image_field_converts_to_empty_string(self, mocker):
        """Should convert None ImageFieldFile to empty string."""
        mock_entity_cls = Mock()
        mock_entity_cls.safe_validate.return_value = Result.Ok('entity_instance')

        mock_model = Mock()
        mock_meta = Mock()
        mock_field = Mock()
        mock_field.name = 'field1'
        mock_field.get_internal_type.return_value = (
            'CharField'  # Make it CharField so it goes to the None check
        )
        mock_meta.concrete_fields = [mock_field]
        mock_meta.many_to_many = []
        mock_model._meta = mock_meta

        mocker.patch('utils.support.getattr', return_value=None)
        mocker.patch(
            'utils.support.isinstance', side_effect=lambda obj, cls: cls == ImageFieldFile
        )

        result = model_to_entity(mock_model, mock_entity_cls)

        mock_entity_cls.safe_validate.assert_called_once_with({'field1': ''})

    def test_entity_validation_failure(self, mocker):
        """Should return Err when entity validation fails."""
        mock_entity_cls = Mock()
        mock_entity_cls.safe_validate.return_value = Result.Err('validation_error')

        mock_model = Mock()
        mock_meta = Mock()
        mock_meta.concrete_fields = []
        mock_meta.many_to_many = []
        mock_model._meta = mock_meta

        result = model_to_entity(mock_model, mock_entity_cls)

        assert result.is_err()
        assert 'Failed to convert model to entity' in result.unwrap_err().msg


class TestModelsToEntities:
    """Tests for the models_to_entities function."""

    def test_successful_conversion_multiple_models(self, mocker):
        """Should convert multiple models successfully."""
        mock_entity_cls = Mock()

        # Mock model_to_entity to return success for both models
        mock_entity1 = Mock()
        mock_entity2 = Mock()
        mocker.patch(
            'utils.support.model_to_entity',
            side_effect=[Result.Ok(mock_entity1), Result.Ok(mock_entity2)],
        )

        mock_queryset = [Mock(), Mock()]  # Two mock models

        result = models_to_entities(mock_queryset, mock_entity_cls)

        assert result.is_ok()
        assert result.unwrap() == [mock_entity1, mock_entity2]

    def test_error_propagation_on_single_failure(self, mocker):
        """Should return Err when any model conversion fails."""
        mock_entity_cls = Mock()

        mock_error = Mock()
        mocker.patch(
            'utils.support.model_to_entity',
            side_effect=[
                Result.Ok(Mock()),
                Result.Err('conversion_error', src_error=mock_error),
            ],
        )

        mock_queryset = [Mock(), Mock()]

        result = models_to_entities(mock_queryset, mock_entity_cls)

        assert result.is_err()
        assert 'Failed to convert models to entities' in result.unwrap_err().msg


class TestEntityToModel:
    """Tests for the entity_to_model function."""

    def test_successful_creation_new_entity(self, mocker):
        """Should create new model instance when entity.id is None."""
        mock_entity = Mock(spec=BaseEntity)
        mock_entity.id = None
        mock_entity.model_dump.return_value = {'field1': 'value1', 'field2': 42}

        mock_model_cls = Mock()

        result = entity_to_model(mock_entity, mock_model_cls)

        assert result.is_ok()
        mock_model_cls.assert_called_once_with(field1='value1', field2=42)

    def test_successful_update_existing_entity(self, mocker):
        """Should update existing model instance when entity.id exists."""
        mock_entity = Mock(spec=BaseEntity)
        mock_entity.id = 123
        mock_entity.model_dump.return_value = {'field1': 'value1', 'field2': 42}

        mock_existing_instance = Mock()
        mock_model_cls = Mock()
        mock_model_cls.objects.get.return_value = mock_existing_instance

        # Mock setattr to track calls
        setattr_calls = []

        def mock_setattr(obj, name, value):
            setattr_calls.append((name, value))
            return None

        mocker.patch('utils.support.setattr', side_effect=mock_setattr)

        result = entity_to_model(mock_entity, mock_model_cls)

        assert result.is_ok()
        assert result.unwrap() == mock_existing_instance
        mock_model_cls.objects.get.assert_called_once_with(id=123)
        assert ('field1', 'value1') in setattr_calls
        assert ('field2', 42) in setattr_calls

    def test_exclude_lists_from_model_data(self, mocker):
        """Should exclude list values from model data (for ManyToMany)."""
        mock_entity = Mock(spec=BaseEntity)
        mock_entity.id = None
        mock_entity.model_dump.return_value = {'field1': 'value1', 'many_field': [1, 2, 3]}

        mock_model_cls = Mock()

        result = entity_to_model(mock_entity, mock_model_cls)

        mock_model_cls.assert_called_once_with(field1='value1')

    def test_dict_with_id_converts_to_foreign_key(self, mocker):
        """Should convert dict with 'id' to foreign key field."""
        mock_entity = Mock(spec=BaseEntity)
        mock_entity.id = None
        mock_entity.model_dump.return_value = {'fk_field': {'id': 456}}

        mock_model_cls = Mock()

        result = entity_to_model(mock_entity, mock_model_cls)

        mock_model_cls.assert_called_once_with(fk_field_id=456)

    def test_exclude_id_from_model_data(self, mocker):
        """Should exclude 'id' field from model data."""
        mock_entity = Mock(spec=BaseEntity)
        mock_entity.id = None
        mock_entity.model_dump.return_value = {'id': 123, 'field1': 'value1'}

        mock_model_cls = Mock()

        result = entity_to_model(mock_entity, mock_model_cls)

        mock_model_cls.assert_called_once_with(field1='value1')

    def test_general_exception_handling(self, mocker):
        """Should return Err for any unexpected exception."""
        mock_entity = Mock(spec=BaseEntity)
        mock_entity.id = None
        mock_entity.model_dump.return_value = {'field1': 'value1'}

        mock_model_cls = Mock()
        mock_model_cls.side_effect = Exception('Unexpected error')

        result = entity_to_model(mock_entity, mock_model_cls)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Unexpected error'

    def test_update_nonexistent_entity(self, mocker):
        """Should return Err when trying to update a non-existent model instance."""

        # Create custom DoesNotExist exception
        class FakeDoesNotExist(Exception):
            pass

        mock_entity = Mock(spec=BaseEntity)
        mock_entity.id = 999
        mock_entity.model_dump.return_value = {'field1': 'value1'}

        mock_model_cls = Mock()
        mock_model_cls.DoesNotExist = FakeDoesNotExist
        mock_model_cls.objects.get.side_effect = FakeDoesNotExist('Not found')

        result = entity_to_model(mock_entity, mock_model_cls)

        assert result.is_err()
        assert 'Instance with id 999 not found for update' in result.unwrap_err().msg


class TestModelValidate:
    """Tests for the model_validate function."""

    def test_successful_validation(self):
        """Should return Ok when model validation succeeds."""
        mock_model = Mock()
        mock_model.full_clean.return_value = None

        result = model_validate(mock_model)

        assert result.is_ok()
        assert result.unwrap() == mock_model

    def test_validation_error_propagation(self):
        """Should return Err when ValidationError occurs."""
        mock_model = Mock()
        validation_error = ValidationError('Field is required')
        mock_model.full_clean.side_effect = validation_error

        result = model_validate(mock_model)

        assert result.is_err()
        assert result.unwrap_err().src_error == validation_error


class TestGetAvailableDatesMessage:
    """Tests for the get_available_dates_message function."""

    def test_consecutive_reservations_no_gaps(self):
        """Should return message with checkout date when reservations are consecutive."""
        reservation1 = Mock(spec=ReservationEntity)
        reservation1.checkout = date(2023, 1, 5)
        reservation2 = Mock(spec=ReservationEntity)
        reservation2.checkin = date(2023, 1, 6)
        reservation2.checkout = date(2023, 1, 10)

        reservations = [reservation1, reservation2]

        result = get_available_dates_message(reservations)

        assert result.is_ok()
        assert 'apartir de' in result.unwrap()
        assert '10/01/2023' in result.unwrap()

    def test_reservations_with_gaps(self):
        """Should return message with available date ranges when there are gaps."""
        reservation1 = Mock(spec=ReservationEntity)
        reservation1.checkout = date(2023, 1, 5)  # Start available from day after checkout
        reservation2 = Mock(spec=ReservationEntity)
        reservation2.checkin = date(2023, 1, 10)
        reservation2.checkout = date(2023, 1, 15)

        reservations = [reservation1, reservation2]

        result = get_available_dates_message(reservations)

        assert result.is_ok()
        assert '05/01/2023 a 09/01/2023' in result.unwrap()
        assert 'apartir de' in result.unwrap()
        assert '15/01/2023' in result.unwrap()

    def test_single_reservation(self):
        """Should handle single reservation correctly."""
        reservation = Mock(spec=ReservationEntity)
        reservation.checkout = date(2023, 1, 10)

        reservations = [reservation]

        result = get_available_dates_message(reservations)

        assert result.is_ok()
        assert '10/01/2023.' in result.unwrap()
