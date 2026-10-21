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
