from backend.repositories.perfil_repository import get_profile_by_pk, get_history as repository_get_history
from backend.services.common import perfil_atual_e_inicial
from toolFarejador.monitoramento.toolResultadoMonitoramento import analisando_comportamento


def summary(cliente_usuario, pk):
    saved = get_profile_by_pk(cliente_usuario, pk)
    historico = get_history(cliente_usuario, pk)
    if not saved and not historico:
        raise ValueError("Perfil não encontrado.")

    perfil_atual, perfil_inicial = perfil_atual_e_inicial(saved, historico)
    if historico:
        resumo = analisando_comportamento(historico, cliente_usuario)
    else:
        resumo = {"timiline": [], "historico": {}}

    timeline = resumo.get("timiline", resumo.get("timeline", []))
    history_by_field = resumo.get("historico", {})
    deltas = {}
    for field in ["seguidores", "seguindo", "total_posts", "total_reels", "total_destaques"]:
        current = perfil_atual.get(field, 0)
        initial = perfil_inicial.get(field, current)
        try:
            delta = current - initial
        except TypeError:
            delta = 0
        deltas[field] = {"inicial": initial, "atual": current, "variacao": delta}

    return {
        "perfil": perfil_atual,
        "deltas": deltas,
        "timeline": timeline,
        "historico": history_by_field,
        "eventos": len(timeline),
        "capturas": len(historico),
    }


def get_history(cliente_usuario, pk):
    return repository_get_history(cliente_usuario, pk)


def history_field(cliente_usuario, pk, field):
    data = summary(cliente_usuario, pk)
    values = data.get("historico", {}).get(field, [])
    return {"perfil": data["perfil"], "field": field, "values": values}
