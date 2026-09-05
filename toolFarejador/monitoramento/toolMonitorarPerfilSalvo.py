from datetime import datetime
import hashlib


def gerador_hash(texto):
    texto = str(texto)
    return hashlib.sha256(texto.encode()).hexdigest()


def salvar_recorrente(metadata_perfil, CAMINHO=None, cliente_usuario=None):
    """Registra a captura diretamente no PostgreSQL."""
    if not isinstance(metadata_perfil, dict):
        return None

    if not cliente_usuario:
        raise ValueError("cliente_usuario é obrigatório para salvar o histórico no PostgreSQL.")

    from backend.database.sync import sincronizar_historico
    from backend.repositories.perfil_repository import get_history

    sincronizar_historico(cliente_usuario, metadata_perfil)

    perfil = metadata_perfil.get("perfil") or {}
    pk = perfil.get("pk")
    if pk is None:
        return None

    return get_history(cliente_usuario, pk)


import instaloader


def extrair_perfil_sem_login(username):
    L = instaloader.Instaloader()
    resultado = {"perfil": {}, "conteudo": {"posts": [], "reels": [], "destaques": []}}

    def pegar(obj, atributo, default=None):
        try:
            valor = getattr(obj, atributo, default)
            return default if callable(valor) else valor
        except Exception:
            return default

    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except Exception as erro:
        resultado["erro"] = {"tipo": type(erro).__name__, "mensagem": str(erro)}
        return resultado

    pk = pegar(profile, "userid")
    id_perfil = None
    for atributo in ("id", "profile_id", "user_id", "pk"):
        valor = pegar(profile, atributo)
        if valor is not None and valor != pk:
            id_perfil = valor
            break
    if id_perfil is None:
        metadata = pegar(profile, "_metadata")
        if isinstance(metadata, dict):
            for chave in ("id", "user_id", "profile_id"):
                valor = metadata.get(chave)
                if valor is not None and valor != pk:
                    id_perfil = valor
                    break

    links = []
    link_externo = pegar(profile, "external_url")
    if link_externo:
        links.append({"url": link_externo})

    resultado["perfil"] = {
        "pk": pk, "id": id_perfil, "username": pegar(profile, "username"),
        "nome": pegar(profile, "full_name"), "biografia": pegar(profile, "biography"),
        "privado": pegar(profile, "is_private"), "verificado": pegar(profile, "is_verified"),
        "memorializado": pegar(profile, "is_memorialized"), "seguidores": pegar(profile, "followers"),
        "seguindo": pegar(profile, "followees"), "total_posts": 0, "total_reels": 0,
        "total_destaques": 0, "pronomes": [], "links": links,
        "foto_perfil": pegar(profile, "profile_pic_url"),
    }

    try:
        for post in profile.get_posts():
            data_post = pegar(post, "date")
            data_post_utc = pegar(post, "date_utc")
            dados_post = {
                "id": pegar(post, "mediaid"), "shortcode": pegar(post, "shortcode"),
                "url": pegar(post, "url"), "data": data_post.isoformat() if data_post else None,
                "data_utc": data_post_utc.isoformat() if data_post_utc else None,
                "legenda": pegar(post, "caption"), "curtidas": pegar(post, "likes"),
                "comentarios": pegar(post, "comments"), "tipo": pegar(post, "typename"),
                "eh_video": pegar(post, "is_video"), "url_imagem": pegar(post, "display_url"),
                "url_video": pegar(post, "video_url"), "hashtags": pegar(post, "caption_hashtags", []),
                "mencoes": pegar(post, "caption_mentions", []), "localizacao": None, "carrossel": [],
            }
            location = pegar(post, "location")
            if location:
                dados_post["localizacao"] = {"nome": pegar(location, "name"), "lat": pegar(location, "lat"), "lng": pegar(location, "lng")}
            if dados_post["tipo"] == "GraphSidecar":
                try:
                    for item in post.get_sidecar_nodes():
                        dados_post["carrossel"].append({
                            "id": pegar(item, "mediaid"), "eh_video": pegar(item, "is_video"),
                            "url_imagem": pegar(item, "display_url"), "url_video": pegar(item, "video_url"),
                        })
                except Exception:
                    pass
            if dados_post["tipo"] == "GraphVideo":
                resultado["conteudo"]["reels"].append(dados_post)
            else:
                resultado["conteudo"]["posts"].append(dados_post)
    except Exception as erro:
        print(erro)

    try:
        for highlight in profile.get_highlights():
            dados_highlight = {"id": pegar(highlight, "unique_id"), "titulo": pegar(highlight, "title"), "itens": []}
            try:
                for item in highlight.get_items():
                    data_item = pegar(item, "date_utc")
                    dados_highlight["itens"].append({
                        "id": pegar(item, "mediaid"), "data": data_item.isoformat() if data_item else None,
                        "url": pegar(item, "url"), "eh_video": pegar(item, "is_video"),
                    })
            except Exception:
                pass
            resultado["conteudo"]["destaques"].append(dados_highlight)
    except Exception as erro:
        print(erro)

    resultado["perfil"]["total_posts"] = len(resultado["conteudo"]["posts"])
    resultado["perfil"]["total_reels"] = len(resultado["conteudo"]["reels"])
    resultado["perfil"]["total_destaques"] = len(resultado["conteudo"]["destaques"])
    return resultado


def carregar_lista_perfil_salvos(cliente_usuario):
    from backend.repositories.perfil_repository import get_saved_profiles
    return [
        item.get("perfil", {}).get("username")
        for item in get_saved_profiles(cliente_usuario)
        if item.get("perfil", {}).get("username")
    ]


def monitorar_perfil_usuario(selecionado, cliente_usuario):
    from toolFarejador.extracao.modulo_extrair_perfil import extrair_perfil
    perfil_monitorar = extrair_perfil(selecionado)
    foto_perfil = perfil_monitorar["perfil"].pop("foto_perfil", None)
    conteudo = perfil_monitorar.pop("conteudo", None)
    perfil_monitorar["hash"] = gerador_hash(perfil_monitorar)
    perfil_monitorar["timestamp_capture"] = datetime.now().isoformat()
    perfil_monitorar["perfil"]["foto_perfil"] = foto_perfil
    perfil_monitorar["conteudo"] = conteudo

    return salvar_recorrente(perfil_monitorar, cliente_usuario=cliente_usuario)


def lista_perfil_monitorados(cliente_usuario):
    from backend.database.connection import get_engine
    from backend.database.models import Monitoramento
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    with Session(get_engine()) as session:
        registros = session.scalars(
            select(Monitoramento)
            .where(Monitoramento.cliente_usuario == cliente_usuario)
            .order_by(Monitoramento.id)
        ).all()

    return [
        {
            "pk": registro.instagram_pk,
            "username": registro.username,
            "nome": registro.nome,
            "sleep": registro.sleep,
            "monitorando": registro.monitorando,
            "atualizado": registro.atualizado.isoformat() if registro.atualizado else None,
        }
        for registro in registros
    ]


def monitoramento_perfis_tempo_real():
    from toolFarejador.monitoramento.toolMonitoramentoSistema import monitoramento_perfis_tempo_real as executar
    return executar()
