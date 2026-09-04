from backend.repositories.perfil_repository import get_saved_profiles
from backend.services.common import normalizar_username, safe_number
from backend.services.perfil_service import _profile_view


def _compare_winner(a_value, b_value):
    if a_value > b_value:
        return "a"
    if b_value > a_value:
        return "b"
    return "empate"


def compare_profiles(cliente_usuario, username_a, username_b):
    username_a = normalizar_username(username_a)
    username_b = normalizar_username(username_b)
    if not username_a or not username_b:
        raise ValueError("Escolha dois perfis.")
    if username_a == username_b:
        raise ValueError("Escolha dois perfis diferentes.")

    profiles = get_saved_profiles(cliente_usuario)
    index = {
        normalizar_username(x.get("perfil", {}).get("username")): x
        for x in profiles
    }
    if username_a not in index:
        raise ValueError(f"@{username_a} não está salvo neste usuário.")
    if username_b not in index:
        raise ValueError(f"@{username_b} não está salvo neste usuário.")

    a = _profile_view(cliente_usuario, username_a)
    b = _profile_view(cliente_usuario, username_b)
    pa, pb = a["perfil"], b["perfil"]

    def delta(obj, campo):
        return obj.get("deltas", {}).get(campo, {}).get("variacao", 0) or 0

    campos = ["seguidores", "seguindo", "total_posts", "total_reels", "total_destaques"]
    comparacao = []
    for campo in campos:
        va, vb = safe_number(pa.get(campo)), safe_number(pb.get(campo))
        da, db = safe_number(delta(a, campo)), safe_number(delta(b, campo))
        comparacao.append({
            "campo": campo,
            "nome": campo.replace("total_", "").replace("_", " ").title(),
            "a": va, "b": vb, "variacao_a": da, "variacao_b": db,
            "vencedor": _compare_winner(va, vb),
            "lider_crescimento": _compare_winner(da, db),
        })

    atividade_a, atividade_b = len(a.get("timeline", [])), len(b.get("timeline", []))
    crescimento_a, crescimento_b = safe_number(delta(a, "seguidores")), safe_number(delta(b, "seguidores"))
    inicial_a = safe_number(a.get("deltas", {}).get("seguidores", {}).get("inicial"))
    inicial_b = safe_number(b.get("deltas", {}).get("seguidores", {}).get("inicial"))
    pct_a = crescimento_a / inicial_a * 100 if inicial_a else 0
    pct_b = crescimento_b / inicial_b * 100 if inicial_b else 0

    return {
        "a": a, "b": b, "comparacao": comparacao,
        "resumo": {
            "seguidores": {
                "a": safe_number(pa.get("seguidores")), "b": safe_number(pb.get("seguidores")),
                "vencedor": _compare_winner(safe_number(pa.get("seguidores")), safe_number(pb.get("seguidores"))),
            },
            "crescimento": {
                "a": crescimento_a, "b": crescimento_b,
                "percentual_a": pct_a, "percentual_b": pct_b,
                "vencedor": _compare_winner(pct_a, pct_b),
            },
            "atividade": {"a": atividade_a, "b": atividade_b, "vencedor": _compare_winner(atividade_a, atividade_b)},
            "ritmo": {
                "a": safe_number(a.get("analise", {}).get("tendencia", {}).get("ritmo_atual")),
                "b": safe_number(b.get("analise", {}).get("tendencia", {}).get("ritmo_atual")),
                "vencedor": _compare_winner(
                    safe_number(a.get("analise", {}).get("tendencia", {}).get("ritmo_atual")),
                    safe_number(b.get("analise", {}).get("tendencia", {}).get("ritmo_atual")),
                ),
            },
            "recorde_ganho": {
                "a": safe_number(a.get("analise", {}).get("recordes", {}).get("maior_ganho")),
                "b": safe_number(b.get("analise", {}).get("recordes", {}).get("maior_ganho")),
                "vencedor": _compare_winner(
                    safe_number(a.get("analise", {}).get("recordes", {}).get("maior_ganho")),
                    safe_number(b.get("analise", {}).get("recordes", {}).get("maior_ganho")),
                ),
            },
            "capturas": {"a": a.get("capturas", 0), "b": b.get("capturas", 0)},
        },
    }


def compare_public_profiles(username_a, username_b):
    from backend.services.perfil_service import get_public_profile
    return compare_profiles("publico", username_a, username_b)
