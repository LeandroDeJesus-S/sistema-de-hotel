import pytest
from pydantic import BaseModel, ValidationError

@pytest.fixture
def validate_vo():
    def _validate(vo_type, value):
        class Model(BaseModel):
            v: vo_type
        return Model(v=value).v
    return _validate
