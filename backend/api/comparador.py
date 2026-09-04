from fastapi import APIRouter, HTTPException, Request
from backend.core.dependencies import require_user
from backend.services.comparador_service import compare_profiles, compare_public_profiles

router = APIRouter()

@router.get("/api/public/compare")
def compare_public(username_a: str, username_b: str):
    if username_a.strip().lower() == username_b.strip().lower(): raise HTTPException(status_code=400, detail="Escolha dois perfis diferentes.")
    try: return compare_public_profiles(username_a, username_b)
    except Exception as e: raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/compare")
def compare_private(request: Request, username_a: str, username_b: str):
    user = require_user(request)
    if username_a.strip().lower() == username_b.strip().lower(): raise HTTPException(status_code=400, detail="Escolha dois perfis diferentes.")
    try: return compare_profiles(user, username_a, username_b)
    except Exception as e: raise HTTPException(status_code=404, detail=str(e))
