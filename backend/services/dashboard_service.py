from backend.repositories.perfil_repository import get_saved_profiles
from backend.repositories.feed_repository import get_feed_all
from backend.services.common import PUBLIC_CLIENTE, limitar
from backend.services.feed_service import feed_publico, carregar_config_atualizacao_paginas


def dashboard(cliente_usuario):
    profiles = get_saved_profiles(cliente_usuario)
    active = sum(1 for x in profiles if x["monitoramento"].get("monitorando") is True)
    paused = max(0, len(profiles) - active)
    dados_feed = get_feed_all(cliente_usuario)
    movements = sum(1 for x in dados_feed if x.get("movimento") is True)
    last = dados_feed[0].get("timestamp_capture") if dados_feed else None
    return {
        "usuarios": len(profiles),
        "monitorados": active,
        "pausados": paused,
        "movimentos": movements,
        "eventos": len(dados_feed),
        "ultima_atividade": last,
        "atividade_recente": limitar(cliente_usuario, "atividade_recente", dados_feed, 8),
    }


def public_dashboard():
    profiles = get_saved_profiles(PUBLIC_CLIENTE)
    public_profiles = [p for p in profiles if isinstance(p.get("perfil"), dict)]
    dados_feed = feed_publico()
    active = sum(1 for x in public_profiles if x.get("monitoramento", {}).get("monitorando"))
    return {
        "usuarios": len(public_profiles),
        "monitorados": active,
        "eventos": len(dados_feed),
        "movimentos": sum(1 for x in dados_feed if x.get("movimento") is True),
        "ultima_atividade": dados_feed[0].get("timestamp_capture") if dados_feed else None,
        "atividade_recente": limitar(PUBLIC_CLIENTE, "atividade_recente", dados_feed, 8),
        "perfis_destaque": limitar(PUBLIC_CLIENTE, "usuario_salvos", public_profiles, 10),
    }
