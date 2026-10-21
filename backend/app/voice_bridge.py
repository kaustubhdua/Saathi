import json
import math
from time import perf_counter
from typing import Any, Awaitable, Callable

from .observability import emit_event

from .exotel_stream import decode_media, encode_clear, encode_media, parse_start


def _is_silent(pcm: bytes, *, threshold: int = 450) -> bool:
    """Cheap PCM16 RMS gate for the bounded-turn adapter.

    This is only a turn-boundary heuristic. Sarvam realtime VAD is the
    production replacement and should be preferred once deployed.
    """
    if len(pcm) < 320:
        return False
    samples = memoryview(pcm[: len(pcm) - (len(pcm) % 2)]).cast("h")
    if not samples:
        return False
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    return rms < threshold


async def run_exotel_session(
    websocket: Any,
    *,
    transcribe: Callable[[bytes, int], Awaitable[str]],
    respond: Callable[[str], Awaitable[str]],
    synthesize: Callable[[str, int], Awaitable[bytes]],
    max_turn_seconds: float = 8.0,
    silence_seconds: float = 0.6,
    min_turn_seconds: float = 0.25,
) -> None:
    """Run one bounded-turn bidirectional Exotel media session.

    The adapter uses PCM silence as a conservative turn boundary and flushes
    the final partial turn on stop. It is still not a realtime streaming
    implementation; Sarvam realtime STT + server VAD is the production path.
    """
    if max_turn_seconds <= 0 or silence_seconds <= 0 or min_turn_seconds <= 0:
        raise ValueError("turn timing values must be positive")
    if min_turn_seconds >= max_turn_seconds:
        raise ValueError("min_turn_seconds must be below max_turn_seconds")

    stream_sid: str | None = None
    sample_rate = 8000
    audio_buffer = bytearray()
    silent_bytes = 0
    saw_speech = False
    playback_active = False

    async def process_turn() -> None:
        nonlocal audio_buffer, silent_bytes, saw_speech, playback_active
        if not audio_buffer:
            return
        pcm = bytes(audio_buffer)
        audio_buffer.clear()
        silent_bytes = 0
        saw_speech = False
        turn_started = perf_counter()
        stage_started = perf_counter()
        transcript = await transcribe(pcm, sample_rate)
        stt_ms = round((perf_counter() - stage_started) * 1000, 2)
        if not transcript.strip():
            emit_event(
                "voice.turn.completed",
                pipeline="exotel_bounded",
                outcome="no_transcript",
                stt_ms=stt_ms,
                response_ms=0,
                tts_ms=0,
                total_ms=round((perf_counter() - turn_started) * 1000, 2),
            )
            return
        stage_started = perf_counter()
        reply = await respond(transcript)
        response_ms = round((perf_counter() - stage_started) * 1000, 2)
        if not reply.strip():
            emit_event(
                "voice.turn.completed",
                pipeline="exotel_bounded",
                outcome="no_reply",
                stt_ms=stt_ms,
                response_ms=response_ms,
                tts_ms=0,
                total_ms=round((perf_counter() - turn_started) * 1000, 2),
            )
            return
        stage_started = perf_counter()
        audio = await synthesize(reply, sample_rate)
        tts_ms = round((perf_counter() - stage_started) * 1000, 2)
        if stream_sid and audio:
            playback_active = True
            await websocket.send(encode_media(stream_sid, audio))
        emit_event(
            "voice.turn.completed",
            pipeline="exotel_bounded",
            outcome="spoken" if audio else "no_audio",
            stt_ms=stt_ms,
            response_ms=response_ms,
            tts_ms=tts_ms,
            total_ms=round((perf_counter() - turn_started) * 1000, 2),
        )
        # Exotel can interrupt buffered output when the caller starts speaking again.
        # The next inbound speech frame clears the remote playback buffer.


    async for raw in websocket:
        try:
            event = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue

        event_type = event.get("event")
        if event_type == "connected":
            continue

        if event_type == "start":
            start = parse_start(event)
            if not start.stream_sid or not start.call_sid:
                raise ValueError("invalid_exotel_start_event")
            if start.sample_rate not in {8000, 16000, 24000}:
                raise ValueError("unsupported_exotel_sample_rate")
            stream_sid, sample_rate = start.stream_sid, start.sample_rate
            audio_buffer.clear()
            silent_bytes = 0
            saw_speech = False
            playback_active = False
            continue

        if event_type == "media":
            try:
                pcm = decode_media(event)
            except (ValueError, TypeError):
                continue
            if not pcm:
                continue

            audio_buffer.extend(pcm)
            frame_bytes = max(2, int(sample_rate * 2 * 0.1))
            frame = pcm[-frame_bytes:]
            frame_silent = _is_silent(frame)
            if frame_silent:
                silent_bytes += len(frame)
            else:
                silent_bytes = 0
                if playback_active and stream_sid:
                    await websocket.send(encode_clear(stream_sid))
                    playback_active = False
                saw_speech = True

            duration = len(audio_buffer) / (sample_rate * 2)
            silence_duration = silent_bytes / (sample_rate * 2)
            if saw_speech and duration >= min_turn_seconds and silence_duration >= silence_seconds:
                await process_turn()
            elif duration >= max_turn_seconds:
                await process_turn()
            continue

        if event_type == "stop":
            playback_active = False
            await process_turn()
            break

        # DTMF/mark events are deliberately ignored by the bounded MVP bridge.
        # They remain part of the protocol surface for a future barge-in/handoff path.


async def run_exotel_realtime_session(
    websocket: Any,
    *,
    stt_session: Any,
    respond: Callable[[str], Awaitable[str]],
    synthesize_stream: Callable[[str, int], Any],
) -> None:
    """Run one Exotel session with streaming STT/TTS and deterministic barge-in."""
    import asyncio

    stream_sid: str | None = None
    sample_rate = 8000
    playback_task: asyncio.Task | None = None
    response_task: asyncio.Task | None = None
    reader_task: asyncio.Task | None = None

    async def cancel_playback() -> None:
        nonlocal playback_task
        if playback_task and not playback_task.done():
            playback_task.cancel()
            await asyncio.gather(playback_task, return_exceptions=True)
        playback_task = None
        if stream_sid:
            await websocket.send(encode_clear(stream_sid))

    async def cancel_response() -> None:
        nonlocal response_task
        if response_task and not response_task.done():
            response_task.cancel()
            await asyncio.gather(response_task, return_exceptions=True)
        response_task = None

    async def speak(reply: str) -> None:
        if not stream_sid:
            return
        async for chunk in synthesize_stream(reply, sample_rate):
            if chunk and stream_sid:
                await websocket.send(encode_media(stream_sid, chunk))

    async def process_transcript(transcript: str) -> None:
        if not transcript.strip():
            return
        await cancel_playback()
        reply = await respond(transcript)
        if reply.strip():
            await speak(reply)

    async def start_response(transcript: str) -> None:
        nonlocal response_task
        await cancel_response()
        response_task = asyncio.create_task(process_transcript(transcript))

    async def stt_reader() -> None:
        while True:
            event = await stt_session.receive()
            event_name = event.get("event")
            if event_name == "vad.speech_start":
                await cancel_response()
                await cancel_playback()
            elif event_name == "transcript.final":
                text = str(event.get("text") or "").strip()
                if text:
                    await start_response(text)
            elif event_name == "error" and event.get("is_fatal"):
                raise RuntimeError(
                    f"sarvam_realtime_stt_error:{event.get('code') or 'fatal'}"
                )
            elif event_name == "session.end":
                return

    try:
        async for raw in websocket:
            if reader_task and reader_task.done():
                reader_error = reader_task.exception()
                if reader_error:
                    raise reader_error

            try:
                event = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue

            event_type = event.get("event")
            if event_type == "connected":
                continue

            if event_type == "start":
                start = parse_start(event)
                if not start.stream_sid or not start.call_sid:
                    raise ValueError("invalid_exotel_start_event")
                if start.sample_rate not in {8000, 16000}:
                    raise ValueError("realtime_bridge_requires_8k_or_16k")
                if stream_sid:
                    raise ValueError("duplicate_exotel_start_event")
                stream_sid, sample_rate = start.stream_sid, start.sample_rate
                await stt_session.connect(sample_rate=sample_rate)
                reader_task = asyncio.create_task(stt_reader())
                continue

            if event_type == "media":
                try:
                    pcm = decode_media(event)
                except (ValueError, TypeError):
                    continue
                if pcm:
                    await stt_session.send_audio(pcm)
                continue

            if event_type == "stop":
                end = getattr(stt_session, "end", None)
                if end is not None:
                    await end()
                break

        if reader_task:
            try:
                await asyncio.wait_for(asyncio.shield(reader_task), timeout=2.0)
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                raise exc
        if response_task:
            try:
                await asyncio.wait_for(asyncio.shield(response_task), timeout=5.0)
            except asyncio.TimeoutError:
                await cancel_response()
            except asyncio.CancelledError:
                pass
        if stream_sid:
            await stt_session.close()
    finally:
        if reader_task and not reader_task.done():
            reader_task.cancel()
            await asyncio.gather(reader_task, return_exceptions=True)
        await cancel_response()
        await cancel_playback()
        try:
            await stt_session.close()
        except Exception:
            pass
