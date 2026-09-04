"""Controle central dos limites de exibição do Farejador."""
import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[2]
SYSTEM_CONFIG = BASE / "sistema" / "config" / "limite_exebicao_dados.json"
SYSTEM_STATE = BASE / "sistema" / "config" / ".limite_exebicao_dados_estado.json"
USER_ROOT = BASE / "sistema" / "user"

LIMITES_PADRAO = {
    "feed": 10,
    "usuario_salvos": 10,
    "atividade_recente": 8,
    "explorar": 10,
    "historico": 10,
    "timeline": 10,
    "mudancas": 10,
    "mapa_atividade": 28,
    "series_historico": 10,
    "historico_perfil": 10,
    "descobertas": 10,
}

def _ler(caminho: Path, padrao: Any) -> Any:
    try:
        if not caminho.exists():
            return padrao
        with caminho.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (OSError, json.JSONDecodeError, TypeError):
        return padrao

def _salvar(caminho: Path, dados: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(f".{caminho.name}.tmp")
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)
        arquivo.flush()
    temporario.replace(caminho)

def _normalizar(dados: Any) -> dict:
    resultado = {}
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            try:
                numero = int(valor)
            except (TypeError, ValueError):
                continue
            resultado[str(chave)] = max(1, numero)
    return resultado

def carregar_limites_sistema() -> dict:
    dados = _ler(SYSTEM_CONFIG, {})
    limites = dict(LIMITES_PADRAO)
    limites.update(_normalizar(dados))
    if not SYSTEM_CONFIG.exists():
        _salvar(SYSTEM_CONFIG, limites)
    return limites

def caminho_config_usuario(cliente_usuario: str) -> Path:
    cliente_usuario = str(cliente_usuario or "").strip().lower()
    if not cliente_usuario:
        raise ValueError("cliente_usuario é obrigatório.")
    return USER_ROOT / cliente_usuario / "config" / "limite_de_exebicao_dados.json"

def garantir_configuracao_usuario(cliente_usuario: str) -> dict:
    caminho = caminho_config_usuario(cliente_usuario)
    atual = _normalizar(_ler(caminho, {}))
    limites_sistema = carregar_limites_sistema()
    for chave, valor in limites_sistema.items():
        atual.setdefault(chave, valor)
    _salvar(caminho, atual)
    return atual

def sincronizar_limites_usuarios() -> dict:
    sistema = carregar_limites_sistema()
    anterior = _normalizar(_ler(SYSTEM_STATE, {}))
    alteradas = {chave: valor for chave, valor in sistema.items()
                 if anterior.get(chave) != valor}
    if not alteradas:
        _salvar(SYSTEM_STATE, sistema)
        return {"alteradas": {}, "usuarios_atualizados": 0}

    atualizados = 0
    if USER_ROOT.exists():
        for pasta_usuario in USER_ROOT.iterdir():
            if not pasta_usuario.is_dir():
                continue
            caminho = caminho_config_usuario(pasta_usuario.name)
            if not caminho.exists():
                garantir_configuracao_usuario(pasta_usuario.name)
                continue
            dados = _normalizar(_ler(caminho, {}))
            mudou = False
            for chave, valor in alteradas.items():
                if chave in dados and dados[chave] != valor:
                    dados[chave] = valor
                    mudou = True
            if mudou:
                _salvar(caminho, dados)
                atualizados += 1

    _salvar(SYSTEM_STATE, sistema)
    return {"alteradas": alteradas, "usuarios_atualizados": atualizados}

def carregar_limites_usuario(cliente_usuario: str) -> dict:
    sincronizar_limites_usuarios()
    usuario = garantir_configuracao_usuario(cliente_usuario)
    sistema = carregar_limites_sistema()
    limites = dict(LIMITES_PADRAO)
    limites.update(sistema)
    for chave, valor in usuario.items():
        if chave in limites:
            limites[chave] = min(limites[chave], max(1, int(valor)))
    return limites

def limite_exibicao(cliente_usuario: str, chave: str, padrao: int = 10) -> int:
    try:
        return max(1, int(carregar_limites_usuario(cliente_usuario).get(chave, padrao)))
    except Exception:
        return max(1, int(padrao))

def limitar_lista(cliente_usuario: str, chave: str, valores, padrao: int = 10):
    if not isinstance(valores, list):
        return valores
    return valores[:limite_exibicao(cliente_usuario, chave, padrao)]

def inicializar_limites_exibicao() -> None:
    carregar_limites_sistema()
    sincronizar_limites_usuarios()
    if USER_ROOT.exists():
        for pasta_usuario in USER_ROOT.iterdir():
            if pasta_usuario.is_dir():
                garantir_configuracao_usuario(pasta_usuario.name)
