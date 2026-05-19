from tw_guidance_computer.adapters.inbound.alert_overlay import format_alert_overlay
from tw_guidance_computer.domain.models import SafeHarborRoute


class TestFormatAlertOverlay:
    def test_route_found_formatting(self):
        route = SafeHarborRoute(
            destination_sector=100,
            destination_name="The Federation",
            route=[865, 246, 301, 100],
        )
        lines = format_alert_overlay(route, turns_remaining=42)
        assert lines == [
            "TURNS CRITICAL: 42 remaining",
            "",
            "Nearest safe harbor: Sector 100",
            "Route: 865 → 246 → 301 → 100",
            "Distance: 3 hops",
        ]

    def test_already_safe_formatting(self):
        route = SafeHarborRoute(
            destination_sector=1,
            destination_name="Sol",
            route=[1],
        )
        lines = format_alert_overlay(route, turns_remaining=30)
        assert lines == [
            "TURNS CRITICAL: 30 remaining",
            "",
            "You are currently in a safe sector.",
            "(Sol)",
        ]

    def test_no_route_formatting(self):
        lines = format_alert_overlay(None, turns_remaining=15)
        assert lines == [
            "TURNS CRITICAL: 15 remaining",
            "",
            "Uhoh, I think you're in trouble.",
            "No known route to safe space.",
        ]

    def test_long_route_truncation(self):
        route = SafeHarborRoute(
            destination_sector=12,
            destination_name="Safe Zone",
            route=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        )
        lines = format_alert_overlay(route, turns_remaining=20)
        assert lines[2] == "Nearest safe harbor: Sector 12"
        assert lines[3] == "Route: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 ... (4 more)"
        assert lines[4] == "Distance: 11 hops"

    def test_turns_displayed_correctly(self):
        route = SafeHarborRoute(
            destination_sector=50,
            destination_name="Stardock",
            route=[10, 20, 50],
        )
        lines = format_alert_overlay(route, turns_remaining=99)
        assert lines[0] == "TURNS CRITICAL: 99 remaining"
