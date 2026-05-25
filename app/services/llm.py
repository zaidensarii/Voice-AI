"""LLM service — generates the agent's next utterance from the session history."""
from __future__ import annotations

from typing import Tuple

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.conversation import END_CALL_TOKEN, Session


_client: AsyncOpenAI | None = None


def _client_or_none() -> AsyncOpenAI | None:
    global _client
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def next_reply(session: Session, user_utterance: str) -> Tuple[str, bool]:
    """Append the user's utterance, ask the LLM for the next reply.

    Returns (reply_text_for_tts, should_end_call).
    """
    from app.services.conversation import Message  # local import to avoid cycle

    session.history.append(Message(role="user", content=user_utterance))
    session.turn_count += 1

    client = _client_or_none()
    if client is None:
        reply = "Thank you, I have noted that. Have a great day!"
        end = True
    else:
        messages = [{"role": m.role, "content": m.content} for m in session.history]
        completion = await client.chat.completions.create(
            model=get_settings().openai_model,
            messages=messages,
            temperature=0.6,
            max_tokens=120,
        )
        reply = (completion.choices[0].message.content or "").strip()
        end = END_CALL_TOKEN in reply
        reply = reply.replace(END_CALL_TOKEN, "").strip()
        if not reply:
            reply = "Thank you, have a great day!"

    # Safety net: cap conversation length.
    if session.turn_count >= session.scenario.max_turns:
        end = True

    session.history.append(Message(role="assistant", content=reply))
    if end:
        session.ended = True
    return reply, end
