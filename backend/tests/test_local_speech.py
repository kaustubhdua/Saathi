import asyncio
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from app import local_speech


def test_local_stt_decodes_audio_and_uses_vosk_model(monkeypatch, tmp_path):
    model_path = tmp_path / "vosk-model-small-hi-0.22"
    (model_path / "am").mkdir(parents=True)
    observed = {"chunks": 0}

    class FakeModel:
        def __init__(self, path):
            observed["model_path"] = path

    class FakeRecognizer:
        def __init__(self, model, sample_rate):
            observed["sample_rate"] = sample_rate

        def AcceptWaveform(self, chunk):
            observed["chunks"] += 1
            return False

        def FinalResult(self):
            return json.dumps({"text": "namaste kisan"})

    monkeypatch.setitem(sys.modules, "vosk", SimpleNamespace(Model=FakeModel, KaldiRecognizer=FakeRecognizer))
    monkeypatch.setattr(local_speech, "_decode_audio", lambda audio, **kwargs: b"\x00\x00" * 5000)
    local_speech._load_vosk_model.cache_clear()
    provider = local_speech.VoskHindiSpeechToTextProvider(str(model_path))
    transcript = asyncio.run(provider.transcribe(b"audio bytes", language="hi-IN"))
    assert transcript == "namaste kisan"
    assert observed["model_path"] == str(model_path)
    assert observed["sample_rate"] == 16000
    assert observed["chunks"] >= 2


def test_local_stt_rejects_unsupported_language_before_decode():
    provider = local_speech.VoskHindiSpeechToTextProvider("/missing/model")
    with pytest.raises(ValueError, match="local_stt_language_not_supported"):
        asyncio.run(provider.transcribe(b"audio", language="fr"))


def test_audio_decoder_bounds_input_and_timeout(monkeypatch):
    provider_error = local_speech.LocalSpeechError
    with pytest.raises(ValueError, match="audio_too_large"):
        local_speech._decode_audio(b"x" * (local_speech.MAX_AUDIO_BYTES + 1), ffmpeg_binary="ffmpeg", timeout_seconds=15)

    monkeypatch.setattr(local_speech.shutil, "which", lambda name: "/usr/bin/ffmpeg")

    def timeout_run(command, **kwargs):
        assert kwargs["timeout"] == 25.0
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(local_speech.subprocess, "run", timeout_run)
    with pytest.raises(provider_error, match="local_audio_decode_timeout"):
        local_speech._decode_audio(b"audio", ffmpeg_binary="ffmpeg", timeout_seconds=100)


def test_local_tts_returns_wav_without_network(monkeypatch):
    monkeypatch.setattr(local_speech.shutil, "which", lambda name: "/usr/bin/espeak-ng")
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout=b"RIFFfake-wav", stderr=b"")

    monkeypatch.setattr(local_speech.subprocess, "run", fake_run)
    provider = local_speech.EspeakHindiTextToSpeechProvider()
    result = asyncio.run(provider.synthesize("नमस्ते किसान", language="hi"))
    assert result.startswith(b"RIFF")
    assert seen["command"][0] == "/usr/bin/espeak-ng"
    assert seen["command"][seen["command"].index("-v") + 1] == "hi"
    assert "नमस्ते किसान" in seen["command"]


def test_local_tts_reports_missing_binary(monkeypatch):
    monkeypatch.setattr(local_speech.shutil, "which", lambda name: None)
    provider = local_speech.EspeakHindiTextToSpeechProvider()
    with pytest.raises(local_speech.LocalSpeechError, match="local_tts_engine_unavailable"):
        asyncio.run(provider.synthesize("नमस्ते", language="hi"))
