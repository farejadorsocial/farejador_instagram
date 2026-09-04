from backend.repositories.perfil_repository import get_saved_profiles
from backend.services.common import PUBLIC_CLIENTE, limitar, safe_number
from backend.services.perfil_service import _public_profile, profile_public_metrics
from toolFarejador.sistema.toolSistemaPublico import sincronizar_dados_publicos


def _explore_for_client(cliente_usuario, public=False):
    if public:
        sincronizar_dados_publicos()
        fonte = PUBLIC_CLIENTE
    else:
        fonte = cliente_usuario

    items = []
    for item in get_saved_profiles(fonte):
        perfil = item.get("perfil", {}) or {}
        if not perfil.get("username"):
            continue
        try:
            items.append(profile_public_metrics(item, fonte))
        except Exception:
            items.append({
                "perfil": _public_profile(perfil),
                "seguidores": safe_number(perfil.get("seguidores")),
                "crescimento": 0, "crescimento_percentual": 0,
                "eventos": 0, "capturas": 0,
                "conteudo": sum(safe_number(perfil.get(k)) for k in ("total_posts", "total_reels", "total_destaques")),
                "atividade": 0, "mudancas_perfil": 0, "mudancas_rede": 0,
                "ritmo_diario": 0, "atividade_score": 0, "descobertas": 0,
            })

    by_growth_pct = sorted(items, key=lambda x: (x["crescimento_percentual"], x["crescimento"], x["seguidores"]), reverse=True)
    by_growth_abs = sorted(items, key=lambda x: (x["crescimento"], x["crescimento_percentual"]), reverse=True)
    by_followers = sorted(items, key=lambda x: x["seguidores"], reverse=True)
    by_activity = sorted(items, key=lambda x: (x["atividade"], x["eventos"], x["capturas"]), reverse=True)
    by_content = sorted(items, key=lambda x: (x["conteudo"], x["atividade"]), reverse=True)
    by_pace = sorted(items, key=lambda x: (x.get("ritmo_diario", 0), x.get("crescimento", 0)), reverse=True)
    by_discoveries = sorted(items, key=lambda x: (x.get("descobertas", 0), x.get("atividade_score", 0)), reverse=True)

    return {
        "total_perfis": len(items),
        "total_eventos": sum(int(x["eventos"]) for x in items),
        "total_capturas": sum(int(x["capturas"]) for x in items),
        "maior_crescimento": limitar(fonte, "explorar", by_growth_pct, 10),
        "maior_crescimento_absoluto": limitar(fonte, "explorar", by_growth_abs, 10),
        "mais_seguidores": limitar(fonte, "explorar", by_followers, 10),
        "mais_ativos": limitar(fonte, "explorar", by_activity, 10),
        "mais_conteudo": limitar(fonte, "explorar", by_content, 10),
        "maior_ritmo": limitar(fonte, "explorar", by_pace, 10),
        "mais_descobertas": limitar(fonte, "explorar", by_discoveries, 10),
    }


def public_explore():
    return _explore_for_client(PUBLIC_CLIENTE, public=True)


def explore(cliente_usuario):
    return _explore_for_client(cliente_usuario, public=False)
