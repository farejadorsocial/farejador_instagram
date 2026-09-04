"""Sincronização da fonte administrativa para os dados públicos."""

from pathlib import Path
import shutil

from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario


def caminho_base(*partes, nome_projeto="instagram"):
    try:
        atual = Path(__file__).resolve()
    except NameError:
        atual = Path.cwd().resolve()
    for pasta in [atual] + list(atual.parents):
        if pasta.name == nome_projeto:
            return pasta.joinpath(*partes)
    raise FileNotFoundError(f"Não foi encontrada a pasta '{nome_projeto}'.")


def _arquivo_precisa_copiar(origem: Path, destino: Path) -> bool:
    if not destino.exists():
        return True
    try:
        a, b = origem.stat(), destino.stat()
        return a.st_size != b.st_size or a.st_mtime_ns > b.st_mtime_ns
    except OSError:
        return True


def sincronizar_dados_publicos() -> dict:
    """Espelha dados/admin em sistema/dados/publico sem alterar o admin."""
    origem = caminho_dados_usuario("admin")
    destino = caminho_base("sistema", "dados", "publico")
    origem.mkdir(parents=True, exist_ok=True)
    destino.mkdir(parents=True, exist_ok=True)

    copiados = mantidos = removidos = 0
    arquivos_origem = set()

    for arquivo in origem.rglob("*"):
        if not arquivo.is_file():
            continue
        relativo = arquivo.relative_to(origem)
        arquivos_origem.add(relativo)
        alvo = destino / relativo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if _arquivo_precisa_copiar(arquivo, alvo):
            temporario = alvo.with_name(f".{alvo.name}.tmp")
            shutil.copy2(arquivo, temporario)
            temporario.replace(alvo)
            copiados += 1
        else:
            mantidos += 1

    for arquivo in list(destino.rglob("*")):
        if not arquivo.is_file():
            continue
        relativo = arquivo.relative_to(destino)
        if relativo not in arquivos_origem:
            try:
                arquivo.unlink()
                removidos += 1
            except OSError:
                pass

    for pasta in sorted(
        [p for p in destino.rglob("*") if p.is_dir()],
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        try:
            pasta.rmdir()
        except OSError:
            pass

    return {
        "origem": str(origem),
        "destino": str(destino),
        "copiados": copiados,
        "mantidos": mantidos,
        "removidos": removidos,
        "arquivos_publicos": len(arquivos_origem),
    }
