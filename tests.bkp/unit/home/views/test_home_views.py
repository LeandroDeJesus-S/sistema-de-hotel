"""
Tests for the home app views.
"""

from reservations.models import Benefit, Room
from services.models import Service


def test_home_view_uses_correct_template(home_response):
    """
    Tests if the home view uses the correct template.
    """
    # Assert
    assert 'static/home/html/home.html' in [t.name for t in home_response.templates]


def test_displayable_benefits_are_sent_to_context(home_response):
    """
    Tests if all benefits marked with displayable_on_homepage=True are sent in the context.
    """
    # Arrange
    expected_benefits = Benefit.objects.filter(displayable_on_homepage=True)

    # Act
    result = home_response.context.get('benefits')

    # Assert
    assert list(result) == list(expected_benefits)


def test_top_4_most_popular_rooms_are_sent_to_context(home_response):
    """
    Tests if the top 4 most popular rooms are sent correctly in the context.
    """
    # Arrange
    expected_rooms = Room.objects.filter(reservation_room__pk__in=[2, 3, 1, 4])

    # Act
    result = home_response.context.get('rooms')

    # Assert
    assert list(result) == list(expected_rooms)


def test_all_services_are_sent_to_context(home_response):
    """
    Tests if all services are sent correctly in the context.
    """
    # Arrange
    expected_services = Service.objects.all()

    # Act
    result = home_response.context.get('services')

    # Assert
    assert list(result) == list(expected_services)
