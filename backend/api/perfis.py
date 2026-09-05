from urllib.parse import urlparse, unquote, quote
from urllib.request import Request as UrlRequest, urlopen
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from typing import Optional
import mimetypes
import re
from backend.schemas.perfil import AnalyzeBody, SaveProfileBody, MonitorBody
from backend.core.dependencies import require_user, rate_limit
from backend.services.perfil_service import get_public_profiles as service_get_public_profiles, get_public_profile as service_get_public_profile, public_profile_by_pk as service_public_profile_by_pk, get_private_profile as service_get_private_profile, analyze as service_analyze, save_current_profile as service_save_current_profile, remove_saved as service_remove_saved
from backend.services.monitoramento_service import set_monitoring

router = APIRouter()

_MEDIA_HOSTS = ("instagram.com", "cdninstagram.com", "fbcdn.net", "facebook.com")
_MEDIA_MAX_BYTES = 100 * 1024 * 1024
_MEDIA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36"


def _media_url_permitida(url: str):
    parsed = urlparse(unquote(url))
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not any(host == h or host.endswith("." + h) for h in _MEDIA_HOSTS):
        raise HTTPException(status_code=400, detail="URL de mídia não permitida.")
    return parsed


def _nome_seguro(valor: str, padrao: str):
    texto = re.sub(r"[^A-Za-z0-9._-]+", "_", unquote(str(valor or "")).strip().lstrip("@"))
    texto = re.sub(r"_+", "_", texto).strip("._-")
    return texto[:80] or padrao


def _extensao_midia(content_type: str, url: str, kind: str):
    mapa = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
    }
    if content_type in mapa:
        return mapa[content_type]
    ext = mimetypes.guess_extension(content_type or "")
    if ext:
        return ext
    tipo_url = mimetypes.guess_type(urlparse(url).path)[0]
    ext = mimetypes.guess_extension(tipo_url or "")
    return ext or (".mp4" if kind == "video" else ".jpg")


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
    _media_url_permitida(url)
    try:
        req = UrlRequest(url, headers={"User-Agent": _MEDIA_USER_AGENT, "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8", "Referer": "https://www.instagram.com/"})
        with urlopen(req, timeout=12) as resposta:
            content_type = resposta.headers.get_content_type()
            if not content_type.startswith("image/"): raise HTTPException(status_code=415, detail="O recurso não é uma imagem.")
            data = resposta.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024: raise HTTPException(status_code=413, detail="Imagem muito grande.")
        return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=300"})
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=502, detail=f"Não foi possível carregar a foto: {e}")


@router.get("/api/media-download")
def media_download(request: Request, url: str, pk: str, username: str, kind: str = "image", index: int = 1):
    require_user(request)
    kind = str(kind or "image").lower()
    if kind not in {"profile", "image", "video", "carousel"}:
        raise HTTPException(status_code=400, detail="Tipo de mídia inválido.")
    if not str(pk).strip() or not str(username).strip():
        raise HTTPException(status_code=400, detail="PK e usuário são obrigatórios para o download.")
    _media_url_permitida(url)
    index = max(1, min(int(index or 1), 999))

    perfil_pk = _nome_seguro(pk, "perfil")
    perfil_username = _nome_seguro(username, "usuario")
    if kind == "profile":
        base = f"perfil_{perfil_pk}_{perfil_username}"
    elif kind == "video":
        base = f"post_{perfil_pk}_{perfil_username}_{index:02d}"
    elif kind == "carousel":
        base = f"carrossel_{perfil_pk}_{perfil_username}_{index:02d}"
    else:
        base = f"post_{perfil_pk}_{perfil_username}_{index:02d}"

    try:
        req = UrlRequest(url, headers={
            "User-Agent": _MEDIA_USER_AGENT,
            "Accept": "video/mp4,video/*,image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://www.instagram.com/",
        })
        resposta = urlopen(req, timeout=30)
        content_type = resposta.headers.get_content_type().lower()
        content_length = resposta.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > _MEDIA_MAX_BYTES:
                    resposta.close()
                    raise HTTPException(status_code=413, detail="A mídia é maior que o limite permitido para download.")
            except ValueError:
                content_length = None
        esperado = "video/" if kind == "video" else "image/"
        if not content_type.startswith(esperado):
            resposta.close()
            raise HTTPException(status_code=415, detail=f"O recurso retornado não é um {('vídeo' if kind == 'video' else 'arquivo de imagem')} válido.")
        extensao = _extensao_midia(content_type, url, kind)
        filename = base + extensao

        def stream():
            total = 0
            try:
                while True:
                    chunk = resposta.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > _MEDIA_MAX_BYTES:
                        break
                    yield chunk
            finally:
                resposta.close()

        headers = {
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        }
        if content_length:
            headers["Content-Length"] = content_length
        return StreamingResponse(stream(), media_type=content_type, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Não foi possível baixar a mídia: {e}")
