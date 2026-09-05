from fastapi import APIRouter, HTTPException, Request, Response
from backend.schemas.auth import AuthBody
from backend.services.auth_service import register, login, logout
from backend.core.dependencies import current_user, dados_acesso_request, cookie_kwargs, rate_limit
from backend.core.visitor import registrar_visitante
from backend.core.config import carregar_permissoes_navegador

router = APIRouter()

@router.get("/api/session")
def session(request: Request, response: Response):
    user = current_user(request)
    if not user:
        try:
            visitante_id = registrar_visitante(request)
            response.set_cookie("farejador_visitante", visitante_id, httponly=True, samesite="lax", max_age=31536000)
        except Exception as erro:
            print(f"[visitante] Falha ao registrar visitante: {erro}")
    return {"autenticado": bool(user), "cliente_usuario": user, "modo_publico": not bool(user), "publico_cliente_usuario": "admin", "versao": request.app.version}

@router.post("/api/auth/register")
def do_register(body: AuthBody, request: Request, response: Response):
    rate_limit(request, "auth")
    if body.password != body.confirmar_senha:
        raise HTTPException(status_code=400, detail="As senhas não conferem.")
    acesso = dados_acesso_request(request, body.dispositivo_cliente)
    try:
        username = register(body.username, body.password, acesso)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    token, _ = login(username, body.password, acesso)
    response.set_cookie("farejador_token", token, **cookie_kwargs())
    return {"ok": True, "cliente_usuario": username}

@router.post("/api/auth/login")
def do_login(body: AuthBody, request: Request, response: Response):
    rate_limit(request, "auth")
    acesso = dados_acesso_request(request, body.dispositivo_cliente)
    try:
        token, username = login(body.username, body.password, acesso)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    response.set_cookie("farejador_token", token, **cookie_kwargs())
    return {"ok": True, "cliente_usuario": username}

@router.post("/api/auth/logout")
def do_logout(request: Request, response: Response):
    token = request.cookies.get("farejador_token")
    if token:
        logout(token)
    response.delete_cookie("farejador_token")
    return {"ok": True}

@router.get("/api/config/permissoes-navegador")
def get_permissoes_navegador():
    return carregar_permissoes_navegador()
