"""Scenario registry.

Scenarios are pure data so new outbound campaigns can be added without touching
the call engine. Each scenario defines an agent persona, an opening line, the
LLM system prompt, and the list of variables expected at call time.
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    greeting: str
    system_prompt: str
    variables: List[str] = field(default_factory=list)
    max_turns: int = 12


_EVENT_REG_SYSTEM = """You are {agent_name}, a friendly and concise voice agent calling on behalf of {organizer}.
Your goal: confirm that {attendee_name} is still planning to attend "{event_name}" on {event_date} at {event_venue}.

Conversation policy:
- Speak naturally, one short sentence at a time (this is a phone call, not chat).
- Always wait for the user's reply; never deliver more than ~2 sentences per turn.
- Confirm attendance, capture any change (cancel / reschedule / number of guests), and answer simple questions about the event.
- If the user is busy or asks to call back, politely acknowledge and end the call.
- If you have gathered the confirmation (or a clear decline), thank them and end the call.

End-of-call protocol:
- When the call is complete, your FINAL message MUST end with the exact token [[END_CALL]] on its own.
- Do not say the token out loud — it is a control signal that will be stripped before speech.
"""

_EVENT_REG_GREETING = (
    "Hi, may I speak with {attendee_name}? This is {agent_name} calling from {organizer} "
    "about your registration for {event_name}."
)


SCENARIOS: Dict[str, Scenario] = {
    "event_confirmation": Scenario(
        id="event_confirmation",
        name="Event Registration Confirmation",
        description="Outbound call to confirm an attendee's registration for an upcoming event.",
        greeting=_EVENT_REG_GREETING,
        system_prompt=_EVENT_REG_SYSTEM,
        variables=[
            "agent_name",
            "organizer",
            "attendee_name",
            "event_name",
            "event_date",
            "event_venue",
        ],
    ),
}


DEFAULT_VARIABLES: Dict[str, str] = {
    "agent_name": "Aria",
    "organizer": "Acme Events",
    "attendee_name": "there",
    "event_name": "our upcoming conference",
    "event_date": "this Saturday",
    "event_venue": "the main hall",
}


def get_scenario(scenario_id: str) -> Scenario:
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario: {scenario_id}")
    return SCENARIOS[scenario_id]


def render(template: str, variables: Dict[str, str]) -> str:
    merged = {**DEFAULT_VARIABLES, **(variables or {})}
    # Only the placeholders the template references are required.
    try:
        return template.format(**merged)
    except KeyError as exc:
        missing = exc.args[0]
        merged[missing] = DEFAULT_VARIABLES.get(missing, f"{{{missing}}}")
        return template.format(**merged)
