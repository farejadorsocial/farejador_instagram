import json
from pathlib import Path

from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario


from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
def caminho_base(*caminho_final, nome_projeto="instagram"):
    try:
        caminho_atual = Path(__file__).resolve()
    except NameError:
        caminho_atual = Path.cwd().resolve()

    for pasta in [caminho_atual] + list(caminho_atual.parents):
        if pasta.name == nome_projeto:
            return pasta.joinpath(*caminho_final)

    raise FileNotFoundError(
        f"Não foi encontrada a pasta '{nome_projeto}'."
    )


def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_dados_json(dados, caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)


def carregar_dados_perfil_salvos(cliente_usuario):
    caminho_perfil_salvos = caminho_dados_usuario(
        cliente_usuario, "perfil_salvos"
    )

    lista = []

    if not caminho_perfil_salvos.exists():
        return {
            "lista_username_salvos": [],
            "dados_perfil": [],
        }

    for arquivo in caminho_perfil_salvos.glob("*.json"):
        try:
            dados = carregar_dados(arquivo)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(dados, dict):
            lista.append(dados)

    lista_username = [
        item.get("perfil", {}).get("username")
        for item in lista
        if item.get("perfil", {}).get("username")
    ]

    return {
        "lista_username_salvos": lista_username,
        "dados_perfil": lista,
    }


def _remover_arquivo(caminho):
    caminho = Path(caminho)
    if caminho.exists() and caminho.is_file():
        caminho.unlink()
        return True
    return False


def _reconstruir_feed(cliente_usuario):
    pasta_notificacoes = caminho_dados_usuario(cliente_usuario, "notificacoes")
    caminho_feed = caminho_dados_usuario(cliente_usuario, 'feed', 'feed.json')

    notificacoes = []

    if pasta_notificacoes.exists():
        for arquivo in pasta_notificacoes.glob("*.json"):
            try:
                dados = carregar_dados(arquivo)
            except (OSError, json.JSONDecodeError):
                continue

            if isinstance(dados, dict):
                notificacoes.append(dados)

    notificacoes.sort(
        key=lambda item: item.get("timestamp_capture", ""),
        reverse=True,
    )

    salvar_dados_json(notificacoes, caminho_feed)
    return notificacoes


def remover_perfil(perfil_selecionado, cliente_usuario="admin"):
    """
    Remove um perfil e todos os dados derivados pertencentes ao cliente.

    A remoção usa cliente_usuario + pk como identidade física dos arquivos.
    Os campos caminho_perfil_salvo/caminho_historico_salvo existentes nos
    JSONs são tratados apenas como metadados, pois versões antigas podem
    conter caminhos absolutos de outra máquina.
    """
    username = str(perfil_selecionado or "").strip().lstrip("@").lower()
    if not username:
        return {
            "removido": False,
            "username": username,
            "arquivos_removidos": [],
        }

    dados_salvos = carregar_dados_perfil_salvos(cliente_usuario)
    selecionado = None

    for item in dados_salvos["dados_perfil"]:
        perfil = item.get("perfil", {})
        item_username = str(perfil.get("username", "")).strip().lower()
        if item_username == username:
            selecionado = item
            break

    if selecionado is None:
        return {
            "removido": False,
            "username": username,
            "arquivos_removidos": [],
        }

    perfil = selecionado.get("perfil", {})
    pk = perfil.get("pk")

    if pk is None:
        raise ValueError("O perfil salvo não possui pk.")

    # A identidade dos dados é sempre cliente_usuario + pk.
    caminhos = [
        caminho_dados_usuario(cliente_usuario, "perfil_salvos", f"{pk}.json"),
        caminho_dados_usuario(cliente_usuario, "historico", f"{pk}.json"),
        caminho_dados_usuario(cliente_usuario, "monitoramento", f"{pk}.json"),
        caminho_dados_usuario(cliente_usuario, "notificacoes", f"{pk}.json"),
        caminho_dados_usuario(cliente_usuario, "resumo", f"{pk}.json"),
    ]

    removidos = []
    for caminho in caminhos:
        if _remover_arquivo(caminho):
            removidos.append(str(caminho))

    _reconstruir_feed(cliente_usuario)

    return {
        "removido": True,
        "pk": pk,
        "username": perfil.get("username", username),
        "arquivos_removidos": removidos,
    }


if __name__ == "__main__":
    cliente_usuario = "admin"
    lista = carregar_dados_perfil_salvos(cliente_usuario)
    if lista["lista_username_salvos"]:
        print(remover_perfil(lista["lista_username_salvos"][0], cliente_usuario))
