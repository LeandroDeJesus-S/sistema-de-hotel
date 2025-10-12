from base.entity import BaseEntity


def test_base_entity_safe_create():
    """"Test that the safe_create method returns a valid entity
    """
    class TestEntity(BaseEntity):
        name: str

    entity = TestEntity.safe_create(name='John Doe')
    assert entity.value.name == 'John Doe'


def test_base_entity_custom_error_messages():
    """"Test if the attribute `__messages` is working correctly.
    """
    class TestEntity(BaseEntity):
        name: str

        _messages = {
            'name': {
                'missing': 'Name is required',
            }
        }

    entity = TestEntity.safe_create()
    assert entity.error.msg == 'Name is required'
