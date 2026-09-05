from datetime import datetime
import json
import os
import hashlib
from pathlib import Path


def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)


def salvar_dados_json(dados,caminho):
    with open(caminho,"w",encoding="utf-8") as arquivo:
        json.dump(dados,arquivo,ensure_ascii=False,indent=4)


def caminho_base(*caminho_final, nome_projeto="instagram"):
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
    """Persiste o perfil no PostgreSQL; JSON fica somente como espelho legado."""
    from backend.database.sync import sincronizar_perfil
    sincronizar_perfil(cliente_usuario, dados)


def salvar_perfil_dados(cliente_usuario, dados_perfil):
    """Salva o resultado da análise no PostgreSQL e mantém o JSON legado."""
    if not isinstance(dados_perfil, dict):
        raise ValueError("Dados do perfil inválidos.")
    perfil = dados_perfil.get("perfil")
    if not isinstance(perfil, dict):
        raise ValueError("O resultado da análise não possui o bloco perfil.")
    pk = perfil.get("pk")
    username = perfil.get("username")
    if pk is None or not username:
        raise ValueError("O resultado da análise não possui pk ou username.")

    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_perfil_salvar = caminho_dados_usuario(cliente_usuario, 'perfil_salvos', f'{pk}.json')
    caminho_historico_salvar = caminho_dados_usuario(cliente_usuario, 'historico', f'{pk}.json')

    dados = json.loads(json.dumps(dados_perfil, ensure_ascii=False))
    dados["caminho_perfil_salvo"] = str(caminho_perfil_salvar)
    dados["caminho_historico_salvo"] = str(caminho_historico_salvar)

    # PostgreSQL é a confirmação de persistência.
    _sincronizar_postgresql(cliente_usuario, dados)

    # Espelho legado para compatibilidade durante a transição.
    caminho_perfil_salvar.parent.mkdir(parents=True, exist_ok=True)
    caminho_historico_salvar.parent.mkdir(parents=True, exist_ok=True)
    if not caminho_historico_salvar.exists():
        caminho_historico_salvar.write_text("[]", encoding="utf-8")
    salvar_dados_json(dados, caminho_perfil_salvar)
    return dados


def salvar_perfil(cliente_usuario):
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_log = caminho_dados_usuario(cliente_usuario, 'log', 'perfil.json')
    perfil_log = carregar_dados(caminho_log)
    id_pk = perfil_log['perfil']['pk']

    caminho_perfil_salvar = caminho_dados_usuario(cliente_usuario, 'perfil_salvos', f'{id_pk}.json')
    caminho_historico_salvar = caminho_dados_usuario(cliente_usuario, 'historico', f'{id_pk}.json')
    perfil_log['caminho_perfil_salvo'] = str(caminho_perfil_salvar)
    perfil_log['caminho_historico_salvo'] = str(caminho_historico_salvar)

    # PostgreSQL primeiro.
    _sincronizar_postgresql(cliente_usuario, perfil_log)

    # Espelho legado.
    caminho_perfil_salvar.parent.mkdir(parents=True, exist_ok=True)
    caminho_historico_salvar.parent.mkdir(parents=True, exist_ok=True)
    if not caminho_historico_salvar.exists():
        caminho_historico_salvar.write_text("[]", encoding="utf-8")
    salvar_dados_json(perfil_log, caminho_perfil_salvar)
    return perfil_log


if __name__ == "__main__":
    cliente_usuario = 'admin'
    resultado = salvar_perfil(cliente_usuario)
