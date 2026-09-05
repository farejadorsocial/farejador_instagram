from datetime import datetime
import json
import os
import hashlib
from pathlib import Path


def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)


def salvar_dados_json(dados, caminho):
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)


def caminho_base(*caminho_final, nome_projeto="farejador_instagram"):
    """Retorna caminhos relativos à raiz do projeto."""
    try:
        caminho_atual = Path(__file__).resolve()
    except NameError:
        caminho_atual = Path.cwd().resolve()
    for pasta in [caminho_atual] + list(caminho_atual.parents):
        if pasta.name == nome_projeto:
            return pasta.joinpath(*caminho_final)
    raise FileNotFoundError(f"Não foi encontrada a pasta '{nome_projeto}'.")


def _sincronizar_postgresql(cliente_usuario, dados):
    """Persiste o perfil diretamente no PostgreSQL."""
    from backend.database.sync import sincronizar_perfil
    sincronizar_perfil(cliente_usuario, dados)


def salvar_perfil_dados(cliente_usuario, dados_perfil):
    """Salva o perfil diretamente no PostgreSQL, sem criar espelho JSON."""
    if not isinstance(dados_perfil, dict):
        raise ValueError("Dados do perfil inválidos.")
    perfil = dados_perfil.get("perfil")
    if not isinstance(perfil, dict):
        raise ValueError("O resultado da análise não possui o bloco perfil.")
    pk = perfil.get("pk")
    username = perfil.get("username")
    if pk is None or not username:
        raise ValueError("O resultado da análise não possui pk ou username.")

    dados = json.loads(json.dumps(dados_perfil, ensure_ascii=False))
    dados["caminho_perfil_salvo"] = None
    dados["caminho_historico_salvo"] = None

    _sincronizar_postgresql(cliente_usuario, dados)
    return dados


def salvar_perfil(cliente_usuario):
    """Persiste o perfil do log no PostgreSQL, sem criar arquivos de dados do perfil."""
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_log = caminho_dados_usuario(cliente_usuario, 'log', 'perfil.json')
    perfil_log = carregar_dados(caminho_log)

    id_pk = perfil_log['perfil']['pk']
    perfil_log['caminho_perfil_salvo'] = None
    perfil_log['caminho_historico_salvo'] = None

    _sincronizar_postgresql(cliente_usuario, perfil_log)
    return perfil_log


if __name__ == "__main__":
    cliente_usuario = 'admin'
    resultado = salvar_perfil(cliente_usuario)
