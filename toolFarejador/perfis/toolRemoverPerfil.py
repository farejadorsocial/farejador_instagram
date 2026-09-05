from backend.repositories.perfil_repository import get_saved_profiles


def carregar_dados_perfil_salvos(cliente_usuario):
    """Lê perfis salvos do PostgreSQL."""
    dados = get_saved_profiles(cliente_usuario)
    lista_username = [
        item.get("perfil", {}).get("username")
        for item in dados
        if item.get("perfil", {}).get("username")
    ]

    return {
        "lista_username_salvos": lista_username,
        "dados_perfil": dados,
    }


def remover_perfil(perfil_selecionado, cliente_usuario="admin"):
    """
    Remove um perfil e todos os dados derivados pertencentes ao cliente.

    PostgreSQL é a fonte oficial da existência e da remoção do perfil.
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

    from backend.database.sync import remover_dados_perfil
    remover_dados_perfil(cliente_usuario, pk)

    if cliente_usuario == "admin":
        try:
            from toolFarejador.sistema.toolSistemaPublico import sincronizar_dados_publicos
            sincronizar_dados_publicos()
        except Exception as erro:
            print(f"[postgres] Falha ao atualizar dados públicos: {erro}")

    return {
        "removido": True,
        "pk": pk,
        "username": perfil.get("username", username),
        "arquivos_removidos": [],
    }


if __name__ == "__main__":
    cliente_usuario = "admin"
    lista = carregar_dados_perfil_salvos(cliente_usuario)
    if lista["lista_username_salvos"]:
        print(remover_perfil(lista["lista_username_salvos"][0], cliente_usuario))
