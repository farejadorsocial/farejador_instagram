from backend.repositories.perfil_repository import (
    get_saved_profiles, get_profile_by_pk, get_history,
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


def remove_saved(cliente_usuario, username):
    username = normalizar_username(username)
    if not username:
        raise ValueError("Perfil inválido para remoção.")
    resultado = remover_perfil(username, cliente_usuario)
    if not resultado.get("removido"):
        raise ValueError("Usuário salvo não encontrado.")
    return resultado


def _public_profile(perfil):
    if not isinstance(perfil, dict):
        return {}
    return {k: perfil.get(k) for k in PUBLIC_PROFILE_FIELDS if k in perfil}


def _public_profile_card(item):
    perfil = _public_profile(item.get("perfil", {}))
    return {
        "perfil": perfil,
        "monitoramento": {
            "monitorando": bool(item.get("monitoramento", {}).get("monitorando")),
        },
    }


def get_public_profiles(search=None, limit=100):
    perfis = [_public_profile_card(p) for p in get_saved_profiles(PUBLIC_CLIENTE)]
    termo = normalizar_username(search) if search else ""
    if termo:
        perfis = [
            p for p in perfis
            if termo in normalizar_username(p["perfil"].get("username"))
            or termo in str(p["perfil"].get("nome", "")).lower()
        ]
    limite_max = min(max(1, int(limit)), limite(PUBLIC_CLIENTE, "usuario_salvos", 10))
    return perfis[:limite_max]


def _find_public_profile(username):
    username = normalizar_username(username)
    for item in get_saved_profiles(PUBLIC_CLIENTE):
        perfil = item.get("perfil", {})
        if normalizar_username(perfil.get("username")) == username:
            return item
    return None


def get_public_profile(username):
    item = _find_public_profile(username)
    if not item:
        raise ValueError("Perfil público não encontrado no Farejador.")
    pk = item.get("perfil", {}).get("pk")
    data = summary(PUBLIC_CLIENTE, pk)
    historico = data.get("historico", {}) or {}
    bruto = get_history(PUBLIC_CLIENTE, pk)
    return {
        "perfil": _public_profile(data.get("perfil", {})),
        "deltas": data.get("deltas", {}),
        "timeline": limitar(PUBLIC_CLIENTE, "timeline", data.get("timeline", []), 10),
        "historico": historico,
        "eventos": data.get("eventos", 0),
        "capturas": data.get("capturas", 0),
        "monitorando": bool(item.get("monitoramento", {}).get("monitorando")),
        "series": {
            campo: limitar(PUBLIC_CLIENTE, "series_historico", history_values(bruto, campo), 10)
            for campo in ("seguidores", "seguindo", "total_posts", "total_reels", "total_destaques")
        },
        "biografia_historico": biography_history(bruto),
        "historico_perfil": {
            campo: limitar(PUBLIC_CLIENTE, "historico_perfil", history_values(bruto, campo), 10)
            for campo in ("biografia", "privado", "verificado", "memorializado", "pronomes", "links")
        },
        "analise": analisar_perfil(bruto, data),
    }


def public_profile_by_pk(pk):
    for item in get_saved_profiles(PUBLIC_CLIENTE):
        if str(item.get("perfil", {}).get("pk")) == str(pk):
            return get_public_profile(item.get("perfil", {}).get("username"))
    raise ValueError("Perfil público não encontrado no Farejador.")


def _profile_view(cliente_usuario, username):
    username = normalizar_username(username)
    item = next(
        (
            x for x in get_saved_profiles(cliente_usuario)
            if normalizar_username(x.get("perfil", {}).get("username")) == username
        ),
        None,
    )
    if not item:
        raise ValueError("Perfil não encontrado entre os seus usuários salvos.")

    pk = item.get("perfil", {}).get("pk")
    data = summary(cliente_usuario, pk)
    historico = get_history(cliente_usuario, pk)
    return {
        "perfil": _public_profile(data.get("perfil", {})),
        "deltas": data.get("deltas", {}),
        "timeline": limitar(PUBLIC_CLIENTE, "timeline", data.get("timeline", []), 10),
        "historico": data.get("historico", {}),
        "eventos": data.get("eventos", 0),
        "capturas": data.get("capturas", 0),
        "monitorando": bool(item.get("monitoramento", {}).get("monitorando")),
        "series": {
            campo: history_values(historico, campo)
            for campo in ("seguidores", "seguindo", "total_posts", "total_reels", "total_destaques")
        },
        "biografia_historico": biography_history(historico),
        "historico_perfil": {
            campo: history_values(historico, campo)
            for campo in ("biografia", "privado", "verificado", "memorializado", "pronomes", "links")
        },
        "analise": analisar_perfil(historico, data),
    }


def get_private_profile(cliente_usuario, username):
    return _profile_view(cliente_usuario, username)


def profile_public_metrics(item, cliente_usuario=PUBLIC_CLIENTE):
    perfil = item.get("perfil", {}) or {}
    pk = perfil.get("pk")
    historico = get_history(cliente_usuario, pk) if pk else []
    try:
        resumo = summary(cliente_usuario, pk) if pk else {}
    except Exception:
        resumo = {}

    deltas = resumo.get("deltas", {}) or {}
    seguidores = safe_number(perfil.get("seguidores"))
    analise = analisar_perfil(historico, resumo)
    crescimento = safe_number(deltas.get("seguidores", {}).get("variacao"))
    inicial = safe_number(deltas.get("seguidores", {}).get("inicial"))
    crescimento_pct = (crescimento / inicial * 100) if inicial > 0 else 0

    timeline = resumo.get("timeline") or resumo.get("timiline") or []
    eventos = len(timeline)
    capturas = len(historico)
    conteudo = sum(safe_number(perfil.get(k)) for k in ("total_posts", "total_reels", "total_destaques"))
    mudancas_perfil = sum(1 for t in timeline if isinstance(t, dict) and t.get("categoria") == "perfil")
    mudancas_rede = sum(1 for t in timeline if isinstance(t, dict) and t.get("categoria") == "rede")
    atividade = eventos + mudancas_perfil + mudancas_rede + max(capturas - 1, 0)
    ritmo = safe_number(analise.get("projecao", {}).get("ritmo_diario"))
    score = safe_number(analise.get("atividade", {}).get("score"))

    return {
        "perfil": _public_profile(perfil),
        "seguidores": seguidores,
        "crescimento": crescimento,
        "crescimento_percentual": crescimento_pct,
        "eventos": eventos,
        "capturas": capturas,
        "conteudo": conteudo,
        "atividade": atividade,
        "mudancas_perfil": mudancas_perfil,
        "mudancas_rede": mudancas_rede,
        "ritmo_diario": ritmo,
        "atividade_score": score,
        "qualidade": analise.get("qualidade", {}),
        "descobertas": len(analise.get("insights", [])),
        "analise": analise,
    }
