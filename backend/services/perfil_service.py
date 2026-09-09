from backend.repositories.perfil_repository import (
    get_saved_profiles, get_profile_by_pk, get_history, profile_is_saved,
)
from backend.services.common import (
    PUBLIC_CLIENTE, normalizar_username, limitar, limite, safe_number,
    history_values, biography_history,
)
from backend.services.historico_service import summary
from toolFarejador.extracao.toolExtrairUsuarioSemLogin import extraindo_perfil
from toolFarejador.perfis.toolSalvarPerfil import salvar_perfil, salvar_perfil_dados
from toolFarejador.perfis.toolRemoverPerfil import remover_perfil
from toolFarejador.perfis.toolAnalisePerfil import analisar_perfil

PUBLIC_PROFILE_FIELDS = (
    "pk", "username", "nome", "biografia", "privado", "verificado",
    "memorializado", "seguidores", "seguindo", "total_posts",
    "total_reels", "total_destaques", "pronomes", "links", "foto_perfil",
    "categoria",
)


def analyze(cliente_usuario, username):
    username = normalizar_username(username)
    if not username:
        raise ValueError("Informe um usuário do Instagram.")
    return extraindo_perfil(cliente_usuario, username)


def save_current_profile(cliente_usuario, dados_perfil=None):
    if dados_perfil is not None:
        return salvar_perfil_dados(cliente_usuario, dados_perfil)
    return salvar_perfil(cliente_usuario)


def is_profile_saved(cliente_usuario, pk):
    return profile_is_saved(cliente_usuario, pk)


def remove_saved(cliente_usuario, username):
    username = normalizar_username(username)
    if not username:
        raise ValueError("Informe um usuário do Instagram.")

    # O monitoramento ativo bloqueia a remoção do perfil até o vencimento.
    from backend.services.monitoramento_service import verificar_monitoramento_ativo
    verificar_monitoramento_ativo(cliente_usuario, username)

    return remover_perfil(cliente_usuario, username)


def get_profile(cliente_usuario, pk):
    return get_profile_by_pk(cliente_usuario, pk)


def get_saved(cliente_usuario):
    return get_saved_profiles(cliente_usuario)


def get_profile_history(cliente_usuario, pk):
    return get_history(cliente_usuario, pk)


def get_profile_analysis(cliente_usuario, pk):
    return analisar_perfil(cliente_usuario, pk)


def get_profile_summary(cliente_usuario, pk):
    return summary(cliente_usuario, pk)
