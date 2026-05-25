"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Telephony provider switch: "twilio" (self-built pipeline) or "vapi" (managed end-to-end)
    telephony_provider: str = "twilio"

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # Vapi (managed STT+LLM+TTS+telephony)
    vapi_api_key: str = ""
    vapi_phone_number_id: str = ""        # id of a phone number you've imported/bought in Vapi
    vapi_voice_provider: str = "vapi"      # e.g. "vapi", "11labs", "playht", "azure"
    vapi_voice_id: str = "Elliot"          # built-in Vapi voice; override per provider as needed
    vapi_model_provider: str = "openai"
    vapi_model: str = "gpt-4o-mini"
    vapi_transcriber_provider: str = "deepgram"
    vapi_transcriber_model: str = "nova-2"
    vapi_max_duration_seconds: int = 600

    # LLM (used by the Twilio pipeline; Vapi uses its own)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # TTS (used by the Twilio pipeline; Vapi uses its own)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_turbo_v2_5"

    # App
    public_base_url: str = "http://localhost:8000"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
