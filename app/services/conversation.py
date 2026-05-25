"""In-memory conversation session store.

For a production deployment this would be backed by Redis or a database; the
interface is intentionally small so it can be swapped without touching callers.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.scenarios import Scenario, render


END_CALL_TOKEN = "[[END_CALL]]"


@dataclass
class Message:
    role: str  # "system" | "assistant" | "user"
    content: str


@dataclass
class Session:
    id: str
    scenario: Scenario
    variables: Dict[str, str]
    phone_number: str
    history: List[Message] = field(default_factory=list)
    call_sid: Optional[str] = None
    ended: bool = False
    turn_count: int = 0

    def rendered_greeting(self) -> str:
        return render(self.scenario.greeting, self.variables)

    def system_prompt(self) -> str:
        return render(self.scenario.system_prompt, self.variables)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}

    def create(self, scenario: Scenario, variables: Dict[str, str], phone_number: str) -> Session:
        session_id = uuid.uuid4().hex[:12]
        session = Session(
            id=session_id,
            scenario=scenario,
            variables=variables or {},
            phone_number=phone_number,
        )
        session.history.append(Message(role="system", content=session.system_prompt()))
        # Seed the assistant's opening line so the LLM has full context.
        session.history.append(Message(role="assistant", content=session.rendered_greeting()))
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)


# Module-level singleton (suitable for single-process dev / demo).
store = SessionStore()
