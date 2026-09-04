import json
from backend.repositories.feed_repository import feed
from backend.services.common import PUBLIC_CLIENTE, limitar, path, load_json


def feed_publico():
    from toolFarejador.sistema.toolSistemaPublico import sincronizar_dados_publicos
    sincronizar_dados_publicos()
    saida = []
    for item in limitar(PUBLIC_CLIENTE, "feed", feed(PUBLIC_CLIENTE), 10):
        saida.append({
            "pk": item.get("pk"),
            "username": item.get("username"),
            "movimento": bool(item.get("movimento")),
            "timestamp_capture": item.get("timestamp_capture"),
            "icone": item.get("icone", "•"),
            "texto": item.get("texto") or item.get("mensagem") or "",
            "mensagem": item.get("mensagem") or item.get("texto") or "",
        })
    return saida


def carregar_config_atualizacao_paginas():
    configuracao = load_json(
        path("sistema", "config", "atualizacao_paginas.json"), {}
    )
    if not isinstance(configuracao, dict):
        configuracao = {}
    feed_config = configuracao.get("feed")
    if not isinstance(feed_config, dict):
        feed_config = {}
    paginas = configuracao.get("paginas")
    if not isinstance(paginas, dict):
        paginas = {}
    return {
        "feed": {
            "intervalo_segundos": max(1, int(feed_config.get("intervalo_segundos", 2))),
            "ativo": bool(feed_config.get("ativo", True)),
        },
        "paginas": {
            "intervalo_segundos": max(2, int(paginas.get("intervalo_segundos", 10))),
        },
    }


def salvar_config_atualizacao_paginas(configuracao):
    if not isinstance(configuracao, dict):
        raise ValueError("Configuração inválida.")
    caminho = path("sistema", "config", "atualizacao_paginas.json")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(f".{caminho.name}.tmp")
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(configuracao, arquivo, ensure_ascii=False, indent=4)
        arquivo.flush()
    temporario.replace(caminho)
    return carregar_config_atualizacao_paginas()
