"""Twilio webhook endpoints — drive the live phone conversation via TwiML."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request, Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.config import get_settings
from app.services import llm, tts
from app.services.conversation import store


log = logging.getLogger("voiceai.webhooks")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _twiml(resp: VoiceResponse) -> Response:
    return Response(content=str(resp), media_type="application/xml")


async def _speak(vr: VoiceResponse, text: str) -> None:
    """Attach speech to the TwiML response — ElevenLabs <Play> if available, else Twilio <Say>."""
    audio_path = await tts.synthesize(text)
    if audio_path:
        public_url = f"{get_settings().public_base_url.rstrip('/')}{audio_path}"
        vr.play(public_url)
    else:
        vr.say(text, voice="Polly.Joanna-Neural")


def _gather(vr: VoiceResponse, action_url: str) -> Gather:
    return vr.gather(
        input="speech",
        action=action_url,
        method="POST",
        speech_timeout="auto",
        speech_model="experimental_conversations",
        language="en-US",
        action_on_empty_result=True,
    )


@router.post("/voice/{session_id}")
async def voice_entry(session_id: str) -> Response:
    """First TwiML returned when Twilio picks up our outbound call."""
    session = store.get(session_id)
    vr = VoiceResponse()
    if not session:
        vr.say("Sorry, this call session is no longer available. Goodbye.")
        vr.hangup()
        return _twiml(vr)

    base = get_settings().public_base_url.rstrip("/")
    gather = _gather(vr, f"{base}/webhooks/respond/{session_id}")
    await _speak(gather, session.rendered_greeting())

    # If the caller says nothing, fall through to a graceful hangup.
    vr.say("I didn't catch that. We'll try you again later. Goodbye.")
    vr.hangup()
    return _twiml(vr)


@router.post("/respond/{session_id}")
async def voice_respond(
    session_id: str,
    SpeechResult: str = Form(default=""),
    Confidence: float = Form(default=0.0),
) -> Response:
    """Twilio posts back the user's speech here. We reply with the next agent turn."""
    session = store.get(session_id)
    vr = VoiceResponse()
    if not session:
        vr.say("Sorry, this session has expired. Goodbye.")
        vr.hangup()
        return _twiml(vr)

    user_text = (SpeechResult or "").strip()
    log.info("session=%s heard=%r confidence=%.2f", session_id, user_text, Confidence)

    if not user_text:
        # Re-prompt once via the same endpoint.
        base = get_settings().public_base_url.rstrip("/")
        gather = _gather(vr, f"{base}/webhooks/respond/{session_id}")
        await _speak(gather, "Sorry, I didn't catch that. Could you repeat?")
        vr.hangup()
        return _twiml(vr)

    reply, should_end = await llm.next_reply(session, user_text)

    if should_end:
        await _speak(vr, reply)
        vr.hangup()
        return _twiml(vr)

    base = get_settings().public_base_url.rstrip("/")
    gather = _gather(vr, f"{base}/webhooks/respond/{session_id}")
    await _speak(gather, reply)
    vr.hangup()
    return _twiml(vr)


@router.post("/status/{session_id}")
async def call_status(session_id: str, request: Request) -> Response:
    form = await request.form()
    log.info("call status session=%s status=%s sid=%s", session_id, form.get("CallStatus"), form.get("CallSid"))
    return Response(status_code=204)
