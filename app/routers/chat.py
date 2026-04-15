import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, SessionContext
from app.services.agent import AgentOrchestrator
from app.services.auth import get_current_user
from app.services.rate_limit import check_rate_limit

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    ctx: SessionContext = Depends(get_current_user),
):
    if not check_rate_limit(ctx.id_alumno):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    pool = request.app.state.db_pool

    async def event_stream():
        agent = AgentOrchestrator(pool)
        async for event in agent.process(body.mensaje, ctx):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
