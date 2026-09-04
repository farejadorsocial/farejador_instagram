from backend.services.common import PUBLIC_CLIENTE, data_root, load_json
from toolFarejador.perfis.toolRemoverPerfil import carregar_dados_perfil_salvos
from toolFarejador.monitoramento.toolAtivarMonitoramento import lista_perfil_monitorados


def get_saved_profiles(cliente_usuario):
    if cliente_usuario == PUBLIC_CLIENTE:
        pasta = data_root(cliente_usuario) / "perfil_salvos"
        pasta_monitoramento = data_root(cliente_usuario) / "monitoramento"
        items = []
        if pasta.exists():
            for arquivo in sorted(pasta.glob("*.json")):
                dados = load_json(arquivo, None)
                if isinstance(dados, dict):
                    items.append(dados)

        monitoring = {}
        if pasta_monitoramento.exists():
            for arquivo in pasta_monitoramento.glob("*.json"):
                dados = load_json(arquivo, None)
                if isinstance(dados, dict):
                    monitoring[str(dados.get("pk"))] = dados

        return [
            {
                "perfil": item.get("perfil", {}),
                "monitoramento": monitoring.get(
                    str(item.get("perfil", {}).get("pk")),
                    {"monitorando": False, "sleep": 10},
                ),
                "caminho_historico_salvo": item.get("caminho_historico_salvo"),
            }
            for item in items
        ]

    result = carregar_dados_perfil_salvos(cliente_usuario)
    profiles = []
    monitoring = {
        str(x.get("pk")): x for x in lista_perfil_monitorados(cliente_usuario)
    }

    for item in result.get("dados_perfil", []):
        perfil = item.get("perfil", {})
        pk = str(perfil.get("pk"))
        profiles.append({
            "perfil": perfil,
            "monitoramento": monitoring.get(
                pk,
                {"monitorando": False, "sleep": 10},
            ),
            "caminho_historico_salvo": item.get("caminho_historico_salvo"),
        })

    return profiles


def get_profile_by_pk(cliente_usuario, pk):
    return load_json(data_root(cliente_usuario) / "perfil_salvos" / f"{pk}.json", {})


def get_history(cliente_usuario, pk):
    return load_json(data_root(cliente_usuario) / "historico" / f"{pk}.json", [])
