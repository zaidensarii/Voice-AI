"""TTS service.

Primary: ElevenLabs streaming -> MP3 file written under app/static/audio.
Fallback: returns None so the caller can use Twilio's built-in <Say> (Polly).
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings


AUDIO_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(text: str, voice_id: str) -> Path:
    key = hashlib.sha256(f"{voice_id}:{text}".encode("utf-8")).hexdigest()[:24]
    return AUDIO_DIR / f"{key}.mp3"


async def synthesize(text: str) -> Optional[str]:
    """Return a public URL path (e.g. /static/audio/xyz.mp3) or None to fall back to <Say>."""
    settings = get_settings()
    if not settings.elevenlabs_api_key:
        return None

    path = _cache_path(text, settings.elevenlabs_voice_id)
    if not path.exists():
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
        headers = {
            "xi-api-key": settings.elevenlabs_api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": settings.elevenlabs_model_id,
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.75},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                # Soft-fail: caller will fall back to <Say>.
                return None
            path.write_bytes(resp.content)

    # Public URL served by FastAPI's StaticFiles mount.
    return f"/static/audio/{path.name}"
