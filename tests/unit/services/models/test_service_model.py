"""
Tests for the Service model.
"""
import pytest
from PIL import Image
from services.rules import ServiceRules
from services.models import Service
import os
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO


@pytest.mark.django_db
def test_image_is_resized_after_saving(hotel_instance):
    """
    Tests if the image is resized correctly after saving.
    """
    # Arrange
    # Create a dummy image in memory
    image_buffer = BytesIO()
    img = Image.new('RGB', (1000, 1000), color = 'red')
    img.save(image_buffer, format='JPEG')
    image_buffer.seek(0) # Rewind to the beginning of the buffer

    # Simulate an uploaded file
    uploaded_image = SimpleUploadedFile(
        name='test_image.jpg',
        content=image_buffer.getvalue(),
        content_type='image/jpeg'
    )

    service = Service(name='Test Service', presentation_text='Some text', logo=uploaded_image, hotel=hotel_instance)
    service.save()
    service.refresh_from_db()

    # Assert
    assert (service.logo.width, service.logo.height) == ServiceRules.IMG_SIZE


@pytest.mark.django_db
def test_str_method_returns_service_name(hotel_instance):
    """
    Tests if the __str__ method of the Service model returns the service name.
    """
    # Arrange
    service = Service(name='Test Service', presentation_text='Some text', logo='', hotel=hotel_instance)

    # Act
    result = str(service)

    # Assert
    assert result == 'Test Service'
