from datetime import datetime
import json
import os
import hashlib
from pathlib import Path
import random
import time
import random



def gerador_hash(texto):
    texto = str(texto)
    hash_ = hashlib.sha256(texto.encode()).hexdigest()
    
    return hash_

def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    return dados



def salvar_dados_json(dados,caminho):
    with open(caminho,"w",encoding="utf-8") as arquivo:
        json.dump(dados,arquivo,ensure_ascii=False,indent=4)



def caminho_base(*caminho_final, nome_projeto="instagram"):
    """
    Retorna caminhos relativos à raiz do projeto.

    Funciona no:
    - VSCode
    - Jupyter Notebook
    - Scripts Python
    - Anaconda
    """

    # VSCode / Scripts
    try:
        caminho_atual = Path(__file__).resolve()
    except NameError:
        # Jupyter Notebook
        caminho_atual = Path.cwd().resolve()

    # Procura a raiz do projeto
    for pasta in [caminho_atual] + list(caminho_atual.parents):

        if pasta.name == nome_projeto:

            # junta os caminhos corretamente
            return pasta.joinpath(*caminho_final)

    raise FileNotFoundError(
        f"Não foi encontrada a pasta '{nome_projeto}'."
    )



def salvar_recorrente(metadata_perfil, CAMINHO):

    caminho = CAMINHO if isinstance(CAMINHO, Path) else caminho_base(*CAMINHO)

    caminho.parent.mkdir(parents=True, exist_ok=True)

    if not caminho.exists():
        caminho.write_text("[]", encoding="utf-8")

    if not isinstance(metadata_perfil, dict):
        return None

    dados = carregar_dados(caminho)

    if not isinstance(dados, list):
        dados = []

    # ==========================================
    # HASH DA NOVA CAPTURA
    # ==========================================

    novo_hash = metadata_perfil.get('hash')

    # ==========================================
    # COMPARA SOMENTE COM A ÚLTIMA CAPTURA
    # ==========================================

    if dados:

        ultimo = dados[-1]

        if (
            isinstance(ultimo, dict)
            and ultimo.get('hash') == novo_hash
        ):
            return dados

    # ==========================================
    # NOVA ALTERAÇÃO
    # ==========================================

    dados.append(metadata_perfil)

    salvar_dados_json(dados, caminho)

    return dados





import instaloader


def extrair_perfil_sem_login(username):
    """
    Extrai dados públicos de um perfil do Instagram utilizando
    Instaloader, sem realizar login.

    Retorno:

    {
        "perfil": {
            "pk": ...,
            "id": ...,
            "username": ...,
            "nome": ...,
            "biografia": ...,
            "privado": ...,
            "verificado": ...,
            "memorializado": ...,
            "seguidores": ...,
            "seguindo": ...,
            "total_posts": ...,
            "total_reels": ...,
            "total_destaques": ...,
            "pronomes": [],
            "links": [],
            "foto_perfil": ...
        },

        "conteudo": {
            "posts": [],
            "reels": [],
            "destaques": []
        }
    }
    """

    L = instaloader.Instaloader()

    resultado = {
        "perfil": {},
        "conteudo": {
            "posts": [],
            "reels": [],
            "destaques": []
        }
    }

    # ==========================================================
    # FUNÇÃO AUXILIAR
    # ==========================================================

    def pegar(obj, atributo, default=None):
        """
        Obtém um atributo com segurança.
        """

        try:
            valor = getattr(obj, atributo, default)

            if callable(valor):
                return default

            return valor

        except Exception:
            return default

    # ==========================================================
    # CARREGAR PERFIL
    # ==========================================================

    try:

        profile = instaloader.Profile.from_username(
            L.context,
            username
        )

    except Exception as e:

        resultado["erro"] = {
            "tipo": type(e).__name__,
            "mensagem": str(e)
        }

        return resultado

    # ==========================================================
    # IDENTIFICADORES
    # ==========================================================

    pk = pegar(profile, "userid")

    # ----------------------------------------------------------
    # Tentar encontrar um ID adicional, sem inventar valor
    # ----------------------------------------------------------

    id_perfil = None

    possiveis_ids = [
        "id",
        "profile_id",
        "user_id",
        "pk"
    ]

    for atributo in possiveis_ids:

        valor = pegar(profile, atributo)

        if valor is not None:

            # Não utilizar o mesmo valor do pk como outro id
            if valor != pk:
                id_perfil = valor
                break

    # ----------------------------------------------------------
    # Metadata interna, quando disponível
    # ----------------------------------------------------------

    if id_perfil is None:

        metadata = pegar(profile, "_metadata")

        if isinstance(metadata, dict):

            possiveis_ids_metadata = [
                "id",
                "user_id",
                "profile_id"
            ]

            for chave in possiveis_ids_metadata:

                valor = metadata.get(chave)

                if valor is not None and valor != pk:

                    id_perfil = valor
                    break

    # ==========================================================
    # LINKS
    # ==========================================================

    links = []

    link_externo = pegar(
        profile,
        "external_url"
    )

    if link_externo:

        links.append({
            "url": link_externo
        })

    # ==========================================================
    # DADOS DO PERFIL
    # ==========================================================

    resultado["perfil"] = {

        # ------------------------------------------------------
        # IDENTIFICAÇÃO
        # ------------------------------------------------------

        "pk": pk,

        "id": id_perfil,

        "username": pegar(
            profile,
            "username"
        ),

        "nome": pegar(
            profile,
            "full_name"
        ),

        # ------------------------------------------------------
        # INFORMAÇÕES
        # ------------------------------------------------------

        "biografia": pegar(
            profile,
            "biography"
        ),

        # ------------------------------------------------------
        # STATUS DA CONTA
        # ------------------------------------------------------

        "privado": pegar(
            profile,
            "is_private"
        ),

        "verificado": pegar(
            profile,
            "is_verified"
        ),

        "memorializado": pegar(
            profile,
            "is_memorialized"
        ),

        # ------------------------------------------------------
        # CONTADORES
        # ------------------------------------------------------

        "seguidores": pegar(
            profile,
            "followers"
        ),

        "seguindo": pegar(
            profile,
            "followees"
        ),

        # ------------------------------------------------------
        # TOTAIS
        #
        # Serão atualizados depois da extração do conteúdo.
        # ------------------------------------------------------

        "total_posts": 0,

        "total_reels": 0,

        "total_destaques": 0,

        # ------------------------------------------------------
        # PERFIL
        # ------------------------------------------------------

        "pronomes": [],

        "links": links,

        "foto_perfil": pegar(
            profile,
            "profile_pic_url"
        )
    }

    # ==========================================================
    # POSTS
    # ==========================================================

    try:

        for post in profile.get_posts():

            data_post = pegar(
                post,
                "date"
            )

            data_post_utc = pegar(
                post,
                "date_utc"
            )

            dados_post = {

                "id": pegar(
                    post,
                    "mediaid"
                ),

                "shortcode": pegar(
                    post,
                    "shortcode"
                ),

                "url": pegar(
                    post,
                    "url"
                ),

                "data": (
                    data_post.isoformat()
                    if data_post
                    else None
                ),

                "data_utc": (
                    data_post_utc.isoformat()
                    if data_post_utc
                    else None
                ),

                "legenda": pegar(
                    post,
                    "caption"
                ),

                "curtidas": pegar(
                    post,
                    "likes"
                ),

                "comentarios": pegar(
                    post,
                    "comments"
                ),

                "tipo": pegar(
                    post,
                    "typename"
                ),

                "eh_video": pegar(
                    post,
                    "is_video"
                ),

                "url_imagem": pegar(
                    post,
                    "display_url"
                ),

                "url_video": pegar(
                    post,
                    "video_url"
                ),

                "hashtags": pegar(
                    post,
                    "caption_hashtags",
                    []
                ),

                "mencoes": pegar(
                    post,
                    "caption_mentions",
                    []
                ),

                "localizacao": None,

                "carrossel": []
            }

            # ==================================================
            # LOCALIZAÇÃO
            # ==================================================

            location = pegar(
                post,
                "location"
            )

            if location:

                dados_post["localizacao"] = {

                    "nome": pegar(
                        location,
                        "name"
                    ),

                    "lat": pegar(
                        location,
                        "lat"
                    ),

                    "lng": pegar(
                        location,
                        "lng"
                    )
                }

            # ==================================================
            # CARROSSEL
            # ==================================================

            if dados_post["tipo"] == "GraphSidecar":

                try:

                    for item in post.get_sidecar_nodes():

                        dados_item = {

                            "id": pegar(
                                item,
                                "mediaid"
                            ),

                            "eh_video": pegar(
                                item,
                                "is_video"
                            ),

                            "url_imagem": pegar(
                                item,
                                "display_url"
                            ),

                            "url_video": pegar(
                                item,
                                "video_url"
                            )
                        }

                        dados_post["carrossel"].append(
                            dados_item
                        )

                except Exception:
                    pass

            # ==================================================
            # SEPARAR POST / REEL
            # ==================================================

            if dados_post["tipo"] == "GraphVideo":

                resultado["conteudo"]["reels"].append(
                    dados_post
                )

            else:

                resultado["conteudo"]["posts"].append(
                    dados_post
                )

    except Exception as e:

        print(e)
        print()

    # ==========================================================
    # DESTAQUES
    # ==========================================================

    try:

        for highlight in profile.get_highlights():

            dados_highlight = {

                "id": pegar(
                    highlight,
                    "unique_id"
                ),

                "titulo": pegar(
                    highlight,
                    "title"
                ),

                "itens": []
            }

            try:

                for item in highlight.get_items():

                    data_item = pegar(
                        item,
                        "date_utc"
                    )

                    dados_item = {

                        "id": pegar(
                            item,
                            "mediaid"
                        ),

                        "data": (
                            data_item.isoformat()
                            if data_item
                            else None
                        ),

                        "url": pegar(
                            item,
                            "url"
                        ),

                        "eh_video": pegar(
                            item,
                            "is_video"
                        )
                    }

                    dados_highlight["itens"].append(
                        dados_item
                    )

            except Exception:
                pass

            resultado["conteudo"]["destaques"].append(
                dados_highlight
            )

    except Exception as e:
        print(e)
        print()

    # ==========================================================
    # TOTAIS
    # ==========================================================

    resultado["perfil"]["total_posts"] = len(
        resultado["conteudo"]["posts"]
    )

    resultado["perfil"]["total_reels"] = len(
        resultado["conteudo"]["reels"]
    )

    resultado["perfil"]["total_destaques"] = len(
        resultado["conteudo"]["destaques"]
    )

    # ==========================================================
    # RETORNO
    # ==========================================================

    return resultado



def carregar_lista_perfil_salvos(cliente_usuario):
    
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_perfil_salvos = caminho_dados_usuario(cliente_usuario, 'perfil_salvos')


    lista = []

    for c in caminho_perfil_salvos.iterdir():
        dados = carregar_dados(c)

        lista.append(dados)

    lista_username = [i['perfil']['username'] for i in lista]
    
    return lista_username





def monitorar_perfil_usuario(selecionado,cliente_usuario):

    from toolFarejador.extracao.modulo_extrair_perfil import extrair_perfil
    
    perfil_monitorar =  extrair_perfil(selecionado)

    #perfil_monitorar = extrair_perfil_sem_login(selecionado)

    foto_perfil  = perfil_monitorar['perfil'].pop('foto_perfil',None)
    conteudo     = perfil_monitorar.pop('conteudo',None)

    perfil_monitorar['hash'] = gerador_hash(perfil_monitorar)

    perfil_monitorar['timestamp_capture'] = datetime.now().isoformat()

    username = perfil_monitorar['perfil']['username']
    pk       = perfil_monitorar['perfil']['pk']

    perfil_monitorar['perfil']['foto_perfil'] = foto_perfil
    perfil_monitorar['conteudo'] = conteudo


    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    CAMINHO = None

    caminho_historico = caminho_dados_usuario(cliente_usuario, 'historico', f'{pk}.json')
    resultado = salvar_recorrente(perfil_monitorar, caminho_historico)
    
    return resultado




def lista_perfil_monitorados(cliente_usuario):

    lista = []
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_monitorar = caminho_dados_usuario(cliente_usuario, "monitoramento")

    


    if not caminho_monitorar.exists():
        return []

    for arquivo in caminho_monitorar.glob("*.json"):
        try:
            dados = carregar_dados(arquivo)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(dados, dict):
            lista.append(dados)

    return lista


# Compatibilidade com chamadas antigas. A execução real do monitoramento
# global fica no módulo toolMonitoramentoSistema.
def monitoramento_perfis_tempo_real():
    from toolFarejador.monitoramento.toolMonitoramentoSistema import monitoramento_perfis_tempo_real as _monitorar
    return _monitorar()


if __name__ == "__main__":

    cliente_usuario = 'admin'
    
    monitoramento_perfis_tempo_real()







