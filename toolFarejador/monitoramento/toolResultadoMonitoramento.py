from datetime import datetime
import json
import os
import hashlib
from pathlib import Path



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



def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    return dados



def salvar_dados_json(dados,caminho):
    with open(caminho,"w",encoding="utf-8") as arquivo:
        json.dump(dados,arquivo,ensure_ascii=False,indent=4)



def identificar_mudancas(historico):

    if not isinstance(historico, list) or len(historico) < 2:
        return []

    campos_comparacao = [
        'pk',
        'id',
        'username',
        'nome',
        'biografia',
        'privado',
        'verificado',
        'memorializado',
        'seguidores',
        'seguindo',
        'total_posts',
        'total_reels',
        'total_destaques',
        'pronomes',
        'links'
    ]

    campos_identificacao = [
        'pk',
        'id',
        'username',
        'nome'
    ]

    alteracoes = []

    for anterior, atual in zip(historico, historico[1:]):

        perfil_anterior = anterior.get('perfil') or {}
        perfil_atual = atual.get('perfil') or {}

        mudancas = {}

        # ---------------------------------------------------------
        # DETECTA ALTERAÇÕES
        # ---------------------------------------------------------

        for campo in campos_comparacao:

            valor_anterior = perfil_anterior.get(campo)
            valor_atual = perfil_atual.get(campo)

            if valor_anterior != valor_atual:

                mudancas[campo] = {
                    'anterior': valor_anterior,
                    'atual': valor_atual
                }

        # ---------------------------------------------------------
        # SÓ REGISTRA SE EXISTIR ALTERAÇÃO
        # ---------------------------------------------------------

        if not mudancas:
            continue

        # ---------------------------------------------------------
        # IDENTIDADE DO USUÁRIO
        #
        # Utiliza o snapshot atual como referência da identidade.
        # ---------------------------------------------------------

        usuario = {
            'pk': perfil_atual.get('pk'),
            'id': perfil_atual.get('id'),
            'username': perfil_atual.get('username'),
            'nome': perfil_atual.get('nome')
        }

        # ---------------------------------------------------------
        # RESULTADO
        # ---------------------------------------------------------

        alteracoes.append({
            'usuario': usuario,

            'timestamp_anterior': anterior.get('timestamp_capture'),
            'timestamp_atual': atual.get('timestamp_capture'),

            'hash_anterior': anterior.get('hash'),
            'hash_atual': atual.get('hash'),

            'alteracoes': mudancas
        })

    return alteracoes





from datetime import datetime


def gerar_timeline_perfil(historico):
    """
    Gera uma Timeline de alterações do perfil diretamente
    a partir do histórico real de capturas.

    A Timeline:

        - compara snapshots consecutivos;
        - ignora alterações da foto de perfil;
        - identifica mudanças de seguidores e seguindo;
        - identifica mudanças nos totais de posts, reels e destaques;
        - calcula a variação numérica;
        - calcula o tempo entre capturas;
        - calcula o tempo desde o último evento;
        - gera títulos e descrições legíveis;
        - mantém os dados técnicos para análise posterior.

    Parâmetros
    ----------
    historico : list
        Lista de snapshots do perfil.

    Retorna
    -------
    list
        Lista de eventos da Timeline.
    """

    if not isinstance(historico, list) or len(historico) < 2:
        return []

    campos = [
        'biografia',
        'privado',
        'verificado',
        'memorializado',
        'seguidores',
        'seguindo',
        'total_posts',
        'total_reels',
        'total_destaques',
        'pronomes',
        'links'
    ]

    timeline = []

    ultimo_timestamp_evento = None

    # ---------------------------------------------------------
    # FUNÇÕES AUXILIARES
    # ---------------------------------------------------------

    def converter_timestamp(timestamp):
        """
        Converte timestamp ISO para datetime.
        """

        if not timestamp:
            return None

        try:
            return datetime.fromisoformat(
                timestamp.replace('Z', '+00:00')
            )

        except (ValueError, TypeError):
            return None

    def formatar_tempo(segundos):
        """
        Converte segundos para uma descrição legível.
        """

        if segundos is None:
            return None

        segundos = int(max(0, segundos))

        dias, resto = divmod(segundos, 86400)
        horas, resto = divmod(resto, 3600)
        minutos, segundos = divmod(resto, 60)

        partes = []

        if dias:
            partes.append(
                f"{dias} dia"
                if dias == 1
                else f"{dias} dias"
            )

        if horas:
            partes.append(
                f"{horas} hora"
                if horas == 1
                else f"{horas} horas"
            )

        if minutos:
            partes.append(
                f"{minutos} minuto"
                if minutos == 1
                else f"{minutos} minutos"
            )

        if segundos or not partes:
            partes.append(
                f"{segundos} segundo"
                if segundos == 1
                else f"{segundos} segundos"
            )

        return " e ".join(partes)

    def formatar_numero(valor):
        """
        Formata números para exibição.
        """

        if isinstance(valor, float) and valor.is_integer():
            valor = int(valor)

        if isinstance(valor, (int, float)):
            return f"{valor:,}".replace(",", ".")

        return str(valor)

    def valor_bool(valor):
        """
        Converte booleano para texto legível.
        """

        if valor is True:
            return "SIM"

        if valor is False:
            return "NÃO"

        return str(valor)

    # ---------------------------------------------------------
    # COMPARAÇÃO DOS SNAPSHOTS
    # ---------------------------------------------------------

    for anterior, atual in zip(historico, historico[1:]):

        perfil_anterior = anterior.get('perfil', {}) or {}
        perfil_atual = atual.get('perfil', {}) or {}

        timestamp_anterior = anterior.get(
            'timestamp_capture'
        )

        timestamp_atual = atual.get(
            'timestamp_capture'
        )

        dt_anterior = converter_timestamp(
            timestamp_anterior
        )

        dt_atual = converter_timestamp(
            timestamp_atual
        )

        # -----------------------------------------------------
        # TEMPO ENTRE CAPTURAS
        # -----------------------------------------------------

        tempo_entre_capturas_segundos = None

        if dt_anterior and dt_atual:

            tempo_entre_capturas_segundos = (
                dt_atual - dt_anterior
            ).total_seconds()

        # -----------------------------------------------------
        # DADOS DO USUÁRIO
        # -----------------------------------------------------

        usuario = {
            'pk': perfil_atual.get('pk'),
            'id': perfil_atual.get('id'),
            'username': perfil_atual.get('username'),
            'nome': perfil_atual.get('nome'),
            'foto_perfil': perfil_atual.get('foto_perfil')
        }

        # -----------------------------------------------------
        # VERIFICA CADA CAMPO
        # -----------------------------------------------------

        for campo in campos:

            valor_anterior = perfil_anterior.get(campo)
            valor_atual = perfil_atual.get(campo)

            if valor_anterior == valor_atual:
                continue

            # -------------------------------------------------
            # EVENTO BASE
            # -------------------------------------------------

            evento = {
                'timestamp': timestamp_atual,

                'timestamp_anterior': timestamp_anterior,
                'timestamp_atual': timestamp_atual,

                'usuario': usuario,

                'tipo': campo,

                'valor_anterior': valor_anterior,
                'valor_atual': valor_atual,

                'hash_anterior': anterior.get('hash'),
                'hash_atual': atual.get('hash')
            }

            # -------------------------------------------------
            # TEMPO ENTRE CAPTURAS
            # -------------------------------------------------

            evento['tempo_desde_anterior'] = {
                'segundos': tempo_entre_capturas_segundos,
                'texto': formatar_tempo(
                    tempo_entre_capturas_segundos
                )
            }

            # -------------------------------------------------
            # TEMPO DESDE O ÚLTIMO EVENTO
            # -------------------------------------------------

            tempo_desde_ultimo_evento_segundos = None

            if (
                ultimo_timestamp_evento
                and dt_atual
            ):

                dt_ultimo = converter_timestamp(
                    ultimo_timestamp_evento
                )

                if dt_ultimo:

                    tempo_desde_ultimo_evento_segundos = (
                        dt_atual - dt_ultimo
                    ).total_seconds()

            evento['tempo_desde_ultimo_evento'] = {
                'segundos': tempo_desde_ultimo_evento_segundos,
                'texto': formatar_tempo(
                    tempo_desde_ultimo_evento_segundos
                )
            }

            # -------------------------------------------------
            # CATEGORIA
            # -------------------------------------------------

            if campo in (
                'seguidores',
                'seguindo'
            ):
                categoria = 'rede'

            elif campo in (
                'privado',
                'verificado',
                'memorializado'
            ):
                categoria = 'status'

            elif campo in (
                'biografia',
                'pronomes',
                'links'
            ):
                categoria = 'perfil'

            elif campo in (
                'total_posts',
                'total_reels',
                'total_destaques'
            ):
                categoria = 'conteudo'

            else:
                categoria = 'outros'

            evento['categoria'] = categoria

            # -------------------------------------------------
            # VARIAÇÃO
            # -------------------------------------------------

            variacao = None

            if (
                isinstance(valor_anterior, (int, float))
                and not isinstance(valor_anterior, bool)
                and isinstance(valor_atual, (int, float))
                and not isinstance(valor_atual, bool)
            ):
                variacao = valor_atual - valor_anterior

            evento['variacao'] = variacao

            # -------------------------------------------------
            # SEGUIDORES
            # -------------------------------------------------

            if campo == 'seguidores':

                evento['tipo'] = 'seguidores'

                if variacao > 0:

                    evento['titulo'] = (
                        f"Ganhou {formatar_numero(variacao)} "
                        f"seguidor"
                        if variacao == 1
                        else
                        f"Ganhou {formatar_numero(variacao)} "
                        f"seguidores"
                    )

                    evento['descricao'] = (
                        f"Os seguidores passaram de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                elif variacao < 0:

                    quantidade = abs(variacao)

                    evento['titulo'] = (
                        f"Perdeu {formatar_numero(quantidade)} "
                        f"seguidor"
                        if quantidade == 1
                        else
                        f"Perdeu {formatar_numero(quantidade)} "
                        f"seguidores"
                    )

                    evento['descricao'] = (
                        f"Os seguidores caíram de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                else:

                    evento['titulo'] = (
                        "Seguidores alterados"
                    )

                    evento['descricao'] = (
                        f"Os seguidores passaram de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                if variacao is not None:

                    sinal = "+" if variacao > 0 else ""

                    evento['variacao_texto'] = (
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"seguidor"
                        if abs(variacao) == 1
                        else
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"seguidores"
                    )

            # -------------------------------------------------
            # SEGUINDO
            # -------------------------------------------------

            elif campo == 'seguindo':

                evento['tipo'] = 'seguindo'

                if variacao > 0:

                    evento['titulo'] = (
                        f"Começou a seguir "
                        f"{formatar_numero(variacao)} pessoa"
                        if variacao == 1
                        else
                        f"Começou a seguir "
                        f"{formatar_numero(variacao)} pessoas"
                    )

                    evento['descricao'] = (
                        f"Estava seguindo "
                        f"{formatar_numero(valor_anterior)} "
                        f"e passou a seguir "
                        f"{formatar_numero(valor_atual)}"
                    )

                elif variacao < 0:

                    quantidade = abs(variacao)

                    evento['titulo'] = (
                        f"Deixou de seguir "
                        f"{formatar_numero(quantidade)} pessoa"
                        if quantidade == 1
                        else
                        f"Deixou de seguir "
                        f"{formatar_numero(quantidade)} pessoas"
                    )

                    evento['descricao'] = (
                        f"Estava seguindo "
                        f"{formatar_numero(valor_anterior)} "
                        f"e passou a seguir "
                        f"{formatar_numero(valor_atual)}"
                    )

                else:

                    evento['titulo'] = (
                        "Seguindo alterado"
                    )

                    evento['descricao'] = (
                        f"O número de pessoas seguidas "
                        f"mudou de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                if variacao is not None:

                    sinal = "+" if variacao > 0 else ""

                    evento['variacao_texto'] = (
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"seguindo"
                    )

            # -------------------------------------------------
            # TOTAL DE POSTS
            # -------------------------------------------------

            elif campo == 'total_posts':

                evento['tipo'] = 'total_posts'

                if variacao > 0:

                    evento['titulo'] = (
                        f"Publicou {formatar_numero(variacao)} "
                        f"post"
                        if variacao == 1
                        else
                        f"Publicou {formatar_numero(variacao)} "
                        f"posts"
                    )

                    evento['descricao'] = (
                        f"O total de posts passou de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                elif variacao < 0:

                    quantidade = abs(variacao)

                    evento['titulo'] = (
                        f"Removeu {formatar_numero(quantidade)} "
                        f"post"
                        if quantidade == 1
                        else
                        f"Removeu {formatar_numero(quantidade)} "
                        f"posts"
                    )

                    evento['descricao'] = (
                        f"O total de posts caiu de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                else:

                    evento['titulo'] = (
                        "Total de posts alterado"
                    )

                    evento['descricao'] = (
                        f"O total de posts mudou de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                if variacao is not None:

                    sinal = "+" if variacao > 0 else ""

                    evento['variacao_texto'] = (
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"post"
                        if abs(variacao) == 1
                        else
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"posts"
                    )

            # -------------------------------------------------
            # TOTAL DE REELS
            # -------------------------------------------------

            elif campo == 'total_reels':

                evento['tipo'] = 'total_reels'

                if variacao > 0:

                    evento['titulo'] = (
                        f"Publicou {formatar_numero(variacao)} "
                        f"reel"
                        if variacao == 1
                        else
                        f"Publicou {formatar_numero(variacao)} "
                        f"reels"
                    )

                    evento['descricao'] = (
                        f"O total de reels passou de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                elif variacao < 0:

                    quantidade = abs(variacao)

                    evento['titulo'] = (
                        f"Removeu {formatar_numero(quantidade)} "
                        f"reel"
                        if quantidade == 1
                        else
                        f"Removeu {formatar_numero(quantidade)} "
                        f"reels"
                    )

                    evento['descricao'] = (
                        f"O total de reels caiu de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                else:

                    evento['titulo'] = (
                        "Total de reels alterado"
                    )

                    evento['descricao'] = (
                        f"O total de reels mudou de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                if variacao is not None:

                    sinal = "+" if variacao > 0 else ""

                    evento['variacao_texto'] = (
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"reel"
                        if abs(variacao) == 1
                        else
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"reels"
                    )

            # -------------------------------------------------
            # TOTAL DE DESTAQUES
            # -------------------------------------------------

            elif campo == 'total_destaques':

                evento['tipo'] = 'total_destaques'

                if variacao > 0:

                    evento['titulo'] = (
                        f"Criou {formatar_numero(variacao)} "
                        f"destaque"
                        if variacao == 1
                        else
                        f"Criou {formatar_numero(variacao)} "
                        f"destaques"
                    )

                    evento['descricao'] = (
                        f"O total de destaques passou de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                elif variacao < 0:

                    quantidade = abs(variacao)

                    evento['titulo'] = (
                        f"Removeu {formatar_numero(quantidade)} "
                        f"destaque"
                        if quantidade == 1
                        else
                        f"Removeu {formatar_numero(quantidade)} "
                        f"destaques"
                    )

                    evento['descricao'] = (
                        f"O total de destaques caiu de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                else:

                    evento['titulo'] = (
                        "Total de destaques alterado"
                    )

                    evento['descricao'] = (
                        f"O total de destaques mudou de "
                        f"{formatar_numero(valor_anterior)} "
                        f"para "
                        f"{formatar_numero(valor_atual)}"
                    )

                if variacao is not None:

                    sinal = "+" if variacao > 0 else ""

                    evento['variacao_texto'] = (
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"destaque"
                        if abs(variacao) == 1
                        else
                        f"{sinal}"
                        f"{formatar_numero(variacao)} "
                        f"destaques"
                    )

            # -------------------------------------------------
            # PRIVADO
            # -------------------------------------------------

            elif campo == 'privado':

                evento['tipo'] = 'privacidade'

                if (
                    valor_anterior is True
                    and valor_atual is False
                ):

                    evento['titulo'] = (
                        "O perfil ficou público"
                    )

                    evento['descricao'] = (
                        "O perfil deixou de ser privado"
                    )

                elif (
                    valor_anterior is False
                    and valor_atual is True
                ):

                    evento['titulo'] = (
                        "O perfil ficou privado"
                    )

                    evento['descricao'] = (
                        "O perfil tornou-se privado"
                    )

                else:

                    evento['titulo'] = (
                        "Privacidade alterada"
                    )

                    evento['descricao'] = (
                        f"Privacidade mudou de "
                        f"{valor_bool(valor_anterior)} "
                        f"para "
                        f"{valor_bool(valor_atual)}"
                    )

            # -------------------------------------------------
            # VERIFICADO
            # -------------------------------------------------

            elif campo == 'verificado':

                evento['tipo'] = 'verificacao'

                if (
                    valor_anterior is False
                    and valor_atual is True
                ):

                    evento['titulo'] = (
                        "Perfil verificado"
                    )

                    evento['descricao'] = (
                        "O perfil passou a ser verificado"
                    )

                elif (
                    valor_anterior is True
                    and valor_atual is False
                ):

                    evento['titulo'] = (
                        "Verificação removida"
                    )

                    evento['descricao'] = (
                        "O perfil deixou de ser verificado"
                    )

                else:

                    evento['titulo'] = (
                        "Verificação alterada"
                    )

                    evento['descricao'] = (
                        f"Verificação mudou de "
                        f"{valor_bool(valor_anterior)} "
                        f"para "
                        f"{valor_bool(valor_atual)}"
                    )

            # -------------------------------------------------
            # MEMORIALIZADO
            # -------------------------------------------------

            elif campo == 'memorializado':

                evento['tipo'] = 'memorializacao'

                if (
                    valor_anterior is False
                    and valor_atual is True
                ):

                    evento['titulo'] = (
                        "Perfil memorializado"
                    )

                    evento['descricao'] = (
                        "O perfil passou a ser memorializado"
                    )

                elif (
                    valor_anterior is True
                    and valor_atual is False
                ):

                    evento['titulo'] = (
                        "Memorialização removida"
                    )

                    evento['descricao'] = (
                        "O perfil deixou de ser memorializado"
                    )

                else:

                    evento['titulo'] = (
                        "Memorialização alterada"
                    )

                    evento['descricao'] = (
                        f"Memorialização mudou de "
                        f"{valor_bool(valor_anterior)} "
                        f"para "
                        f"{valor_bool(valor_atual)}"
                    )

            # -------------------------------------------------
            # BIOGRAFIA
            # -------------------------------------------------

            elif campo == 'biografia':

                evento['tipo'] = 'biografia'

                evento['titulo'] = (
                    "Alterou a biografia"
                )

                evento['descricao'] = (
                    "A biografia do perfil foi modificada"
                )

            # -------------------------------------------------
            # PRONOMES
            # -------------------------------------------------

            elif campo == 'pronomes':

                evento['tipo'] = 'pronomes'

                evento['titulo'] = (
                    "Alterou os pronomes"
                )

                evento['descricao'] = (
                    "Os pronomes do perfil foram modificados"
                )

            # -------------------------------------------------
            # LINKS
            # -------------------------------------------------

            elif campo == 'links':

                evento['tipo'] = 'links'

                evento['titulo'] = (
                    "Alterou os links"
                )

                evento['descricao'] = (
                    "Os links do perfil foram modificados"
                )

            # -------------------------------------------------
            # ADICIONA EVENTO
            # -------------------------------------------------

            timeline.append(evento)

            # O timestamp do snapshot passa a ser
            # o último evento registrado.

            ultimo_timestamp_evento = timestamp_atual

    return timeline





from datetime import datetime


def gerar_historico_perfil(historico):
    """
    Gera o histórico individual das informações de um perfil.

    Trabalha diretamente sobre o histórico real de capturas.

    Retorna
    -------
    dict
        Histórico organizado por campo.
    """

    if not isinstance(historico, list) or not historico:
        return {}

    campos = [
        'biografia',
        'privado',
        'verificado',
        'memorializado',
        'seguidores',
        'seguindo',
        'total_posts',
        'total_reels',
        'total_destaques',
        'pronomes',
        'links'
    ]

    nomes_campos = {
        'biografia': 'Biografia',
        'privado': 'Privacidade',
        'verificado': 'Verificação',
        'memorializado': 'Memorializado',
        'seguidores': 'Seguidores',
        'seguindo': 'Seguindo',
        'total_posts': 'Total de Posts',
        'total_reels': 'Total de Reels',
        'total_destaques': 'Total de Destaques',
        'pronomes': 'Pronomes',
        'links': 'Links'
    }

    resultado = {
        'usuario': {},

        'seguidores': [],
        'seguindo': [],

        'total_posts': [],
        'total_reels': [],
        'total_destaques': [],

        'privado': [],
        'biografia': [],
        'verificado': [],
        'memorializado': [],
        'pronomes': [],
        'links': []
    }

    # ---------------------------------------------------------
    # USUÁRIO
    # ---------------------------------------------------------

    primeiro = historico[0]

    perfil = primeiro.get(
        'perfil',
        {}
    ) or {}

    resultado['usuario'] = {
        'pk': perfil.get('pk'),
        'id': perfil.get('id'),
        'username': perfil.get('username'),
        'nome': perfil.get('nome')
    }

    # ---------------------------------------------------------
    # VALORES ANTERIORES
    # ---------------------------------------------------------

    perfil_anterior = perfil.copy()

    timestamps_anteriores = {}

    for campo in campos:

        valor_inicial = perfil_anterior.get(campo)

        # Guarda o primeiro estado do campo.
        resultado[campo].append({
            'campo': campo,

            'nome': nomes_campos.get(
                campo,
                campo
            ),

            'valor': valor_inicial,

            'timestamp': primeiro.get(
                'timestamp_capture'
            ),

            'tipo': 'inicial'
        })

        timestamps_anteriores[campo] = (
            primeiro.get(
                'timestamp_capture'
            )
        )

    # ---------------------------------------------------------
    # PERCORRE AS CAPTURAS
    # ---------------------------------------------------------

    for registro in historico[1:]:

        perfil_atual = registro.get(
            'perfil',
            {}
        ) or {}

        timestamp_atual = registro.get(
            'timestamp_capture'
        )

        for campo in campos:

            valor_anterior = perfil_anterior.get(
                campo
            )

            valor_atual = perfil_atual.get(
                campo
            )

            # Nada mudou.
            if valor_anterior == valor_atual:
                continue

            timestamp_anterior = (
                timestamps_anteriores.get(
                    campo
                )
            )

            # -------------------------------------------------
            # TEMPO DESDE A ÚLTIMA ALTERAÇÃO
            # -------------------------------------------------

            tempo_segundos = None

            try:

                if (
                    timestamp_anterior
                    and timestamp_atual
                ):

                    dt_anterior = datetime.fromisoformat(
                        timestamp_anterior.replace(
                            'Z',
                            '+00:00'
                        )
                    )

                    dt_atual = datetime.fromisoformat(
                        timestamp_atual.replace(
                            'Z',
                            '+00:00'
                        )
                    )

                    tempo_segundos = int(
                        (
                            dt_atual - dt_anterior
                        ).total_seconds()
                    )

            except (ValueError, TypeError):
                tempo_segundos = None

            # -------------------------------------------------
            # VARIAÇÃO
            # -------------------------------------------------

            variacao = None
            direcao = None

            if (
                isinstance(
                    valor_anterior,
                    (int, float)
                )
                and not isinstance(
                    valor_anterior,
                    bool
                )
                and isinstance(
                    valor_atual,
                    (int, float)
                )
                and not isinstance(
                    valor_atual,
                    bool
                )
            ):

                variacao = (
                    valor_atual -
                    valor_anterior
                )

                if variacao > 0:
                    direcao = 'aumento'

                elif variacao < 0:
                    direcao = 'reducao'

                else:
                    direcao = 'sem_alteracao'

            # -------------------------------------------------
            # DESCRIÇÃO
            # -------------------------------------------------

            descricao = None

            # -------------------------------------------------
            # SEGUIDORES
            # -------------------------------------------------

            if campo == 'seguidores':

                if variacao is not None:

                    if variacao > 0:

                        descricao = (
                            f'+{variacao} seguidores'
                        )

                    elif variacao < 0:

                        descricao = (
                            f'{variacao} seguidores'
                        )

            # -------------------------------------------------
            # SEGUINDO
            # -------------------------------------------------

            elif campo == 'seguindo':

                if variacao is not None:

                    if variacao > 0:

                        descricao = (
                            f'Seguiu +{variacao}'
                        )

                    elif variacao < 0:

                        descricao = (
                            f'Deixou de seguir '
                            f'{abs(variacao)}'
                        )

            # -------------------------------------------------
            # TOTAL DE POSTS
            # -------------------------------------------------

            elif campo == 'total_posts':

                if variacao is not None:

                    if variacao > 0:

                        descricao = (
                            f'+{variacao} posts'
                        )

                    elif variacao < 0:

                        descricao = (
                            f'{variacao} posts'
                        )

            # -------------------------------------------------
            # TOTAL DE REELS
            # -------------------------------------------------

            elif campo == 'total_reels':

                if variacao is not None:

                    if variacao > 0:

                        descricao = (
                            f'+{variacao} reels'
                        )

                    elif variacao < 0:

                        descricao = (
                            f'{variacao} reels'
                        )

            # -------------------------------------------------
            # TOTAL DE DESTAQUES
            # -------------------------------------------------

            elif campo == 'total_destaques':

                if variacao is not None:

                    if variacao > 0:

                        descricao = (
                            f'+{variacao} destaques'
                        )

                    elif variacao < 0:

                        descricao = (
                            f'{variacao} destaques'
                        )

            # -------------------------------------------------
            # PRIVADO
            # -------------------------------------------------

            elif campo == 'privado':

                if (
                    valor_anterior is True
                    and valor_atual is False
                ):

                    descricao = (
                        'Conta ficou pública'
                    )

                elif (
                    valor_anterior is False
                    and valor_atual is True
                ):

                    descricao = (
                        'Conta ficou privada'
                    )

            # -------------------------------------------------
            # VERIFICADO
            # -------------------------------------------------

            elif campo == 'verificado':

                if valor_atual is True:

                    descricao = (
                        'Conta foi verificada'
                    )

                else:

                    descricao = (
                        'Verificação removida'
                    )

            # -------------------------------------------------
            # MEMORIALIZADO
            # -------------------------------------------------

            elif campo == 'memorializado':

                if valor_atual is True:

                    descricao = (
                        'Conta foi memorializada'
                    )

                else:

                    descricao = (
                        'Conta deixou de ser '
                        'memorializada'
                    )

            # -------------------------------------------------
            # BIOGRAFIA
            # -------------------------------------------------

            elif campo == 'biografia':

                descricao = (
                    'Biografia alterada'
                )

            # -------------------------------------------------
            # PRONOMES
            # -------------------------------------------------

            elif campo == 'pronomes':

                descricao = (
                    'Pronomes alterados'
                )

            # -------------------------------------------------
            # LINKS
            # -------------------------------------------------

            elif campo == 'links':

                descricao = (
                    'Links do perfil alterados'
                )

            # -------------------------------------------------
            # REGISTRO
            # -------------------------------------------------

            item = {
                'campo': campo,

                'nome': nomes_campos.get(
                    campo,
                    campo
                ),

                'valor_anterior': valor_anterior,

                'valor_atual': valor_atual,

                'variacao': variacao,

                'direcao': direcao,

                'descricao': descricao,

                'timestamp': timestamp_atual,

                'timestamp_anterior': timestamp_anterior,

                'tempo_desde_anterior_segundos': (
                    tempo_segundos
                )
            }

            resultado[campo].append(
                item
            )

            # A próxima alteração deste campo será calculada
            # a partir desta captura.
            timestamps_anteriores[campo] = (
                timestamp_atual
            )

        # Atualiza o perfil de referência.
        perfil_anterior = perfil_atual.copy()

    return resultado



def analisando_comportamento(historico,cliente_usuario):

    id_pk_usuario = f"{historico[0]['perfil']['pk']}.json"

    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_resumo = caminho_dados_usuario(cliente_usuario, 'resumo', id_pk_usuario)
    
    caminho_resumo.parent.mkdir(parents=True,exist_ok=True)

    if not caminho_resumo.exists():
        caminho_resumo.write_text("[]",encoding="utf-8")

    timiline         = gerar_timeline_perfil(historico)
    historico_perfil = gerar_historico_perfil(historico)
    
    resumo = {
            'timiline':timiline,
            'historico':historico_perfil
        }

    salvar_dados_json(resumo,caminho_resumo)
    
    
    return resumo



def resumo_perfil(pk, cliente_usuario='admin'):
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    historico = carregar_dados(caminho_dados_usuario(cliente_usuario, 'historico', f'{pk}.json'))
    return historico



if __name__ == "__main__":
    
    cliente_usuario = 'admin'
    
    pk = 1030845726
    
    historico = resumo_perfil(pk, cliente_usuario)
    
    resultado = analisando_comportamento(historico,cliente_usuario)




