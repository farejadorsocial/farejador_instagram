import json
from pathlib import Path
from typing import Any

from toolFarejador.sistema.toolLimiteExibicaoDados import (
    inicializar_limites_exibicao,
    limite_exibicao,
    limitar_lista,
)

BASE = Path(__file__).resolve().parents[2]
PUBLIC_CLIENTE = "publico"

inicializar_limites_exibicao()


def path(*parts):
    return BASE.joinpath(*parts)


def load_json(p, default=None):
    p = Path(p)
    if not p.exists():
        return [] if default is None else default
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return [] if default is None else default


def save_json(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def normalizar_username(username):
    return str(username or "").strip().lstrip("@").lower()


def data_root(cliente_usuario):
    """Retorna a raiz de dados do cliente.

    O cliente público é um espelho administrativo armazenado em
    sistema/dados/publico; os clientes autenticados usam
    sistema/user/<cliente>/dados.
    """
    if cliente_usuario == PUBLIC_CLIENTE:
        return BASE / "sistema" / "dados" / "publico"
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    return Path(caminho_dados_usuario(cliente_usuario))


def limitar(cliente_usuario, chave, dados, fallback=10):
    try:
        return limitar_lista(cliente_usuario, chave, dados, fallback)
    except Exception:
        return list(dados or [])[:fallback]


def limite(cliente_usuario, chave, fallback=10):
    try:
        return int(limite_exibicao(cliente_usuario, chave, fallback))
    except Exception:
        return fallback


def safe_number(value):
    try:
        if value is None or value == "":
            return 0
        return float(value)
    except (TypeError, ValueError):
        return 0


def history_values(historico, field):
    saida = []
    for item in historico or []:
        if not isinstance(item, dict):
            continue
        perfil = item.get("perfil", {}) or {}
        if field not in perfil:
            continue
        saida.append({
            "timestamp": item.get("timestamp_capture"),
            "valor": perfil.get(field),
        })
    return saida


def biography_history(historico):
    eventos = []
    anterior = None
    for item in historico or []:
        if not isinstance(item, dict):
            continue
        perfil = item.get("perfil", {}) or {}
        atual = perfil.get("biografia") or ""
        if anterior is not None and atual != anterior:
            eventos.append({
                "timestamp": item.get("timestamp_capture"),
                "anterior": anterior,
                "atual": atual,
            })
        anterior = atual
    return eventos


def perfil_atual_e_inicial(perfil_salvo, historico):
    perfil_salvo = perfil_salvo or {}
    perfil_base = perfil_salvo.get("perfil", {}) or {}
    snapshots_validos = [
        item for item in historico
        if isinstance(item, dict) and isinstance(item.get("perfil"), dict)
    ]
    if not snapshots_validos:
        return perfil_base, perfil_base
    return snapshots_validos[-1]["perfil"], snapshots_validos[0]["perfil"]
