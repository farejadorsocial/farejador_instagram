from fastapi import APIRouter, HTTPException, Request
from backend.core.dependencies import require_user
from backend.schemas.perfil import MonitorBody
from backend.services.monitoramento_service import set_monitoring, refresh_notifications

router = APIRouter()

@router.post("/api/notifications/refresh")
def do_refresh(request: Request):
    user = require_user(request)
    try: return refresh_notifications(user)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))
