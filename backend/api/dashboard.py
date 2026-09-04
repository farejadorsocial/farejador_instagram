from fastapi import APIRouter, Request, Response
from backend.core.dependencies import current_user, require_user
from backend.services.dashboard_service import dashboard, public_dashboard, carregar_config_atualizacao_paginas
from backend.services.perfil_service import get_saved_profiles
from toolFarejador.sistema.toolLimiteExibicaoDados import carregar_limites_usuario, limitar_lista

router = APIRouter()

@router.get("/api/dashboard")
def get_dashboard(request: Request):
    user = current_user(request)
    return dashboard(user) if user else public_dashboard()

@router.get("/api/config/atualizacao-paginas")
def get_page_update_config():
    return carregar_config_atualizacao_paginas()

@router.get("/api/config/limites-exibicao")
def get_limites_exibicao(request: Request):
    return carregar_limites_usuario(current_user(request) or "publico")

@router.get("/api/health")
def health():
    return {"status": "ok", "version": "1.8.0"}

@router.get("/api/profiles")
def get_profiles(request: Request):
    user = require_user(request)
    return limitar_lista(user, "usuario_salvos", get_saved_profiles(user), 10)
