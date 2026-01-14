import pytest
from django.urls import reverse
from django.http import Http404
from reservations.models import Reservation
from base.dtos import TemplateRenderResultDTO

@pytest.mark.django_db
def test_rooms_list_view(client, room_model_instance):
    """Test that rooms list view renders correctly."""
    response = client.get(reverse('rooms'))
    assert response.status_code == 200
    assert 'rooms.html' in [t.name for t in response.templates]
    # Compare IDs as objects might be different instances
    assert any(r.id == room_model_instance.id for r in response.context['rooms'])

@pytest.mark.django_db
def test_room_detail_view(client, room_model_instance):
    """Test that room detail view renders correctly."""
    response = client.get(reverse('room', kwargs={'pk': room_model_instance.pk}))
    assert response.status_code == 200
    assert 'room.html' in [t.name for t in response.templates]
    # room_model_instance might be different instance, check PK
    assert response.context['room'].id == room_model_instance.id

@pytest.mark.django_db
def test_room_detail_view_404(client):
    """Test that room detail view returns 404 for invalid room."""
    response = client.get(reverse('room', kwargs={'pk': 99999}))
    assert response.status_code == 404

@pytest.mark.django_db
def test_reserve_view_redirect_if_not_authenticated(client, room_model_instance):
    """Test that reserve view redirects unauthenticated users."""
    response = client.get(reverse('reserve', kwargs={'room_pk': room_model_instance.pk}))
    assert response.status_code == 302
    assert 'signin' in response.url

@pytest.mark.django_db
def test_reserve_view_get_success(authenticated_client, room_model_instance):
    """Test that reserve view renders for authenticated users without active reservations."""
    client, user = authenticated_client
    # Ensure user has no active reservations
    Reservation.objects.filter(client=user).delete()

    response = client.get(reverse('reserve', kwargs={'room_pk': room_model_instance.pk}))
    assert response.status_code == 200
    assert 'reserve.html' in [t.name for t in response.templates]

@pytest.mark.django_db
def test_reserve_view_post_success(
    authenticated_client,
    room_model_instance,
    mock_recaptcha,
    reservations_container,
    mock_unit_of_work
):
    """Test successful reservation creation."""
    client, user = authenticated_client
    # Ensure user has no active reservations
    Reservation.objects.filter(client=user).delete()

    from datetime import date, timedelta
    checkin = date.today() + timedelta(days=10)
    checkout = checkin + timedelta(days=5)

    with reservations_container.unit_of_work.override(mock_unit_of_work):
        response = client.post(
            reverse('reserve', kwargs={'room_pk': room_model_instance.pk}),
            {
                'checkin': checkin.strftime('%Y-%m-%d'),
                'checkout': checkout.strftime('%Y-%m-%d'),
                'obs': 'Test reservation',
                'g-recaptcha-response': 'mocked_response'
            }
        )
    # Expect redirect to confirmation or payment
    assert response.status_code == 302
    # Verify reservation was created
    assert Reservation.objects.filter(client=user, room=room_model_instance).exists()

@pytest.mark.django_db
def test_reservations_history_view(authenticated_client, reservation_model_instance):
    """Test reservations history view."""
    client, user = authenticated_client
    # Ensure the reservation belongs to the authenticated user
    reservation_model_instance.client = user
    reservation_model_instance.save()

    response = client.get(reverse('reservations_history'))
    assert response.status_code == 200
    assert 'reservations_history.html' in [t.name for t in response.templates]
    assert any(r.id == reservation_model_instance.id for r in response.context['reservations'])

@pytest.mark.django_db
def test_reservation_history_detail_view(authenticated_client, reservation_model_instance):
    """Test reservation detail view (history)."""
    client, user = authenticated_client
    # Ensure the reservation belongs to the authenticated user
    reservation_model_instance.client = user
    reservation_model_instance.save()

    response = client.get(reverse('reservation_history', kwargs={'pk': reservation_model_instance.pk}))
    assert response.status_code == 200
    assert 'reservation_history.html' in [t.name for t in response.templates]

    # The view returns a DTO in the context
    dto = response.context['reservation']
    assert dto.id == reservation_model_instance.id

@pytest.mark.django_db
def test_reservation_history_detail_other_user_404(authenticated_client, reservation_model_instance, client_model_instance_factory):
    """Test that viewing another user's reservation returns 404."""
    client, user = authenticated_client
    other_user = client_model_instance_factory()

    # Assign reservation to other user
    reservation_model_instance.client = other_user
    reservation_model_instance.save()

    response = client.get(reverse('reservation_history', kwargs={'pk': reservation_model_instance.pk}))
    assert response.status_code == 404

@pytest.mark.django_db
def test_cancel_reservation_view_get(authenticated_client, reservation_model_instance):
    """Test cancel reservation confirmation page."""
    client, user = authenticated_client
    reservation_model_instance.client = user
    reservation_model_instance.status = 'A' # ACTIVE
    reservation_model_instance.save()

    response = client.get(reverse('cancel_reservation', kwargs={'pk': reservation_model_instance.pk}))
    assert response.status_code == 200
    assert 'cancel_reservation.html' in [t.name for t in response.templates]

@pytest.mark.django_db
def test_cancel_reservation_view_post_success(
    authenticated_client,
    reservation_model_instance,
    mock_recaptcha,
    reservations_container,
    mock_unit_of_work
):
    """Test successful reservation cancellation."""
    client, user = authenticated_client
    reservation_model_instance.client = user
    reservation_model_instance.status = 'S' # SCHEDULED (allows cancellation)
    reservation_model_instance.save()

    with reservations_container.unit_of_work.override(mock_unit_of_work):
        response = client.post(
            reverse('cancel_reservation', kwargs={'pk': reservation_model_instance.pk}),
            {
                'reason': 'Changed plans',
                'g-recaptcha-response': 'mocked_response'
            }
        )
    assert response.status_code == 302
    # Verify status changed to Cancelled ('C')
    reservation_model_instance.refresh_from_db()
    assert reservation_model_instance.status == 'C'

@pytest.mark.django_db
def test_rooms_list_view_error(client, reservations_container, mocker):
    """Test rooms list view handles repository error."""
    from exc import Result
    mock_repo = mocker.Mock()
    mock_repo.fetch_all.return_value = Result.Err('Database error')

    with reservations_container.room_repo.override(mock_repo):
        response = client.get(reverse('rooms'))

    assert response.status_code == 200
    assert 'rooms.html' in [t.name for t in response.templates]
    assert list(response.context['rooms']) == []
    # Check for error message
    messages = list(response.context['messages'])
    assert any('Could not load rooms.' in str(m) for m in messages)

@pytest.mark.django_db
def test_reserve_view_setup_error(authenticated_client, room_model_instance, reservations_container, mocker):
    """Test reserve view handles setup error."""
    client, user = authenticated_client
    # Ensure user has no active reservations
    Reservation.objects.filter(client=user).delete()

    from exc import Result
    from reservations.domain.entities import Reservation as ReservationEntity

    # We need to mock room_repo.fetch_all_classes AND reservation_service.can_client_create_reservation
    # because setup runs first, then get() runs which calls service.

    # Mock room_repo for setup error
    mock_room_repo = mocker.Mock()
    mock_room_repo.fetch_all_classes.return_value = Result.Err('Classes load error')

    # We also need to mock find_by_id because InitializeReservationUseCase might use it if we posted,
    # but here we are GETting.

    # However, the view uses @inject on setup.
    # The setup method gets called before get().

    with reservations_container.room_repo.override(mock_room_repo):
        response = client.get(reverse('reserve', kwargs={'room_pk': room_model_instance.pk}))

    assert response.status_code == 200
    assert 'reserve.html' in [t.name for t in response.templates]

    # Check for error message from setup
    messages = list(response.context['messages'])
    assert any('Could not load room classes.' in str(m) for m in messages)

@pytest.mark.django_db
def test_reservations_history_view_error(authenticated_client, reservations_container, mocker):
    """Test reservations history view handles service error."""
    client, user = authenticated_client

    from exc import Result

    # Mock the service method fetch_client_reservation_history
    # We can mock the service itself on the container
    mock_service = mocker.Mock()
    mock_service.fetch_client_reservation_history.return_value = Result.Err('History load error')
    # We also need get_reservations_with_cancellation_info and can_client_create_reservation for context data
    mock_service.get_reservations_with_cancellation_info.return_value = []
    mock_service.can_client_create_reservation.return_value = Result.Ok(False)

    with reservations_container.reservation_service.override(mock_service):
        response = client.get(reverse('reservations_history'))

    assert response.status_code == 200
    assert 'reservations_history.html' in [t.name for t in response.templates]
    assert list(response.context['reservations']) == []

    # Check for error message
    messages = list(response.context['messages'])
    assert any('History load error' in str(m) for m in messages)
