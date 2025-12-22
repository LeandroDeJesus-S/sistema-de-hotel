import pytest
from django.db import models
from utils.models.middleware import ResizeImageMiddleware


class MockImageFile:
    """Mock Django image file with path and _committed."""

    def __init__(self, path='/tmp/test.jpg'):
        self.path = path
        self._committed = True


def test_resizes_on_create_with_create_only_true(mocker):
    resize_mock = mocker.patch('utils.support.resize_image')
    middleware = ResizeImageMiddleware('image', 100, 200, create_only=True)

    class TestModel(models.Model):
        image = models.ImageField()

        class Meta:
            app_label = 'test'

    instance = TestModel()
    instance.image = MockImageFile()
    middleware.before_save(instance, is_create=True)
    resize_mock.assert_called_once_with('/tmp/test.jpg', 100, 200)


def test_skips_resize_on_update_with_create_only_true(mocker):
    resize_mock = mocker.patch('utils.support.resize_image')
    middleware = ResizeImageMiddleware('image', 100, 200, create_only=True)

    class TestModel(models.Model):
        image = models.ImageField()

        class Meta:
            app_label = 'test'

    instance = TestModel()
    instance.image = MockImageFile()
    middleware.before_save(instance, is_create=False)
    resize_mock.assert_not_called()


def test_resizes_on_create_and_update_with_create_only_false(mocker):
    resize_mock = mocker.patch('utils.support.resize_image')
    middleware = ResizeImageMiddleware('image', 100, 200, create_only=False)

    class TestModel(models.Model):
        image = models.ImageField()

        class Meta:
            app_label = 'test'

    instance = TestModel()
    instance.image = MockImageFile()

    # Test create
    middleware.before_save(instance, is_create=True)
    resize_mock.assert_called_once_with('/tmp/test.jpg', 100, 200)

    resize_mock.reset_mock()

    # Test update
    middleware.before_save(instance, is_create=False)
    resize_mock.assert_called_once_with('/tmp/test.jpg', 100, 200)


def test_skips_if_field_missing(mocker):
    resize_mock = mocker.patch('utils.support.resize_image')
    middleware = ResizeImageMiddleware('image', 100, 200)

    class TestModel(models.Model):
        # No image field
        class Meta:
            app_label = 'test'

    instance = TestModel()
    middleware.before_save(instance, is_create=True)
    resize_mock.assert_not_called()


def test_skips_if_field_none(mocker):
    resize_mock = mocker.patch('utils.support.resize_image')
    middleware = ResizeImageMiddleware('image', 100, 200)

    class TestModel(models.Model):
        image = models.ImageField()

        class Meta:
            app_label = 'test'

    instance = TestModel()
    instance.image = None
    middleware.before_save(instance, is_create=True)
    resize_mock.assert_not_called()
