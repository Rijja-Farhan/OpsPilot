"""Webhook trigger (spec-a7 'Triggers'): POST /events validates the event and admits it to the durable queue. It returns at once;
the worker (`python -m opspilot.ambient serve`) does the work."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from opspilot.ambient.events import Event
from opspilot.ambient.queue import Intake


def create_app(store, audit, intake: Intake | None = None) -> FastAPI:
    app = FastAPI(title="OpsPilot ambient intake")
    intake = intake or Intake(store, audit)

    @app.post("/events", status_code=202)
    async def post_event(request: Request):
        try:
            raw = await request.json()
            event = Event.model_validate(raw)
        except (ValidationError, ValueError) as e:
            audit.append(None, "validate", "rejected", tier="auto", actor="webhook", reason="invalid_event", detail_text=str(e)[:200])
            return JSONResponse(status_code=422, content={"error": {"code": "invalid_event", "message": "event failed validation"}})
        event = event.model_copy(update={"source": "webhook"})
        return intake.admit(event)

    @app.get("/health")
    async def health():
        return {"queue_depth": store.depth(), "pending_approvals": len(store.approvals("pending")), "alerts": len(store.alerts())}

    return app
