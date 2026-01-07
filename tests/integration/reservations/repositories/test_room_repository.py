import pytest
from reservations.infra.repo import RoomRepository
from reservations.domain.entities import Room, RoomClass
from reservations.models import Room as RoomModel
from decimal import Decimal

@pytest.mark.django_db
class TestRoomRepository:
    @pytest.fixture
    def repo(self):
        return RoomRepository()

    def test_find_by_id_success(self, repo, room_model_instance):
        """Should return a Room entity when a valid ID is provided."""
        result = repo.find_by_id(room_model_instance.id)

        assert result.is_ok()
        room_entity = result.unwrap()
        assert room_entity.id == room_model_instance.id
        assert room_entity.number == room_model_instance.number

    def test_find_by_id_not_found(self, repo):
        """Should return an error when the room ID does not exist."""
        result = repo.find_by_id(9999)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Room not found'

    def test_fetch_all(self, repo, room_model_instance):
        """Should return a list of all Room entities."""
        result = repo.fetch_all()

        assert result.is_ok()
        rooms = result.unwrap()
        assert len(rooms) >= 1
        assert any(r.id == room_model_instance.id for r in rooms)

    def test_fetch_all_with_benefits(self, repo, room_model_instance, benefit_model_instance):
        """Should return Room entities including their associated benefits."""
        room_model_instance.benefits.add(benefit_model_instance)

        result = repo.fetch_all(with_benefits=True)

        assert result.is_ok()
        rooms = result.unwrap()
        target_room = next(r for r in rooms if r.id == room_model_instance.id)
        assert len(target_room.benefits) >= 1
        assert any(b.id == benefit_model_instance.id for b in target_room.benefits)

    def test_fetch_all_benefits(self, repo, benefit_model_instance):
        """Should return a list of all Benefit entities."""
        result = repo.fetch_all_benefits()

        assert result.is_ok()
        benefits = result.unwrap()
        assert len(benefits) >= 1
        assert any(b.id == benefit_model_instance.id for b in benefits)

    def test_fetch_all_classes(self, repo, room_class_model_instance):
        """Should return a list of all RoomClass entities."""
        result = repo.fetch_all_classes()

        assert result.is_ok()
        classes = result.unwrap()
        assert len(classes) >= 1
        assert any(c.id == room_class_model_instance.id for c in classes)

    def test_save_new_room(self, repo, hotel_model_instance, room_class_model_instance):
        """Should successfully save a new Room entity to the database."""
        # We need a domain entity to save
        from home.domain.entities import Hotel as HotelEntity
        hotel_entity = HotelEntity.safe_create(
            id=hotel_model_instance.id,
            name=hotel_model_instance.name,
            slogan=hotel_model_instance.slogan,
            presentation_text=hotel_model_instance.presentation_text
        ).unwrap()

        room_class_entity = RoomClass.safe_create(
            id=room_class_model_instance.id,
            name=room_class_model_instance.name
        ).unwrap()

        new_room = Room.safe_create(
            number="888",
            adults_capacity=2,
            children_capacity=1,
            size=30,
            daily_price=Decimal("250.00"),
            short_desc="New room",
            long_desc="Long description",
            room_class=room_class_entity,
            hotel=hotel_entity
        ).unwrap()

        result = repo.save(new_room)

        assert result.is_ok()
        saved_room = result.unwrap()
        assert saved_room.id is not None
        assert RoomModel.objects.filter(id=saved_room.id).exists()

    def test_fetch_all_exception(self, repo, mocker):
        mocker.patch.object(RoomModel.objects, 'select_related', side_effect=Exception("DB Error"))
        result = repo.fetch_all()
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch rooms'

    def test_fetch_all_conversion_error(self, repo, room_model_instance, mocker):
        from exc import Result
        mocker.patch('reservations.infra.repo.model_to_entity', return_value=Result.Err("Conversion error"))
        result = repo.fetch_all()
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch rooms'

    def test_fetch_all_benefits_exception(self, repo, mocker):
        from reservations.models import Benefit
        mocker.patch.object(Benefit.objects, 'all', side_effect=Exception("DB Error"))
        result = repo.fetch_all_benefits()
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch benefits'

    def test_fetch_all_classes_exception(self, repo, mocker):
        from reservations.models import Class
        mocker.patch.object(Class.objects, 'all', side_effect=Exception("DB Error"))
        result = repo.fetch_all_classes()
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch room classes'

    def test_save_conversion_error(self, repo, hotel_model_instance, room_class_model_instance, mocker):
        from home.domain.entities import Hotel as HotelEntity
        from exc import Result

        hotel_entity = HotelEntity.safe_create(
            id=hotel_model_instance.id, name=hotel_model_instance.name, slogan=hotel_model_instance.slogan,
            presentation_text=hotel_model_instance.presentation_text).unwrap()
        room_class_entity = RoomClass.safe_create(id=room_class_model_instance.id, name=room_class_model_instance.name).unwrap()
        new_room = Room.safe_create(
            number="999", adults_capacity=2, children_capacity=1, size=30, daily_price=Decimal("250.00"),
            short_desc="New", long_desc="Long", room_class=room_class_entity, hotel=hotel_entity
        ).unwrap()

        mocker.patch('reservations.infra.repo.entity_to_model', return_value=Result.Err("Conversion error"))
        result = repo.save(new_room)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to convert room entity to model'

    def test_save_validation_error(self, repo, hotel_model_instance, room_class_model_instance, mocker):
        from home.domain.entities import Hotel as HotelEntity
        from exc import Result
        from django.core.exceptions import ValidationError

        hotel_entity = HotelEntity.safe_create(
            id=hotel_model_instance.id, name=hotel_model_instance.name, slogan=hotel_model_instance.slogan,
            presentation_text=hotel_model_instance.presentation_text).unwrap()
        room_class_entity = RoomClass.safe_create(id=room_class_model_instance.id, name=room_class_model_instance.name).unwrap()
        new_room = Room.safe_create(
            number="999", adults_capacity=2, children_capacity=1, size=30, daily_price=Decimal("250.00"),
            short_desc="New", long_desc="Long", room_class=room_class_entity, hotel=hotel_entity
        ).unwrap()

        mock_model = mocker.Mock()
        mock_model.full_clean.side_effect = ValidationError("Invalid")
        mocker.patch('reservations.infra.repo.entity_to_model', return_value=Result.Ok(mock_model))

        result = repo.save(new_room)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Invalid room'

    def test_save_db_error(self, repo, hotel_model_instance, room_class_model_instance, mocker):
        from home.domain.entities import Hotel as HotelEntity
        from exc import Result

        hotel_entity = HotelEntity.safe_create(
            id=hotel_model_instance.id, name=hotel_model_instance.name, slogan=hotel_model_instance.slogan,
            presentation_text=hotel_model_instance.presentation_text).unwrap()
        room_class_entity = RoomClass.safe_create(id=room_class_model_instance.id, name=room_class_model_instance.name).unwrap()
        new_room = Room.safe_create(
            number="999", adults_capacity=2, children_capacity=1, size=30, daily_price=Decimal("250.00"),
            short_desc="New", long_desc="Long", room_class=room_class_entity, hotel=hotel_entity
        ).unwrap()

        mock_model = mocker.Mock()
        mock_model.save.side_effect = Exception("DB Error")
        mocker.patch('reservations.infra.repo.entity_to_model', return_value=Result.Ok(mock_model))

        result = repo.save(new_room)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not save room'
