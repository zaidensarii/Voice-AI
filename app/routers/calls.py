"""Public REST API: list scenarios + trigger outbound calls."""
from fastapi import APIRouter, HTTPException

from app.models import ScenarioSummary, StartCallRequest, StartCallResponse
from app.scenarios import SCENARIOS, get_scenario
from app.services import telephony
from app.services.conversation import store


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/scenarios", response_model=list[ScenarioSummary])
async def list_scenarios() -> list[ScenarioSummary]:
    return [
        ScenarioSummary(id=s.id, name=s.name, description=s.description, variables=s.variables)
        for s in SCENARIOS.values()
    ]


@router.post("/calls", response_model=StartCallResponse)
async def start_call(req: StartCallRequest) -> StartCallResponse:
    try:
        scenario = get_scenario(req.scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not req.phone_number.startswith("+"):
        raise HTTPException(status_code=400, detail="phone_number must be in E.164 format (e.g. +14155551234)")

    session = store.create(scenario=scenario, variables=req.variables or {}, phone_number=req.phone_number)
    try:
        call_sid = telephony.place_outbound_call(session)
    except Exception as exc:  # surface configuration / provider errors as 400
        raise HTTPException(status_code=400, detail=f"Failed to place call: {exc}") from exc

    session.call_sid = call_sid
    return StartCallResponse(session_id=session.id, call_sid=call_sid, status="initiated")
