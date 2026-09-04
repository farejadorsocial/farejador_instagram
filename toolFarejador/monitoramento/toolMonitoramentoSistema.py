from datetime import datetime
import json
import os
from pathlib import Path
import random
import threading
import time

from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario, USER_ROOT, migrar_dados_legados


def caminho_base(*caminho_final, nome_projeto="instagram"):
    try:
        caminho_atual = Path(__file__).resolve()
    except NameError:
        caminho_atual = Path.cwd().resolve()

    for pasta in [caminho_atual] + list(caminho_atual.parents):
        if pasta.name == nome_projeto:
            return pasta.joinpath(*caminho_final)

    raise FileNotFoundError(f"Não foi encontrada a pasta '{nome_projeto}'.")


def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def carregar_config_sistema():
    caminho = caminho_base("sistema", "config", "monitoramento_perfis.json")
    return carregar_dados(caminho)


def salvar_registro_monitoramento(registros):
    """
    Salva o estado atual do monitoramento em:
    sistema/log/monitoramento_perfis.json

    A gravação é atômica para que a interface possa acompanhar o arquivo
    sem correr o risco de ler um JSON parcialmente escrito.
    """
    caminho = caminho_base("sistema", "log", "monitoramento_perfis.json")
    caminho.parent.mkdir(parents=True, exist_ok=True)

    caminho_tmp = caminho.with_suffix(".tmp")

    with open(caminho_tmp, "w", encoding="utf-8") as arquivo:
        json.dump(
            registros,
            arquivo,
            ensure_ascii=False,
            indent=4,
        )
        arquivo.flush()
        os.fsync(arquivo.fileno())

    caminho_tmp.replace(caminho)


def criar_registro_monitoramento(
    perfis,
    ativos,
    CFG=None,
    monitorando=True,
    intervalo=None,
    erro=False,
    perfil_erro=None,
    mensagem_erro=None,
    ciclo=0,
):
    """
    Monta o snapshot do monitoramento atual.

    'perfis' contém todos os perfis encontrados.
    'ativos' contém somente os perfis atualmente habilitados.
    """
    agora = datetime.now().isoformat(timespec="seconds")

    return {
        'config_sistema':CFG,
        "perfis": {
            "perfis": perfis,
            "ativos": ativos,
            "total": len(perfis),
            "total_ativos": len(ativos),
        },
        "status": {
            "monitorando": bool(monitorando),
            "intervalo":intervalo,
            "erro": bool(erro),
        },
        "erro": {
            "perfil": perfil_erro,
            "mensagem": mensagem_erro,
        },
        "ciclo": ciclo,
        "ultima_atualizacao": agora,
        "timestamp": agora,
    }


def carregar_perfis_para_monitoramento():
    """Carrega perfis monitorados de todos os clientes."""
    resultado = []

    if not USER_ROOT.exists():
        return resultado

    for pasta_cliente in USER_ROOT.iterdir():
        if not pasta_cliente.is_dir():
            continue

        pasta_monitoramento = caminho_dados_usuario(
            pasta_cliente.name,
            "monitoramento",
        )

        if not pasta_monitoramento.exists():
            continue

        for arquivo in pasta_monitoramento.glob("*.json"):
            try:
                registro = carregar_dados(arquivo)
            except (OSError, json.JSONDecodeError):
                continue

            if isinstance(registro, dict):
                registro["cliente_usuario"] = pasta_cliente.name
                resultado.append(registro)

    return resultado


_STOP_EVENT = threading.Event()
_WAKE_EVENT = threading.Event()


def solicitar_parada_monitoramento():
    _STOP_EVENT.set()
    _WAKE_EVENT.set()


def solicitar_atualizacao_monitoramento():
    """Acorda o worker quando uma configuração/perfil muda."""
    _WAKE_EVENT.set()


def _aguardar_monitoramento(segundos):
    """Espera, mas permite que o clique do usuário acorde o worker."""
    segundos = max(0.1, float(segundos))
    acordou = _WAKE_EVENT.wait(segundos)
    if acordou:
        _WAKE_EVENT.clear()
    return acordou


def monitoramento_perfis_tempo_real():
    """Worker global: cada perfil é monitorado dentro do cliente correto."""
    
    from toolFarejador.monitoramento.toolMonitorarPerfilSalvo import monitorar_perfil_usuario
    from toolFarejador.notificacoes.toolNotificacao import notificacao_movimento
    from toolFarejador.sistema.toolSistemaPublico import sincronizar_dados_publicos

    _STOP_EVENT.clear()
    _WAKE_EVENT.clear()

    migrar_dados_legados()

    ciclo = 0

    while not _STOP_EVENT.is_set():

        try:
            # =========================================================
            # CARREGA CONFIGURAÇÃO ATUAL
            # =========================================================

            config_sistema = carregar_config_sistema() or {}

            config_sistema.setdefault(
                "monitoramento_ativo",
                True
            )

            config_sistema.setdefault(
                "intervalo",
                600
            )

            print(f'''Monitaramento Iniciado , Intervalo de  : 
                 { config_sistema["intervalo"]} segundos''')

            print()

            try:
                intervalo_global = max(
                    1,
                    int(config_sistema.get("intervalo", 600))
                )

            except (TypeError, ValueError):

                intervalo_global = 600


            # =========================================================
            # PAUSA GLOBAL
            # =========================================================

            if not config_sistema.get(
                "monitoramento_ativo",
                True
            ):

                perfis = carregar_perfis_para_monitoramento()

                ativos = [
                    p
                    for p in perfis
                    if p.get("monitorando") is True
                ]

                ciclo += 1

                registros = criar_registro_monitoramento(
                    perfis,
                    ativos,
                    CFG=config_sistema,
                    monitorando=False,
                    intervalo=intervalo_global,
                    erro=False,
                    ciclo=ciclo
                )

                registros["motivo"] = (
                    "pausado_pela_configuracao"
                )

                salvar_registro_monitoramento(
                    registros
                )

                # -----------------------------------------------------
                # Mesmo pausado, aguarda o intervalo configurado.
                #
                # A espera continua interruptível através de
                # solicitar_atualizacao_monitoramento().
                # -----------------------------------------------------

                _aguardar_monitoramento(
                    intervalo_global
                )

                continue


            # =========================================================
            # INÍCIO DO CICLO
            # =========================================================

            perfis = carregar_perfis_para_monitoramento()

            ativos = [
                p
                for p in perfis
                if p.get("monitorando") is True
            ]

            ciclo += 1


            # Registra o início do ciclo.

            salvar_registro_monitoramento(
                criar_registro_monitoramento(
                    perfis,
                    ativos,
                    CFG=config_sistema,
                    monitorando=True,
                    intervalo=intervalo_global,
                    erro=False,
                    ciclo=ciclo
                )
            )


            # =========================================================
            # NENHUM PERFIL ATIVO
            # =========================================================

            if not ativos:

                # Não existe trabalho para executar.
                #
                # Mesmo assim, o próximo ciclo somente será iniciado
                # depois do intervalo configurado.

                _aguardar_monitoramento(
                    intervalo_global
                )

                continue


            # =========================================================
            # PROCESSAMENTO DOS PERFIS
            # =========================================================

            erros = []

            processados = 0

            ciclo_interrompido = False


            for registro in ativos:

                if _STOP_EVENT.is_set():
                    break


                # -----------------------------------------------------
                # Se houve alteração manual:
                #
                # - monitorar
                # - pausar
                # - alteração de perfil
                #
                # interrompe o ciclo atual e recarrega a lista.
                # -----------------------------------------------------

                if _WAKE_EVENT.is_set():

                    _WAKE_EVENT.clear()

                    ciclo_interrompido = True

                    break


                cliente_usuario = registro.get(
                    "cliente_usuario"
                )

                username = registro.get(
                    "username"
                )


                if not cliente_usuario or not username:
                    continue


                # =====================================================
                # RELÊ O ESTADO DO PERFIL
                # =====================================================

                caminho_monitor = caminho_dados_usuario(
                    cliente_usuario,
                    "monitoramento",
                    f"{registro.get('pk')}.json",
                )


                try:

                    estado_atual = carregar_dados(
                        caminho_monitor
                    )

                except (
                    OSError,
                    json.JSONDecodeError
                ):

                    estado_atual = {}


                # O perfil pode ter sido pausado depois que a lista
                # de ativos foi carregada.

                if not estado_atual.get(
                    "monitorando",
                    False
                ):
                    continue


                # =====================================================
                # CAPTURA
                # =====================================================

                try:

                    monitorar_perfil_usuario(
                        username,
                        cliente_usuario,
                    )


                    # =================================================
                    # NOTIFICAÇÃO / FEED
                    # =================================================

                    notificacao_movimento(
                        [username],
                        cliente_usuario,
                    )


                    # =================================================
                    # PUBLICAÇÃO DOS DADOS PÚBLICOS
                    # =================================================

                    if cliente_usuario == "admin":

                        sincronizar_dados_publicos()


                    processados += 1


                    # =================================================
                    # SALVA PROGRESSO PARCIAL
                    # =================================================

                    parcial = criar_registro_monitoramento(
                        perfis,
                        ativos,
                        CFG=config_sistema,
                        monitorando=True,
                        intervalo=intervalo_global,
                        erro=False,
                        ciclo=ciclo,
                    )


                    parcial[
                        "ultimo_perfil_processado"
                    ] = {
                        "cliente_usuario": cliente_usuario,
                        "username": username,
                    }


                    parcial[
                        "resultado_ciclo"
                    ] = {
                        "total_processados": processados,
                        "total_erros": len(erros),
                        "total_sucessos": processados,
                    }


                    salvar_registro_monitoramento(
                        parcial
                    )


                except Exception as erro:

                    erro_registro = {
                        "perfil": registro,
                        "mensagem": str(erro),
                        "timestamp": datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    }


                    erros.append(
                        erro_registro
                    )


                    print(
                        f"[monitoramento] Falha em "
                        f"@{username} "
                        f"({cliente_usuario}): "
                        f"{erro}"
                    )


                # =====================================================
                # INTERVALO ENTRE PERFIS
                # =====================================================

                try:

                    intervalo_perfil = max(
                        1,
                        int(
                            registro.get(
                                "sleep",
                                10
                            )
                        )
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    intervalo_perfil = 10


                # Mantém o comportamento existente de intervalo
                # aleatório entre perfis.

                if _aguardar_monitoramento(
                    random.randint(
                        1,
                        intervalo_perfil
                    )
                ):

                    ciclo_interrompido = True

                    break


            # =========================================================
            # FECHAMENTO DO CICLO
            # =========================================================

            primeiro_erro = (
                erros[0]
                if erros
                else None
            )


            registros = criar_registro_monitoramento(
                perfis=perfis,
                ativos=ativos,
                CFG=config_sistema,
                monitorando=True,
                intervalo=intervalo_global,
                erro=bool(erros),
                perfil_erro=(
                    primeiro_erro.get("perfil")
                    if primeiro_erro
                    else None
                ),
                mensagem_erro=(
                    primeiro_erro.get("mensagem")
                    if primeiro_erro
                    else None
                ),
                ciclo=ciclo,
            )


            registros["erros"] = erros


            registros[
                "resultado_ciclo"
            ] = {
                "total_processados": processados,
                "total_erros": len(erros),
                "total_sucessos": processados,
            }





            salvar_registro_monitoramento(
                registros
            )


            # =========================================================
            # CICLO INTERROMPIDO MANUALMENTE
            # =========================================================

            if (
                ciclo_interrompido
                and not _STOP_EVENT.is_set()
            ):

                # Não espera os 900 segundos.
                #
                # Uma alteração manual deve fazer o sistema
                # recarregar a lista imediatamente.

                continue


            # =========================================================
            # INTERVALO ENTRE CICLOS
            # =========================================================
            #
            # ESTE É O PONTO PRINCIPAL DA CORREÇÃO.
            #
            # Depois que TODOS os perfis foram processados,
            # o sistema espera exatamente o intervalo definido
            # em monitoramento_perfis.json.
            #
            # Exemplo:
            #
            # intervalo = 900
            #
            # ciclo terminou às 01:00:00
            # próxima execução = 01:15:00
            #
            # Não existe mais limite artificial de 30 segundos.
            #

            if not _STOP_EVENT.is_set():

                print('---AGUARDANDO---')

                print(f'''
                Proxima Rodada de Monitoramento de Perfil
                Em -> {intervalo_global}, segundos..
                ''')
                          
                print()

                _aguardar_monitoramento(
                    intervalo_global
                )

            


        except Exception as erro:

            print(
                f"[monitoramento] "
                f"Erro no worker: {erro}"
            )

            # ---------------------------------------------------------
            # Se ocorrer um erro inesperado no worker, não entra em
            # loop agressivo.
            #
            # Aguarda o intervalo configurado antes de tentar
            # novamente.
            # ---------------------------------------------------------

            try:

                intervalo_erro = max(
                    1,
                    int(
                        carregar_config_sistema()
                        .get(
                            "intervalo",
                            600
                        )
                    )
                )

            except Exception:

                intervalo_erro = 600


            if not _STOP_EVENT.is_set():

                _aguardar_monitoramento(
                    intervalo_erro
                )



if __name__ == "__main__":
    monitoramento_perfis_tempo_real()