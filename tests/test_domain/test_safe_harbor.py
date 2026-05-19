import pytest

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models import SafeHarborRoute, TurnThresholds


class TestSafeHarborRoute:
    def test_construction(self):
        route = SafeHarborRoute(destination_sector=1, destination_name="StarDock", route=[865, 246, 1])
        assert route.destination_sector == 1
        assert route.destination_name == "StarDock"
        assert route.route == [865, 246, 1]

    def test_frozen(self):
        route = SafeHarborRoute(destination_sector=1, destination_name="StarDock", route=[865, 1])
        with pytest.raises(AttributeError):
            route.destination_sector = 2  # type: ignore[misc]

    def test_hops_multiple(self):
        route = SafeHarborRoute(destination_sector=1, destination_name="SD", route=[865, 246, 301, 1])
        assert route.hops == 3

    def test_hops_single_sector(self):
        route = SafeHarborRoute(destination_sector=865, destination_name="Here", route=[865])
        assert route.hops == 0

    def test_invalid_destination_sector(self):
        with pytest.raises(ValidationError, match="destination_sector must be positive"):
            SafeHarborRoute(destination_sector=0, destination_name="X", route=[1])

    def test_empty_route(self):
        with pytest.raises(ValidationError, match="route must not be empty"):
            SafeHarborRoute(destination_sector=1, destination_name="X", route=[])


class TestTurnThresholds:
    def test_defaults(self):
        t = TurnThresholds()
        assert t.yellow == 200
        assert t.red == 100
        assert t.alert == 50

    def test_custom_values(self):
        t = TurnThresholds(yellow=300, red=150, alert=75)
        assert t.yellow == 300
        assert t.red == 150
        assert t.alert == 75

    def test_invalid_ordering_yellow_equals_red(self):
        with pytest.raises(ValidationError, match="must satisfy yellow > red > alert"):
            TurnThresholds(yellow=100, red=100, alert=50)

    def test_invalid_ordering_red_equals_alert(self):
        with pytest.raises(ValidationError, match="must satisfy yellow > red > alert"):
            TurnThresholds(yellow=200, red=50, alert=50)

    def test_invalid_ordering_reversed(self):
        with pytest.raises(ValidationError, match="must satisfy yellow > red > alert"):
            TurnThresholds(yellow=50, red=100, alert=200)

    def test_non_positive_yellow(self):
        with pytest.raises(ValidationError, match="yellow must be positive"):
            TurnThresholds(yellow=0, red=100, alert=50)

    def test_non_positive_red(self):
        with pytest.raises(ValidationError, match="red must be positive"):
            TurnThresholds(yellow=200, red=0, alert=50)

    def test_non_positive_alert(self):
        with pytest.raises(ValidationError, match="alert must be positive"):
            TurnThresholds(yellow=200, red=100, alert=0)
