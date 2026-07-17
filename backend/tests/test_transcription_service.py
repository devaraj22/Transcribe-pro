from backend.services.transcription_service import normalize_speaker_label


def test_normalize_speaker_label_uses_stable_speaker_names():
    speaker_lookup = {}

    assert normalize_speaker_label("SPEAKER_00", speaker_lookup) == "SPEAKER_01"
    assert normalize_speaker_label("Speaker 1", speaker_lookup) == "SPEAKER_01"
    assert normalize_speaker_label("speaker-2", speaker_lookup) == "SPEAKER_02"
    assert normalize_speaker_label("UNKNOWN", speaker_lookup) == "SPEAKER_03"


def test_normalize_speaker_label_can_use_explicit_fallback_index():
    speaker_lookup = {}

    assert normalize_speaker_label("SPEAKER_00", speaker_lookup, fallback_index=2) == "SPEAKER_02"
    assert normalize_speaker_label("SPEAKER_00", speaker_lookup, fallback_index=3) == "SPEAKER_03"
