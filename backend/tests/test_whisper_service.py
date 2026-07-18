import sys
import types
from pathlib import Path


whisperx_stub = types.ModuleType("whisperx")
whisperx_stub.load_audio = lambda path: path
sys.modules.setdefault("whisperx", whisperx_stub)

import backend.services.whisper_service as whisper_service


def test_build_sentence_segments_falls_back_to_regex():
    text = "Hello world. This is a second sentence!"

    segments = whisper_service.build_sentence_segments(text)

    assert segments == ["Hello world.", "This is a second sentence!"]


def test_write_ass_subtitles_creates_ass_file(tmp_path: Path):
    segments = [
        {"start": 0.0, "end": 1.5, "text": "Hello world", "speaker": "SPEAKER_01"},
        {"start": 1.5, "end": 3.0, "text": "Second line", "speaker": "SPEAKER_02"},
    ]
    output_path = tmp_path / "example.ass"

    result_path = whisper_service.write_ass_subtitles(segments, output_path)

    assert result_path == output_path
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "Dialogue:" in content
