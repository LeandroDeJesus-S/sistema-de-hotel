import pytest
from pydantic import ValidationError
from base.entity import BaseEntity
from exc import Result

class SimpleEntity(BaseEntity):
    name: str
    age: int

def test_safe_validate_success():
    result = SimpleEntity.safe_validate({"name": "Test", "age": 20})
    assert result.is_ok()
    assert result.unwrap().name == "Test"

def test_safe_validate_failure(mocker):
    result = SimpleEntity.safe_validate({"name": "Test"}) # age missing
    assert result.is_err()
    assert "age" in result.unwrap_err().msg

def test_safe_validate_empty_errors(mocker):
    # We need a real ValidationError instance because pydantic is strict
    # and we can't easily instantiate it with empty errors normally.
    # But we can catch one and then mock it.
    try:
        SimpleEntity.model_validate({})
    except ValidationError as e:
        mock_e = e

    mocker.patch.object(mock_e, 'errors', return_value=[])
    mocker.patch.object(SimpleEntity, 'model_validate', side_effect=mock_e)

    result = SimpleEntity.safe_validate({})
    assert result.is_err()
    assert result.unwrap_err().msg == 'Validation error'

def test_safe_create():
    result = SimpleEntity.safe_create(name="Test", age=20)
    assert result.is_ok()
    assert result.unwrap().name == "Test"
