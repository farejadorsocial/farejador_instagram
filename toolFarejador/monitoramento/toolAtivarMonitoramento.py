from datetime import datetime
import json
import os
from pathlib import Path


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


def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)


def salvar_dados_json(dados,caminho):
    with open(caminho,"w",encoding="utf-8") as arquivo:
        json.dump(dados,arquivo,ensure_ascii=False,indent=4)


def criando_registro_monitorar_perfil(selecionado,monitorando):
    pk = selecionado['perfil']['pk']
    username = selecionado['perfil']['username']
    nome = selecionado['perfil']['nome']
    return {
        'pk':pk,
        'username':username,
        'nome':nome,
        'sleep':10,
        'monitorando':monitorando,
        'atualizado':datetime.now().isoformat()
    }


def _sincronizar_postgresql(cliente_usuario, dados):
    """Persiste o estado do monitoramento no PostgreSQL."""
    from backend.database.sync import sincronizar_monitoramento
    sincronizar_monitoramento(cliente_usuario, dados)


def lista_perfil_monitorados(cliente_usuario):
    """Retorna monitoramentos do PostgreSQL, usando JSON apenas como fallback legado."""
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import Session
        from backend.database.connection import get_engine
        from backend.database.models import Monitoramento

        with Session(get_engine()) as session:
            registros = session.scalars(
                select(Monitoramento)
                .where(Monitoramento.cliente_usuario == cliente_usuario)
                .order_by(Monitoramento.id)
            ).all()
            if registros:
                return [
                    r.dados or {
                        'pk': r.instagram_pk,
                        'username': r.username,
                        'monitorando': r.monitorando,
                        'sleep': r.sleep,
                    }
                    for r in registros
                ]
    except Exception as erro:
        print(f"[postgres] Falha ao consultar monitoramentos: {erro}")

    lista = []
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_monitorar = caminho_dados_usuario(cliente_usuario, 'monitoramento')
    if not caminho_monitorar.exists():
        return []
    for i in caminho_monitorar.glob("*.json"):
        try:
            dados = carregar_dados(i)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(dados, dict):
            lista.append(dados)
    return lista


def monitorar_perfil(cliente_usuario,selecionado,monitorando=False):
    resultado = criando_registro_monitorar_perfil(selecionado,monitorando)
    pk = resultado['pk']

    # PostgreSQL primeiro: alteração persistente confirmada no banco.
    _sincronizar_postgresql(cliente_usuario, resultado)

    # Espelho JSON legado durante a transição.
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_monitorar = caminho_dados_usuario(cliente_usuario, 'monitoramento', f'{pk}.json')
    caminho_monitorar.parent.mkdir(parents=True,exist_ok=True)
    salvar_dados_json(resultado,caminho_monitorar)
    return resultado


if __name__ == "__main__":
    cliente_usuario = 'admin'
    selecionado = {'perfil': {'pk': 65832742299, 'username': 'thallyta.isabelly', 'nome': 'T'}}
    monitorar = monitorar_perfil(cliente_usuario,selecionado,monitorando=True)
    lista_monitoramento_perfil = lista_perfil_monitorados(cliente_usuario)
