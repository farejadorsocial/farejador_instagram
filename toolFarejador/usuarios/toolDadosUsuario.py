"""Camada central de dados por cliente.

Toda informação persistente pertencente a um cliente autenticado fica em:
sistema/user/<cliente_usuario>/dados/

O módulo mantém uma migração compatível com a estrutura antiga
dados/<cliente_usuario>/ para não perder dados existentes.
"""

from pathlib import Path
import re
import shutil


BASE = Path(__file__).resolve().parents[2]
USER_ROOT = BASE / "sistema" / "user"
LEGACY_ROOT = BASE / "dados"
USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,64}$")


def caminho_usuario(cliente_usuario: str) -> Path:
    cliente_usuario = str(cliente_usuario or "").strip().lower()
    if not cliente_usuario:
        raise ValueError("cliente_usuario é obrigatório.")
    if not USERNAME_RE.fullmatch(cliente_usuario):
        raise ValueError("cliente_usuario inválido.")
    return USER_ROOT / cliente_usuario


def caminho_dados_usuario(cliente_usuario: str, *partes) -> Path:
    return caminho_usuario(cliente_usuario) / "dados" / Path(*partes)


def _copiar_se_ausente(origem: Path, destino: Path) -> int:
    """Copia a árvore legada apenas para arquivos ainda inexistentes."""
    if not origem.exists():
        return 0

    copiados = 0
    for item in origem.rglob("*"):
        if not item.is_file():
            continue
        relativo = item.relative_to(origem)
        alvo = destino / relativo
        if alvo.exists():
            continue
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, alvo)
        copiados += 1
    return copiados


def garantir_dados_usuario(cliente_usuario: str) -> Path:
    """Garante a nova raiz e migra dados legados sem apagar nada."""
    destino = caminho_usuario(cliente_usuario) / "dados"
    destino.mkdir(parents=True, exist_ok=True)

    legado = LEGACY_ROOT / cliente_usuario
    _copiar_se_ausente(legado, destino)

    return destino


def migrar_dados_legados() -> dict:
    """Migra todos os clientes existentes em dados/<cliente>."""
    resultado = {"clientes": 0, "arquivos_copiados": 0}

    if not LEGACY_ROOT.exists():
        return resultado

    for pasta in LEGACY_ROOT.iterdir():
        if not pasta.is_dir():
            continue
        resultado["clientes"] += 1
        resultado["arquivos_copiados"] += _copiar_se_ausente(
            pasta,
            caminho_usuario(pasta.name) / "dados",
        )

    return resultado
