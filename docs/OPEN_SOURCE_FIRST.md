# Open-source-first, API-key-free core

Saathi's core must run without paid hosted AI credentials. This policy applies to the default developer setup and must remain true in CI.

## Default runtime

- **Reasoning/tool selection:** Ollama running locally with an installed open-weight model (default suggestion: `qwen2.5:3b`). Tool calls are proposals only; deterministic intent classification, capability policy, argument validation and source adapters remain authoritative.
- **Speech in browser:** browser-native speech recognition/synthesis is a convenience fallback, not an offline guarantee. Browser speech engines may use network services depending on browser/OS. Label this clearly in UI.
- **Speech fully offline:** use a locally installed Whisper/whisper.cpp or Vosk model for STT and a locally installed Piper voice for TTS after verifying Hindi/Hinglish quality and each model/voice license. Do not claim this is implemented until the adapters are wired and tested.
- **OCR:** use a locally hosted Tesseract or PaddleOCR installation; keep OCR behind a provider interface, bound upload size and processing time, and label low-confidence extraction for human review.
- **Weather:** Open-Meteo adapter is keyless but needs internet for fresh forecasts. A cached result must show its retrieval time and stale status.
- **Mandi data:** OGD/AGMARKNET access may require a data.gov.in key depending on endpoint/quota. The no-key baseline must gracefully say live mandi prices are unavailable and must never substitute simulated prices without a visible demo label.
- **Scheme information:** use a versioned, source-linked local catalogue and official government links. Display review date and require official confirmation for eligibility and submissions.
- **Persistence and reminders:** a local/self-hosted PostgreSQL deployment can avoid a hosted database vendor API key, but durable consent, household isolation, idempotency, scheduling and delivery tests are still mandatory before enabling household workflows.
- **Telephony:** outbound phone calls are explicitly optional and disabled by default. Browser audio/in-app reminders are the no-key baseline; carrier calling cannot honestly be promised without a compatible provider or user-owned telephony infrastructure.

## Local setup

1. Install Ollama from its official distribution for your OS.
2. Pull a model locally, for example `ollama pull qwen2.5:3b`.
3. Set `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2.5:3b`, and `OLLAMA_BASE_URL=http://127.0.0.1:11434`.
4. Keep `DEMO_MODE=true` for synthetic data and demonstrations. For live public data, explicitly configure live mode and verify each source adapter; do not enable household features merely to make the demo work.
5. If the local model is unavailable, Saathi must continue using deterministic routing where possible and clearly report optional reasoning unavailable. It must not silently fall back to a hosted model.

## Release gates

- CI proves default configuration does not require Gemini, OpenAI, Sarvam, Bhashini, Exotel or Supabase credentials.
- Tests cover Ollama success, no tool call, malformed tool arguments, timeout/connection failure and unsupported tool names.
- Tests prove model output cannot bypass deterministic intent/tool policy, change the caller's household identity, or invent factual source provenance.
- Test no-network mode separately from live public-data mode.
- Verify model and voice licenses, redistribution terms, hardware/latency budget, Hindi/Hinglish quality and accessibility.
- Do not mark local OCR/STT/TTS, durable reminders, live mandi data, or telephony as complete until implementation and acceptance evidence exists.

## Cost and privacy notes

“No API keys” does not mean “no infrastructure cost.” Local inference consumes device/server CPU, RAM, storage and sometimes GPU resources. Public-data adapters still need network access. Keep sensitive audio and documents local by default, avoid logging raw prompts/uploads, and never ship secrets in frontend environment variables.
