from fastapi import APIRouter, HTTPException, Request
from backend.core.dependencies import require_user
from backend.services.historico_service import summary, history_field

router = APIRouter()

@router.get("/api/profiles/{pk}/summary")
def get_summary(request: Request, pk: str):
    user = require_user(request)
    try: return summary(user, pk)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/profiles/{pk}/history/{field}")
def get_history_field(request: Request, pk: str, field: str):
    user = require_user(request)
    allowed = {"seguidores", "seguindo", "biografia", "total_posts", "total_reels", "total_destaques", "privado", "verificado", "memorializado"}
    if field not in allowed: raise HTTPException(status_code=400, detail="Campo de histórico inválido.")
    try: return history_field(user, pk, field)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))
