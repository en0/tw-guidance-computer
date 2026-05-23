from tw_guidance_computer.adapters.inbound.sync_modal import format_sync_modal


class TestFormatSyncModal:
    def test_none_returns_empty(self):
        assert format_sync_modal(None) == []

    def test_progress_status(self):
        lines = format_sync_modal("Exporting sectors...")
        assert lines == ["Exporting sectors..."]

    def test_done_status(self):
        lines = format_sync_modal("Done.")
        assert lines == ["Done."]

    def test_failure_status(self):
        lines = format_sync_modal("Push failed: server unreachable")
        assert lines == ["Push failed: server unreachable"]

    def test_transmitting_status(self):
        lines = format_sync_modal("Transmitting...")
        assert lines == ["Transmitting..."]
