from urllib.parse import urlparse, unquote
from urllib.request import Request as UrlRequest, urlopen
from fastapi import APIRouter, HTTPException, Request, Response
from typing import Optional
from backend.schemas.perfil import AnalyzeBody, SaveProfileBody, MonitorBody
from backend.core.dependencies import require_user, rate_limit
from backend.services.perfil_service import get_public_profiles as service_get_public_profiles, get_public_profile as service_get_public_profile, public_profile_by_pk as service_public_profile_by_pk, get_private_profile as service_get_private_profile, analyze as service_analyze, save_current_profile as service_save_current_profile, remove_saved as service_remove_saved
from backend.services.monitoramento_service import set_monitoring

router = APIRouter()

@router.get("/api/public/profiles")
def get_public_profiles(search: str = "", limit: int = 100):
    return service_get_public_profiles(search=search, limit=limit)

@router.get("/api/public/profiles/{username}")
def get_public_profile(username: str):
    try: return service_get_public_profile(username)
    except Exception as e: raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/public/profiles/{pk}/analytics")
def get_public_analytics(pk: str):
    try: return service_public_profile_by_pk(pk).get("analise", {})
    except Exception as e: raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/public/profiles/{pk}/summary")
def get_public_summary(pk: str):
    try: return service_public_profile_by_pk(pk)
    except Exception as e: raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/profiles/{username}/view")
def private_profile_view(request: Request, username: str):
    user = require_user(request)
    try: return service_get_private_profile(user, username)
    except Exception as e: raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/profile/analyze")
def do_analyze(request: Request, body: AnalyzeBody):
    user = require_user(request); rate_limit(request, "analyze")
    try:
        resultado = service_analyze(user, body.username)
        if not isinstance(resultado, dict) or not isinstance(resultado.get("perfil"), dict):
            raise ValueError("O Instagram não retornou dados suficientes para esse usuário.")
        return resultado
    except Exception as e: raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/profile/save")
def do_save(request: Request, body: Optional[SaveProfileBody] = None):
    user = require_user(request)
    try: return service_save_current_profile(user, body.dados if body else None)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/profiles/{username}/monitor")
def do_monitor(request: Request, username: str, body: MonitorBody):
    user = require_user(request)
    try: return set_monitoring(user, username, body.monitorando)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.delete("/api/profiles/{username}")
def do_remove(request: Request, username: str):
    user = require_user(request)
    try: return service_remove_saved(user, username)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/profile-image")
def profile_image(url: str):
    parsed = urlparse(unquote(url)); host = (parsed.hostname or "").lower()
    permitidos = ("instagram.com", "cdninstagram.com", "fbcdn.net", "facebook.com")
    if parsed.scheme not in {"http", "https"} or not any(host == h or host.endswith("." + h) for h in permitidos):
        raise HTTPException(status_code=400, detail="URL de imagem não permitida.")
    try:
        req = UrlRequest(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36", "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"})
        with urlopen(req, timeout=12) as resposta:
            content_type = resposta.headers.get_content_type()
            if not content_type.startswith("image/"): raise HTTPException(status_code=415, detail="O recurso não é uma imagem.")
            data = resposta.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024: raise HTTPException(status_code=413, detail="Imagem muito grande.")
        return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=300"})
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=502, detail=f"Não foi possível carregar a foto: {e}")
