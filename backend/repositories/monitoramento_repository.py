from toolFarejador.monitoramento.toolAtivarMonitoramento import monitorar_perfil
from toolFarejador.monitoramento.toolMonitoramentoSistema import solicitar_atualizacao_monitoramento
from toolFarejador.notificacoes.toolNotificacao import notificacao_movimento


def set_monitoring_data(cliente_usuario, perfil, enabled):
    return monitorar_perfil(cliente_usuario, perfil, monitorando=enabled)


def solicitar_atualizacao():
    return solicitar_atualizacao_monitoramento()


def notificar_movimentos(usernames, cliente_usuario):
    return notificacao_movimento(usernames, cliente_usuario)
