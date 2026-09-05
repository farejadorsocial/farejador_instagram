from datetime import datetime
import json
import os
from pathlib import Path
import random
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import Monitoramento


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
    """Salva o estado operacional do worker para compatibilidade com a interface."""
    caminho = caminho_base("sistema", "log", "monitoramento_perfis.json")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho_tmp = caminho.with_suffix(".tmp")

    with open(caminho_tmp, "w", encoding="utf-8") as arquivo:
        json.dump(registros, arquivo, ensure_ascii=False, indent=4)
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
    agora = datetime.now().isoformat(timespec="seconds")
    return {
        "config_sistema": CFG,
        "perfis": {
            "perfis": perfis,
            "ativos": ativos,
            "total": len(perfis),
            "total_ativos": len(ativos),
        },
        "status": {
            "monitorando": bool(monitorando),
            "intervalo": intervalo,
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


def _monitoramentos_postgresql():
    with Session(get_engine()) as session:
        registros = session.scalars(
            select(Monitoramento).order_by(Monitoramento.cliente_usuario, Monitoramento.id)
        ).all()

    resultado = []
    for registro in registros:
        dados = dict(registro.dados or {})
        dados["pk"] = registro.instagram_pk
        dados["username"] = registro.username or dados.get("username")
        dados["monitorando"] = bool(registro.monitorando)
        dados["sleep"] = registro.sleep
        dados["cliente_usuario"] = registro.cliente_usuario
        resultado.append(dados)
    return resultado


def carregar_perfis_para_monitoramento():
    """Carrega perfis monitorados exclusivamente do PostgreSQL."""
    try:
        return _monitoramentos_postgresql()
    except Exception as erro:
        print(f"[monitoramento] Falha ao carregar monitoramentos do PostgreSQL: {erro}")
        return []


def _estado_monitoramento(cliente_usuario, pk):
    with Session(get_engine()) as session:
        registro = session.scalar(
            select(Monitoramento).where(
                Monitoramento.cliente_usuario == cliente_usuario,
                Monitoramento.instagram_pk == str(pk),
            )
        )

    if registro is None:
        return None

    dados = dict(registro.dados or {})
    dados["pk"] = registro.instagram_pk
    dados["username"] = registro.username or dados.get("username")
    dados["monitorando"] = bool(registro.monitorando)
    dados["sleep"] = registro.sleep
    dados["cliente_usuario"] = registro.cliente_usuario
    return dados


_STOP_EVENT = threading.Event()
_WAKE_EVENT = threading.Event()


def solicitar_parada_monitoramento():
    _STOP_EVENT.set()
    _WAKE_EVENT.set()


def solicitar_atualizacao_monitoramento():
    """Acorda o worker quando uma configuração/perfil muda."""
    _WAKE_EVENT.set()


def _aguardar_monitoramento(segundos):
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
    ciclo = 0

    while not _STOP_EVENT.is_set():
        try:
            config_sistema = carregar_config_sistema() or {}
            config_sistema.setdefault("monitoramento_ativo", True)
            config_sistema.setdefault("intervalo", 600)

            try:
                intervalo_global = max(1, int(config_sistema.get("intervalo", 600)))
            except (TypeError, ValueError):
                intervalo_global = 600

            perfis = carregar_perfis_para_monitoramento()
            ativos = [p for p in perfis if p.get("monitorando") is True]
            ciclo += 1

            if not config_sistema.get("monitoramento_ativo", True):
                registros = criar_registro_monitoramento(
                    perfis,
                    ativos,
                    CFG=config_sistema,
                    monitorando=False,
                    intervalo=intervalo_global,
                    ciclo=ciclo,
                )
                registros["motivo"] = "pausado_pela_configuracao"
                salvar_registro_monitoramento(registros)
                _aguardar_monitoramento(intervalo_global)
                continue

            salvar_registro_monitoramento(
                criar_registro_monitoramento(
                    perfis,
                    ativos,
                    CFG=config_sistema,
                    monitorando=True,
                    intervalo=intervalo_global,
                    ciclo=ciclo,
                )
            )

            if not ativos:
                _aguardar_monitoramento(intervalo_global)
                continue

            erros = []
            processados = 0
            ciclo_interrompido = False

            for registro in ativos:
                if _STOP_EVENT.is_set():
                    break

                if _WAKE_EVENT.is_set():
                    _WAKE_EVENT.clear()
                    ciclo_interrompido = True
                    break

                cliente_usuario = registro.get("cliente_usuario")
                username = registro.get("username")
                pk = registro.get("pk")

                if not cliente_usuario or not username or pk is None:
                    continue

                estado_atual = _estado_monitoramento(cliente_usuario, pk)
                if not estado_atual or not estado_atual.get("monitorando", False):
                    continue

                try:
                    monitorar_perfil_usuario(username, cliente_usuario)
                    notificacao_movimento([username], cliente_usuario)

                    if cliente_usuario == "admin":
                        sincronizar_dados_publicos()

                    processados += 1

                    parcial = criar_registro_monitoramento(
                        perfis,
                        ativos,
                        CFG=config_sistema,
                        monitorando=True,
                        intervalo=intervalo_global,
                        ciclo=ciclo,
                    )
                    parcial["ultimo_perfil_processado"] = {
                        "cliente_usuario": cliente_usuario,
                        "username": username,
                    }
                    parcial["resultado_ciclo"] = {
                        "total_processados": processados,
                        "total_erros": len(erros),
                        "total_sucessos": processados,
                    }
                    salvar_registro_monitoramento(parcial)

                except Exception as erro:
                    erro_registro = {
                        "perfil": registro,
                        "mensagem": str(erro),
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                    }
                    erros.append(erro_registro)
                    print(
                        f"[monitoramento] Falha em @{username} "
                        f"({cliente_usuario}): {erro}"
                    )

                try:
                    intervalo_perfil = max(1, int(registro.get("sleep", 10)))
                except (TypeError, ValueError):
                    intervalo_perfil = 10

                if _aguardar_monitoramento(random.randint(1, intervalo_perfil)):
                    ciclo_interrompido = True
                    break

            primeiro_erro = erros[0] if erros else None
            registros = criar_registro_monitoramento(
                perfis=perfis,
                ativos=ativos,
                CFG=config_sistema,
                monitorando=True,
                intervalo=intervalo_global,
                erro=bool(erros),
                perfil_erro=primeiro_erro.get("perfil") if primeiro_erro else None,
                mensagem_erro=primeiro_erro.get("mensagem") if primeiro_erro else None,
                ciclo=ciclo,
            )
            registros["erros"] = erros
            registros["resultado_ciclo"] = {
                "total_processados": processados,
                "total_erros": len(erros),
                "total_sucessos": processados,
            }
            salvar_registro_monitoramento(registros)

            if ciclo_interrompido and not _STOP_EVENT.is_set():
                continue

            if not _STOP_EVENT.is_set():
                _aguardar_monitoramento(intervalo_global)

        except Exception as erro:
            print(f"[monitoramento] Erro no worker: {erro}")
            try:
                intervalo_erro = max(1, int((carregar_config_sistema() or {}).get("intervalo", 600)))
            except Exception:
                intervalo_erro = 600
            if not _STOP_EVENT.is_set():
                _aguardar_monitoramento(intervalo_erro)


if __name__ == "__main__":
    monitoramento_perfis_tempo_real()
