import asyncio
import json
from app.voice_bridge import run_exotel_session

class FakeWS:
    def __init__(self, events):
        self.events=events
        self.sent=[]
    def __aiter__(self):
        return self
    async def __anext__(self):
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)
    async def send(self, value):
        self.sent.append(value)

def test_voice_bridge_uses_injected_pipeline(caplog):
    async def run():
        import base64
        pcm=base64.b64encode(b"a"*16000).decode()
        ws=FakeWS([
            json.dumps({"event":"start","start":{"stream_sid":"MZ1","call_sid":"CA1","media_format":{"sample_rate":"8000"}}}),
            json.dumps({"event":"media","media":{"payload":pcm}}),
            json.dumps({"event":"stop"}),
        ])
        calls=[]
        async def stt(audio, rate): calls.append(("stt",len(audio),rate)); return "मंडी का भाव"
        async def respond(text): calls.append(("llm",text)); return "सत्यापित डेटा उपलब्ध नहीं है।"
        async def tts(text, rate): calls.append(("tts",text,rate)); return b"reply"
        await run_exotel_session(ws,transcribe=stt,respond=respond,synthesize=tts)
        assert calls[0][0]=="stt"
        assert calls[1][0]=="llm"
        assert calls[2][0]=="tts"
        assert ws.sent

    import logging
    caplog.set_level(logging.INFO, logger="saathi")
    asyncio.run(run())
    assert '"event":"voice.turn.completed"' in caplog.text
    assert '"pipeline":"exotel_bounded"' in caplog.text
    assert '"stt_ms":' in caplog.text
    assert '"response_ms":' in caplog.text
    assert '"tts_ms":' in caplog.text


def test_voice_bridge_flushes_on_silence_before_max_turn():
    async def run():
        import base64

        speech = b"\x10\x00" * 4000
        silence = b"\x00\x00" * 5200
        ws = FakeWS([
            json.dumps({"event": "start", "start": {
                "stream_sid": "MZ1", "call_sid": "CA1",
                "media_format": {"sample_rate": "8000"},
            }}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(speech).decode()}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(silence).decode()}}),
            json.dumps({"event": "stop"}),
        ])
        calls = []

        async def stt(audio, rate):
            calls.append(("stt", len(audio), rate))
            return "नमस्ते"

        async def respond(text):
            calls.append(("llm", text))
            return "नमस्ते"

        async def tts(text, rate):
            calls.append(("tts", text, rate))
            return b"reply"

        await run_exotel_session(ws, transcribe=stt, respond=respond, synthesize=tts)
        assert calls[0][0] == "stt"
        assert calls[0][1] < 8_000 * 2 * 2

    asyncio.run(run())


def test_voice_bridge_clears_playback_when_caller_barges_in():
    async def run():
        import base64
        speech = b"\x00\x10" * 1200
        silence = b"\x00\x00" * 6000
        ws = FakeWS([
            json.dumps({"event": "start", "start": {"stream_sid": "MZ1", "call_sid": "CA1", "media_format": {"sample_rate": "8000"}}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(speech).decode()}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(silence).decode()}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(silence).decode()}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(silence).decode()}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(silence).decode()}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(silence).decode()}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(silence).decode()}}),
            json.dumps({"event": "media", "media": {"payload": base64.b64encode(speech).decode()}}),
            json.dumps({"event": "stop"}),
        ])
        async def stt(audio, rate): return "नमस्ते"
        async def respond(text): return "जी"
        async def tts(text, rate): return b"reply"
        await run_exotel_session(ws, transcribe=stt, respond=respond, synthesize=tts)
        assert any(json.loads(item).get("event") == "clear" for item in ws.sent)
    asyncio.run(run())



def test_realtime_voice_bridge_emits_first_audio_and_turn_telemetry(caplog):
    import base64
    import logging
    from app.voice_bridge import run_exotel_realtime_session

    class FakeRealtimeSTT:
        def __init__(self):
            self.events = [
                {"event": "transcript.final", "text": "नमस्ते"},
                {"event": "session.end"},
            ]
            self.connected_rate = None
            self.audio = []
            self.ended = False
            self.closed = False

        async def connect(self, *, sample_rate):
            self.connected_rate = sample_rate

        async def receive(self):
            if self.events:
                return self.events.pop(0)
            await asyncio.sleep(0)
            return {"event": "session.end"}

        async def send_audio(self, pcm):
            self.audio.append(pcm)

        async def end(self):
            self.ended = True

        async def close(self):
            self.closed = True

    async def run():
        pcm = base64.b64encode(b"\\x00\\x10" * 160).decode()
        ws = FakeWS([
            json.dumps({"event": "start", "start": {
                "stream_sid": "MZ1", "call_sid": "CA1",
                "media_format": {"sample_rate": "8000"},
            }}),
            json.dumps({"event": "media", "media": {"payload": pcm}}),
            json.dumps({"event": "stop"}),
        ])
        stt = FakeRealtimeSTT()
        async def respond(text):
            assert text == "नमस्ते"
            return "नमस्कार"
        async def synthesize_stream(text, rate):
            assert text == "नमस्कार"
            assert rate == 8000
            yield b"first-audio"
            yield b"second-audio"

        await run_exotel_realtime_session(
            ws, stt_session=stt, respond=respond,
            synthesize_stream=synthesize_stream,
        )
        assert stt.connected_rate == 8000
        assert stt.audio
        assert stt.ended
        assert stt.closed
        assert any(json.loads(item).get("event") == "media" for item in ws.sent)

    caplog.set_level(logging.INFO, logger="saathi")
    asyncio.run(run())
    assert '"event":"voice.turn.completed"' in caplog.text
    assert '"pipeline":"exotel_realtime"' in caplog.text
    assert '"first_audio_ms":' in caplog.text
    assert '"tts_ms":' in caplog.text
    assert '"total_ms":' in caplog.text
