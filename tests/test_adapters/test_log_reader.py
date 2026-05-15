"""Tests for the log reader adapter."""


from tw_guidance_computer.adapters.log_reader import TailLogReader, strip_ansi


class TestStripAnsi:
    def test_removes_color_codes(self):
        text = "\x1b[32mGreen\x1b[0m Normal"
        assert strip_ansi(text) == "Green Normal"

    def test_removes_cursor_positioning(self):
        text = "\x1b[5;23HHello"
        assert strip_ansi(text) == "Hello"

    def test_removes_control_characters(self):
        text = "Hello\x07World"
        assert strip_ansi(text) == "HelloWorld"

    def test_preserves_normal_text(self):
        text = "Sector  : 865 in The Rovine Nebulae."
        assert strip_ansi(text) == text


class TestTailLogReader:
    def test_read_full(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text("Sector  : 100 in Test.\n")
        reader = TailLogReader(log)
        text = reader.read_full()
        assert "Sector  : 100 in Test." in text
        reader.close()

    def test_read_new_after_append(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text("initial\n")
        reader = TailLogReader(log)

        # Reader starts at end, so initial content is not returned
        assert reader.read_new() is None

        # Append new data
        with open(log, "a") as f:
            f.write("new data\n")

        text = reader.read_new()
        assert text is not None
        assert "new data" in text
        reader.close()

    def test_has_data(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text("initial\n")
        reader = TailLogReader(log)

        assert not reader.has_data()

        with open(log, "a") as f:
            f.write("more\n")

        assert reader.has_data()
        reader.close()
