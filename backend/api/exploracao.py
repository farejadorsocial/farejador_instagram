from fastapi import APIRouter, HTTPException, Request
from backend.core.dependencies import require_user
from backend.services.exploracao_service import public_explore as service_public_explore, explore as service_explore

router = APIRouter()

@router.get("/api/public/explore")
def public_explore(categoria: str = ""):
    return service_public_explore(categoria=categoria)

@router.get("/api/explore")
def explore_private(request: Request, categoria: str = ""):
    user = require_user(request)
    try: return service_explore(user, categoria=categoria)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))
