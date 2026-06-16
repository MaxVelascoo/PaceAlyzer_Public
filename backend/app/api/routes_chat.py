from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.orchestrator import handle_message
from db.repositories import get_session_messages
from utils.dates import validate_iso_date
from utils.logger import logger
from utils.request_metrics import clear_request_metrics, get_request_metrics_collector

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not validate_iso_date(req.date):
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")

    try:
        result = handle_message(
            user_id=req.user_id,
            message=req.message,
            date=req.date,
        )
        _emit_request_metrics(http_status=200)
        return ChatResponse(**result)
    except HTTPException as exc:
        _emit_request_metrics(http_status=exc.status_code)
        raise
    except Exception:
        _emit_request_metrics(http_status=500)
        raise


@router.get("/chat/history")
async def chat_history(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id es obligatorio.")

    messages = get_session_messages(user_id)
    return {"messages": messages}


def _emit_request_metrics(http_status: int):
    collector = get_request_metrics_collector()
    if not collector:
        return
    try:
        collector.record_http_status(http_status)
        summary = collector.build_summary()
        logger.request_summary(summary)
    except Exception:
        # Nunca romper la respuesta HTTP por un fallo de métricas
        pass
    finally:
        clear_request_metrics()
