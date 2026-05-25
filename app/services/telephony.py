"""Telephony dispatcher — selects a provider based on TELEPHONY_PROVIDER."""
from __future__ import annotations

from app.config import get_settings
from app.services.conversation import Session
from app.services import telephony_twilio, telephony_vapi


def place_outbound_call(session: Session) -> str:
    """Place an outbound call via the configured provider. Returns the provider's call id/SID."""
    provider = (get_settings().telephony_provider or "twilio").lower()
    if provider == "vapi":
        return telephony_vapi.place_outbound_call(session)
    if provider == "twilio":
        return telephony_twilio.place_outbound_call(session)
    raise RuntimeError(f"Unknown TELEPHONY_PROVIDER: {provider!r} (expected 'twilio' or 'vapi')")

