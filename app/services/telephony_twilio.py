"""Twilio telephony provider — places an outbound call that drives our own webhook pipeline."""
from __future__ import annotations

from twilio.rest import Client

from app.config import get_settings
from app.services.conversation import Session


def _client() -> Client:
    s = get_settings()
    if not (s.twilio_account_sid and s.twilio_auth_token):
        raise RuntimeError("Twilio credentials are not configured. Set TWILIO_* env vars.")
    return Client(s.twilio_account_sid, s.twilio_auth_token)


def place_outbound_call(session: Session) -> str:
    """Initiate an outbound Twilio call that hits our TwiML webhooks. Returns the Call SID."""
    s = get_settings()
    if not s.twilio_from_number:
        raise RuntimeError("TWILIO_FROM_NUMBER is not configured.")
    if not s.public_base_url.startswith("http"):
        raise RuntimeError("PUBLIC_BASE_URL must be a reachable https URL for Twilio webhooks.")

    base = s.public_base_url.rstrip("/")
    call = _client().calls.create(
        to=session.phone_number,
        from_=s.twilio_from_number,
        url=f"{base}/webhooks/voice/{session.id}",
        method="POST",
        status_callback=f"{base}/webhooks/status/{session.id}",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
        status_callback_method="POST",
    )
    return call.sid
