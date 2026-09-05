from backend.repositories.perfil_repository import get_saved_profiles
from backend.repositories.monitoramento_repository import (
    set_monitoring_data, solicitar_atualizacao as repository_solicitar_atualizacao, notificar_movimentos,
)
from backend.services.common import normalizar_username, data_root, load_json
from backend.services.feed_service import feed


def set_monitoring(cliente_usuario, username, enabled):
    username = normalizar_username(username)
    profiles = get_saved_profiles(cliente_usuario)
    selected = next(
        (p for p in profiles if normalizar_username(p["perfil"].get("username")) == username),
        None,
    )
    if not selected:
        raise ValueError("Perfil não encontrado entre os usuários salvos.")

    resultado = set_monitoring_data(cliente_usuario, selected, enabled)
    solicitar_atualizacao()
    if cliente_usuario == "admin":
        from toolFarejador.sistema.toolSistemaPublico import sincronizar_dados_publicos
        sincronizar_dados_publicos()
    return resultado


def refresh_notifications(cliente_usuario):
    usernames = [
        p["perfil"].get("username")
        for p in get_saved_profiles(cliente_usuario)
        if p["perfil"].get("username")
    ]
    if usernames:
        notificar_movimentos(usernames, cliente_usuario)
        try:
            caminho_feed = data_root(cliente_usuario) / "feed" / "feed.json"
            dados_feed = load_json(caminho_feed, [])
            if isinstance(dados_feed, list):
                from backend.database.sync import sincronizar_feed
                sincronizar_feed(cliente_usuario, dados_feed)
        except Exception as erro:
            print(f"[postgres] Falha ao sincronizar feed: {erro}")
    return feed(cliente_usuario)


def analisar_comportamento(*args, **kwargs):
    from toolFarejador.monitoramento.toolResultadoMonitoramento import analisando_comportamento
    return analisando_comportamento(*args, **kwargs)


def solicitar_atualizacao():
    return repository_solicitar_atualizacao()
