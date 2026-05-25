"""Vapi telephony provider — fully managed STT + LLM + TTS + PSTN.

We use Vapi's "transient assistant" feature: instead of pre-creating an assistant
in the Vapi dashboard, we POST the full agent config (system prompt, first message,
voice, model, transcriber) inline with each call. This keeps our scenario-as-data
design intact — every campaign is still defined entirely in app/scenarios.py.

Docs: https://docs.vapi.ai/api-reference/calls/create
"""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.services.conversation import Session


VAPI_CALLS_URL = "https://api.vapi.ai/call"


def place_outbound_call(session: Session) -> str:
    """Initiate an outbound call via Vapi. Returns the Vapi call id."""
    s = get_settings()
    if not s.vapi_api_key:
        raise RuntimeError("VAPI_API_KEY is not configured.")
    if not s.vapi_phone_number_id:
        raise RuntimeError(
            "VAPI_PHONE_NUMBER_ID is not configured. Import or buy a number in the Vapi "
            "dashboard and copy its id into .env."
        )

    assistant: dict = {
        "firstMessage": session.rendered_greeting(),
        "model": {
            "provider": s.vapi_model_provider,
            "model": s.vapi_model,
            "messages": [{"role": "system", "content": session.system_prompt()}],
            "temperature": 0.6,
        },
        "voice": {
            "provider": s.vapi_voice_provider,
            "voiceId": s.vapi_voice_id,
        },
        "transcriber": {
            "provider": s.vapi_transcriber_provider,
            "model": s.vapi_transcriber_model,
            "language": "en",
        },
        "maxDurationSeconds": s.vapi_max_duration_seconds,
    }

    payload: dict = {
        "phoneNumberId": s.vapi_phone_number_id,
        "customer": {"number": session.phone_number},
        "assistant": assistant,
    }

    headers = {
        "authorization": f"Bearer {s.vapi_api_key}",
        "content-type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(VAPI_CALLS_URL, headers=headers, json=payload)

    if resp.status_code >= 400:
        raise RuntimeError(f"Vapi error {resp.status_code}: {resp.text}")

    data = resp.json()
    call_id = data.get("id")
    if not call_id:
        raise RuntimeError(f"Vapi response missing call id: {data}")
    return call_id
