def _requisita_perfil(username):

    import requests

    cookies = {
        'csrftoken': '0mcDlvjhaH0FMpVF4XQBHR',
        'datr': 'qrN7anBdfqlsrjihJpe9Bpru',
        'ig_did': '8FC4B980-F8CE-46AD-B44A-655CD7AE098A',
        'ps_l': '1',
        'ps_n': '1',
        'mid': 'anuzqwALAAEznWW3jRRTPcyoOi71',
        'ig_nrcb': '1',
        'wd': '609x647',
    }

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'pt-BR,pt;q=0.5',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Brave";v="151", "Chromium";v="151"',
        'sec-ch-ua-full-version-list': '"Not=A?Brand";v="99.0.0.0", "Brave";v="151.0.0.0", "Chromium";v="151.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"10.0.0"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        # 'cookie': 'csrftoken=0mcDlvjhaH0FMpVF4XQBHR; datr=qrN7anBdfqlsrjihJpe9Bpru; ig_did=8FC4B980-F8CE-46AD-B44A-655CD7AE098A; ps_l=1; ps_n=1; mid=anuzqwALAAEznWW3jRRTPcyoOi71; ig_nrcb=1; wd=609x647',
    }

    response = requests.get(f'https://www.instagram.com/{username}/',
                            cookies=cookies, headers=headers)
    
    return response.text
    
    
    
    
def extrair_dados_instagram_html(html):
    """
    Extrai e normaliza os dados públicos de um perfil do Instagram
    a partir do HTML.

    IMPORTANTE:
    O retorno segue o modelo já utilizado pelo Farejador:

        {
            "perfil": {...},
            "conteudo": {
                "posts": [],
                "reels": [],
                "destaques": []
            }
        }

    Não adiciona hash nem timestamp_capture.
    Essas informações pertencem ao processo de monitoramento.
    """

    import json
    import re
    import html as html_lib

    # ==========================================================
    # FUNÇÕES AUXILIARES
    # ==========================================================

    def converter_numero(valor, padrao=0):

        if isinstance(valor, bool):
            return int(valor)

        if isinstance(valor, (int, float)):
            return int(valor)

        if isinstance(valor, str):

            texto = valor.strip()

            if not texto:
                return padrao

            # Remove separadores comuns.
            texto = texto.replace(".", "")
            texto = texto.replace(",", "")

            if texto.isdigit():
                return int(texto)

        return padrao


    def encontrar_objetos_com_chave(obj, chave):

        encontrados = []

        if isinstance(obj, dict):

            if chave in obj:
                encontrados.append(obj)

            for valor in obj.values():

                encontrados.extend(
                    encontrar_objetos_com_chave(
                        valor,
                        chave
                    )
                )

        elif isinstance(obj, list):

            for item in obj:

                encontrados.extend(
                    encontrar_objetos_com_chave(
                        item,
                        chave
                    )
                )

        return encontrados


    def procurar_scripts_json(texto):

        if not isinstance(texto, str):
            return []

        padroes = [

            r'<script[^>]*type=["\']application/json["\'][^>]*>'
            r'(.*?)</script>',

            r'<script[^>]*data-sjs[^>]*>'
            r'(.*?)</script>'

        ]

        scripts = []

        for padrao in padroes:

            encontrados = re.findall(
                padrao,
                texto,
                flags=re.DOTALL | re.IGNORECASE
            )

            scripts.extend(encontrados)

        return scripts


    def carregar_json_scripts(texto):

        objetos = []

        scripts = procurar_scripts_json(texto)

        for script in scripts:

            script = script.strip()

            if not script:
                continue

            try:

                dados = json.loads(script)

                objetos.append(dados)

            except (
                TypeError,
                ValueError,
                json.JSONDecodeError
            ):

                continue

        return objetos


    def extrair_total_posts_html(texto):

        """
        O payload estruturado pode trazer:

            all_media_count: None

        mas o HTML possui o total de posts no meta description.

        Exemplo:

            107 seguidores,
            seguindo 452,
            4 posts
        """

        padroes = [

            r'<meta[^>]+property=["\']og:description["\']'
            r'[^>]+content=["\']([^"\']*)["\']',

            r'<meta[^>]+name=["\']description["\']'
            r'[^>]+content=["\']([^"\']*)["\']'

        ]

        for padrao in padroes:

            encontrado = re.search(
                padrao,
                texto,
                flags=re.IGNORECASE | re.DOTALL
            )

            if not encontrado:
                continue

            descricao = html_lib.unescape(
                encontrado.group(1)
            )

            match = re.search(
                r'(?<!\d)(\d[\d.,]*)\s+posts?\b',
                descricao,
                flags=re.IGNORECASE
            )

            if match:

                return converter_numero(
                    match.group(1),
                    0
                )

        return 0


    def normalizar_links(links):

        """
        Mantém somente o URL estável.

        Não salvar lynx_url, tokens e outros metadados
        temporários do Instagram.

        Isso evita gerar falso movimento no histórico.
        """

        if not isinstance(links, list):
            return []

        resultado = []

        for link in links:

            if not isinstance(link, dict):
                continue

            url = link.get("url")

            if not url:
                continue

            resultado.append({
                "url": str(url)
            })

        return resultado


    # ==========================================================
    # ESTRUTURA VAZIA PADRÃO
    # ==========================================================

    estrutura_vazia = {
        "perfil": {},
        "conteudo": {
            "posts": [],
            "reels": [],
            "destaques": []
        }
    }


    # ==========================================================
    # VALIDAR HTML
    # ==========================================================

    if not isinstance(html, str) or not html.strip():

        resultado = dict(estrutura_vazia)

        resultado["erro"] = {
            "tipo": "ValueError",
            "mensagem": "HTML inválido ou vazio."
        }

        return resultado


    # ==========================================================
    # CARREGAR JSONS EMBUTIDOS
    # ==========================================================

    objetos_json = carregar_json_scripts(html)

    if not objetos_json:

        resultado = dict(estrutura_vazia)

        resultado["erro"] = {
            "tipo": "ValueError",
            "mensagem": (
                "Nenhum JSON embutido válido "
                "foi encontrado no HTML."
            )
        }

        return resultado


    # ==========================================================
    # LOCALIZAR TODOS OS PAYLOADS DO USUÁRIO
    # ==========================================================

    candidatos = []

    for objeto in objetos_json:

        encontrados = encontrar_objetos_com_chave(
            objeto,
            "xig_user_by_username"
        )

        for encontrado in encontrados:

            usuario = encontrado.get(
                "xig_user_by_username"
            )

            if isinstance(usuario, dict):

                candidatos.append(usuario)


    if not candidatos:

        resultado = dict(estrutura_vazia)

        resultado["erro"] = {
            "tipo": "LookupError",
            "mensagem": (
                "Perfil do Instagram não encontrado "
                "no HTML."
            )
        }

        return resultado


    # ==========================================================
    # UNIFICAR OS PAYLOADS
    # ==========================================================
    #
    # O Instagram pode dividir os dados assim:
    #
    # PAYLOAD 1
    #   pk
    #   username
    #   follower_count
    #   biography
    #   etc.
    #
    # PAYLOAD 2
    #   pk
    #   polaris_ordered_timeline_connection
    #
    # Por isso não podemos usar somente candidatos[0].
    #

    usuario = {}

    for candidato in candidatos:

        for chave, valor in candidato.items():

            if chave not in usuario:

                usuario[chave] = valor

                continue


            valor_atual = usuario.get(chave)

            # Se o valor atual estiver vazio,
            # aceita o novo valor.

            if valor_atual in (
                None,
                "",
                [],
                {}
            ):

                usuario[chave] = valor

                continue


            # Conexões Relay podem aparecer
            # divididas entre payloads.

            if (
                isinstance(valor_atual, dict)
                and isinstance(valor, dict)
            ):

                combinado = dict(valor_atual)

                for sub_chave, sub_valor in valor.items():

                    if sub_valor not in (
                        None,
                        "",
                        [],
                        {}
                    ):

                        combinado[sub_chave] = sub_valor

                usuario[chave] = combinado


    # ==========================================================
    # IDENTIFICADOR
    # ==========================================================

    pk = usuario.get("pk")

    if pk is None:

        resultado = dict(estrutura_vazia)

        resultado["erro"] = {
            "tipo": "LookupError",
            "mensagem": (
                "O payload foi encontrado, "
                "mas não possui pk."
            )
        }

        return resultado


    pk = converter_numero(
        pk,
        pk
    )


    # ==========================================================
    # POSTS
    # ==========================================================

    timeline = usuario.get(
        "polaris_ordered_timeline_connection"
    )

    if not isinstance(timeline, dict):
        timeline = {}


    edges = timeline.get(
        "edges",
        []
    )

    if not isinstance(edges, list):
        edges = []


    posts = []


    for edge in edges:

        if not isinstance(edge, dict):
            continue

        node = edge.get(
            "node",
            edge
        )

        if not isinstance(node, dict):
            continue

        posts.append(node)


    # ==========================================================
    # TOTAL DE POSTS
    # ==========================================================

    total_posts = usuario.get(
        "all_media_count"
    )


    # ----------------------------------------------------------
    # Fallback para o HTML
    # ----------------------------------------------------------

    if total_posts is None:

        total_posts = extrair_total_posts_html(
            html
        )


    total_posts = converter_numero(
        total_posts,
        0
    )


    # ==========================================================
    # DESTAQUES
    # ==========================================================

    highlights = usuario.get(
        "lox_highlights_connection"
    )

    total_destaques = 0

    if isinstance(highlights, dict):

        edges_destaques = highlights.get(
            "edges",
            []
        )

        if isinstance(edges_destaques, list):

            total_destaques = len(
                edges_destaques
            )


    # ==========================================================
    # REELS
    # ==========================================================
    #
    # O payload atual não fornece uma contagem confiável.
    #
    # Não vamos inventar uma quantidade.
    #
    # O sistema atual trabalha com campo numérico,
    # portanto usamos 0.
    #

    total_reels = 0


    # ==========================================================
    # PERFIL
    # ==========================================================

    perfil = {

        "pk": pk,

        "id": usuario.get(
            "id"
        ),

        "username": usuario.get(
            "username"
        ),

        "nome": usuario.get(
            "full_name"
        ),

        "biografia": usuario.get(
            "biography"
        ),

        "privado": bool(
            usuario.get(
                "is_private",
                False
            )
        ),

        "verificado": bool(
            usuario.get(
                "is_verified",
                False
            )
        ),

        "memorializado": bool(
            usuario.get(
                "is_memorialized",
                False
            )
        ),

        "seguidores": converter_numero(
            usuario.get(
                "follower_count"
            ),
            0
        ),

        "seguindo": converter_numero(
            usuario.get(
                "following_count"
            ),
            0
        ),

        "total_posts": total_posts,

        "total_reels": total_reels,

        "total_destaques": total_destaques,

        "pronomes": (
            usuario.get("pronouns")
            if isinstance(
                usuario.get("pronouns"),
                list
            )
            else []
        ),

        "links": normalizar_links(
            usuario.get(
                "bio_links"
            )
        ),

        "foto_perfil": usuario.get(
            "profile_pic_url"
        )
    }


    # ==========================================================
    # RETORNO
    # ==========================================================

    return {

        "perfil": perfil,

        "conteudo": {

            "posts": posts,

            "reels": [],

            "destaques": []

        }

    }


def extrair_perfil(perfil):

    import time


    try:
        res = _requisita_perfil(perfil)
        resultado = extrair_dados_instagram_html(res)

        print('---'*30)
        print('requisitou perfil : ',perfil)
        print('tamanho da resposta :',len(res))
        print('aguardando 10 seg para proximo requisição')
        time.sleep(10)
        
        return resultado

    except Exception as erro:
        print('Erro No Requests, modulo extrair perfil : ',erro)


if __name__ == "__main__":

    resultado = extrair_perfil(perfil='bonus_de_apostas')

    print(resultado)