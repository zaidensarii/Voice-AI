# Voice AI Agent

A production-minded **outbound voice agent** built with **FastAPI**.
It places a real phone call to a number you enter from a minimal web UI, then holds a context-aware, two-way conversation driven by an LLM — for example, confirming an attendee's registration for an upcoming event.

You can run it in either of two telephony modes:

- **`twilio`** — Pipeline: **Twilio** (PSTN + streaming STT) + **OpenAI** (LLM) + **ElevenLabs** (TTS, optional). Maximum control.
- **`vapi`** — managed end-to-end via **Vapi**. One API key + a phone number id from the Vapi dashboard; STT/LLM/TTS/PSTN all handled by Vapi.

Switch with a single env var: `TELEPHONY_PROVIDER=twilio` or `vapi`.

---

## Features

- **Minimal single-page UI** — enter a phone number, pick a scenario, fill scenario variables, click *Place call*.
- **Dynamic scenario registry** — scenarios are pure data (persona, greeting, system prompt, variables). Add a new outbound campaign without touching the call engine.
- **Context-aware conversation** — full chat history (system + assistant + user) is sent to the LLM on every turn, so the agent remembers what was said.
- **LLM-controlled hangup** — the model emits a `[[END_CALL]]` control token (stripped before speech) to end the call cleanly when the goal is achieved.
- **Pluggable TTS** — uses ElevenLabs if `ELEVENLABS_API_KEY` is set, otherwise falls back transparently to Twilio's neural `<Say>` voice.
- **Clean FastAPI structure** — `routers/` (HTTP surface) + `services/` (telephony, LLM, TTS, session store) + `scenarios.py` (data) + `config.py` (env).

---

## Setup

### 1. Prerequisites

- Python **3.11+**
- A **Twilio** account with a voice-capable phone number
- An **OpenAI** API key
- *(Optional)* an **ElevenLabs** API key for premium TTS
- **ngrok** (or any HTTPS tunnel) so Twilio can reach your local webhooks

### 2. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# then edit .env and fill in the required values
```

| Variable | Required | Notes |
|---|---|---|
| `TELEPHONY_PROVIDER` | yes | `twilio` (self-built) or `vapi` (managed) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | twilio | From the Twilio console |
| `TWILIO_FROM_NUMBER` | twilio | E.164, e.g. `+15555550123` |
| `VAPI_API_KEY` | vapi | Private API key from <https://dashboard.vapi.ai> |
| `VAPI_PHONE_NUMBER_ID` | vapi | Id of a phone number imported/bought in the Vapi dashboard |
| `VAPI_VOICE_PROVIDER` / `VAPI_VOICE_ID` | optional | Defaults to Vapi's built-in `Elliot` voice |
| `VAPI_MODEL_PROVIDER` / `VAPI_MODEL` | optional | Defaults to OpenAI `gpt-4o-mini` |
| `VAPI_TRANSCRIBER_PROVIDER` / `VAPI_TRANSCRIBER_MODEL` | optional | Defaults to Deepgram `nova-2` |
| `OPENAI_API_KEY` | twilio | LLM brain (Vapi uses its own) |
| `OPENAI_MODEL` | optional | Defaults to `gpt-4o-mini` |
| `ELEVENLABS_API_KEY` | optional (twilio) | If empty, falls back to Twilio `<Say>` |
| `ELEVENLABS_VOICE_ID` | optional | Defaults to a public ElevenLabs voice |
| `PUBLIC_BASE_URL` | twilio | Your public HTTPS URL (e.g. an ngrok URL). Optional for Vapi (status webhook only). |

### 4. Expose your server to Twilio
```bash
ngrok http 8000
# copy the https URL into PUBLIC_BASE_URL in .env
```

### 5. Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open <http://localhost:8000>, enter a phone number in E.164 format, fill in the scenario variables, and click **Place call**.

---

## Architecture

```
┌────────────┐     1. POST /api/calls       ┌──────────────────────┐
│  Browser   │ ───────────────────────────► │   FastAPI backend     │
│  (index)   │ ◄─────────── session_id ──── │  app/routers/calls    │
└────────────┘                              └──────────┬───────────┘
                                                       │ 2. REST: place outbound call
                                                       ▼
                                              ┌──────────────────┐
                                              │     Twilio       │
                                              │   (telephony)    │
                                              └────────┬─────────┘
                                                       │ 3. Dial user, POST webhook
                                                       ▼
                          ┌──────────────────────────────────────────────────┐
                          │  /webhooks/voice/{sid}   → greeting + <Gather>    │
                          │  /webhooks/respond/{sid} ← SpeechResult (STT)     │
                          │                          → LLM turn → TTS → TwiML │
                          │  /webhooks/status/{sid}  ← call lifecycle events  │
                          └──────────────────────────────────────────────────┘
                                  │            │              │
                                  │            │              │
                            (Twilio STT)   (OpenAI Chat)  (ElevenLabs TTS
                                                          → /static/audio/*.mp3)
```

**Per-turn flow** (after the user answers the phone):

1. Twilio fetches `POST /webhooks/voice/{session_id}` → we return TwiML that **plays the greeting** (ElevenLabs audio or `<Say>`) and opens a `<Gather input="speech">`.
2. The caller speaks. Twilio performs streaming STT and `POST`s `SpeechResult` to `/webhooks/respond/{session_id}`.
3. The backend appends the utterance to the session history, calls **OpenAI** for the next reply, synthesises **ElevenLabs** TTS (cached on disk), and returns TwiML containing `<Play>` + a new `<Gather>`.
4. When the LLM decides the goal is met, it appends `[[END_CALL]]`. We strip the token, speak the final line, and `<Hangup>`.

### Project layout

```
app/
├── main.py                  # FastAPI app, static mount, router wiring
├── config.py                # Pydantic Settings (env-driven)
├── models.py                # API request/response schemas
├── scenarios.py             # Scenario registry (data only)
├── routers/
│   ├── calls.py             # POST /api/calls, GET /api/scenarios
│   └── webhooks.py          # Twilio TwiML endpoints
├── services/
│   ├── telephony.py         # Provider dispatcher (twilio | vapi)
│   ├── telephony_twilio.py  # Twilio REST wrapper
│   ├── telephony_vapi.py    # Vapi REST wrapper (transient assistant)
│   ├── llm.py               # OpenAI chat completion + end-of-call detection (Twilio path)
│   ├── tts.py               # ElevenLabs synthesis with file cache (Twilio path)
│   └── conversation.py      # In-memory session store
└── static/
    ├── index.html           # Minimal SPA
    └── audio/               # Generated TTS files (gitignored)
```

---

## Design decisions

- **Twilio `<Gather speech>` over Media Streams.** A WebSocket Media Streams pipeline (Deepgram streaming STT + barge-in) gives lower latency, but Twilio's built-in streaming STT is reliable, dead-simple to deploy, and keeps the architecture readable for this task. The `services/` boundary makes it straightforward to swap in a Deepgram WebSocket bridge later without touching scenarios, the LLM, or the UI.
- **Scenarios as data, not code.** Every campaign is just a `Scenario` dataclass with `{greeting, system_prompt, variables}`. The webhooks and LLM service are scenario-agnostic.
- **LLM-emitted end token.** Hard-coding "when to hang up" is brittle. The model decides, signals with `[[END_CALL]]`, and we strip the token before TTS — natural endings, single source of truth.
- **TTS with graceful fallback.** ElevenLabs is preferred for quality; if the key is missing or the API errors, we silently fall back to Twilio's neural voice so the call still completes.
- **Disk-cached TTS.** Identical utterances (e.g. greetings) are synthesised once and replayed, cutting cost and latency.
- **In-memory session store.** Single-process, dependency-free, and isolated behind a small interface — swap for Redis/Postgres without touching call logic.
- **Strict E.164 validation + explicit config errors.** Missing Twilio credentials or a non-HTTPS `PUBLIC_BASE_URL` fail fast at call time with a clear message in the UI.

---

## Vapi quick-start (managed, no ngrok required)

1. Sign up at <https://dashboard.vapi.ai> (free trial includes ~$10 of call credit).
2. **Import or buy a phone number** in the dashboard → *Phone Numbers* tab → copy its **id** (a UUID).
3. Grab your **private API key** from the *API Keys* page.
4. Set in `.env`:
   ```env
   TELEPHONY_PROVIDER=vapi
   VAPI_API_KEY=...
   VAPI_PHONE_NUMBER_ID=...
   ```
5. `uvicorn app.main:app --reload` and open <http://localhost:8000>.

We use Vapi's **transient assistant** feature: instead of pre-creating an assistant in their dashboard, we POST the full agent config (system prompt, first message, voice, model, transcriber) inline with every call — so each scenario in [app/scenarios.py](app/scenarios.py) translates directly into a one-shot Vapi assistant. The UI, scenario registry, and API surface are identical to the Twilio path.

---

## API

### `GET /api/scenarios`
Lists registered scenarios.

### `POST /api/calls`
```json
{
  "phone_number": "+14155551234",
  "scenario_id": "event_confirmation",
  "variables": {
    "agent_name": "Aria",
    "organizer": "Acme Events",
    "attendee_name": "Alex",
    "event_name": "DevCon 2026",
    "event_date": "Saturday, June 6th",
    "event_venue": "Pier 27, San Francisco"
  }
}
```
Returns `{ session_id, call_sid, status }`.

---

## Adding a new scenario

Open [app/scenarios.py](app/scenarios.py) and add an entry to `SCENARIOS`:

```python
SCENARIOS["appointment_reminder"] = Scenario(
    id="appointment_reminder",
    name="Appointment Reminder",
    description="Remind a patient of their upcoming appointment.",
    greeting="Hi {patient_name}, this is {agent_name} calling from {clinic}.",
    system_prompt="You are {agent_name}, calling to remind {patient_name} ...",
    variables=["agent_name", "clinic", "patient_name", "appointment_time"],
)
```

The UI picks it up automatically — no engine changes required.

---

## Troubleshooting

- **"Failed to place call: PUBLIC_BASE_URL must be a reachable https URL"** — set `PUBLIC_BASE_URL` to your ngrok https URL and restart.
- **The call connects but the agent is silent** — your `PUBLIC_BASE_URL` is not reachable from Twilio; check ngrok and that the URL in `.env` matches the active tunnel.
- **ElevenLabs not used** — leave `ELEVENLABS_API_KEY` blank to confirm the Twilio `<Say>` fallback works, then add the key.
