from app.orchestrator import _weather_reply


def test_weather_reply_uses_tomorrow_forecast_when_requested():
    reply = _weather_reply(
        {
            "temperature_c": 26,
            "rain_probability_pct": 20,
            "tomorrow_date": "2026-10-12",
            "tomorrow_rain_probability_pct": 75,
            "tomorrow_precipitation_mm": 8.5,
        },
        "कल बारिश होगी?",
    )
    assert "2026-10-12" in reply
    assert "75%" in reply
    assert "8.5 mm" in reply


def test_weather_reply_keeps_24_hour_window_for_general_question():
    reply = _weather_reply(
        {"temperature_c": 26, "rain_probability_pct": 20},
        "बारिश की संभावना कितनी है?",
    )
    assert "20%" in reply
    assert "अगले 24 घंटे" in reply



def test_weather_reply_never_turns_missing_probability_into_zero():
    reply = _weather_reply({"temperature_c": 26}, "बारिश की संभावना कितनी है?")
    assert "0%" not in reply
    assert "बारिश की संभावना उपलब्ध नहीं है" in reply


def test_tomorrow_request_does_not_fall_back_to_next_24_hour_probability():
    reply = _weather_reply(
        {"rain_probability_pct": 0, "next_24h_rain_probability_max": 0},
        "कल बारिश होगी?",
    )
    assert "0%" not in reply
    assert "कल की बारिश की संभावना उपलब्ध forecast में नहीं मिली" in reply


def test_weather_reply_includes_provider_observation_time_in_utc():
    reply = _weather_reply(
        {
            "temperature_c": 28,
            "rain_probability_pct": 20,
            "observed_at": "2026-10-16T03:30:00+00:00",
        },
        "आज मौसम कैसा है?",
    )
    assert "2026-10-16 03:30 UTC" in reply
