from datetime import datetime


def criando_registro_monitorar_perfil(selecionado, monitorando):
    pk = selecionado['perfil']['pk']
    username = selecionado['perfil']['username']
    nome = selecionado['perfil']['nome']
    return {
        'pk': pk,
        'username': username,
        'nome': nome,
        'sleep': 10,
        'monitorando': bool(monitorando),
        'atualizado': datetime.now().isoformat(),
    }


def _sincronizar_postgresql(cliente_usuario, dados):
    from backend.database.sync import sincronizar_monitoramento
    sincronizar_monitoramento(cliente_usuario, dados)


def lista_perfil_monitorados(cliente_usuario):
    """Retorna exclusivamente o estado persistente do PostgreSQL."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from backend.database.connection import get_engine
    from backend.database.models import Monitoramento

    with Session(get_engine()) as session:
        registros = session.scalars(
            select(Monitoramento)
            .where(Monitoramento.cliente_usuario == cliente_usuario)
            .order_by(Monitoramento.id)
        ).all()
        return [
            r.dados or {
                'pk': r.instagram_pk,
                'username': r.username,
                'monitorando': r.monitorando,
                'sleep': r.sleep,
            }
            for r in registros
        ]


def monitorar_perfil(cliente_usuario, selecionado, monitorando=False):
    """Cria/atualiza o estado de monitoramento diretamente no PostgreSQL."""
    resultado = criando_registro_monitorar_perfil(selecionado, monitorando)
    _sincronizar_postgresql(cliente_usuario, resultado)
    return resultado


if __name__ == "__main__":
    cliente_usuario = 'admin'
    selecionado = {'perfil': {'pk': 65832742299, 'username': 'thallyta.isabelly', 'nome': 'T'}}
    monitorar = monitorar_perfil(cliente_usuario, selecionado, monitorando=True)
    lista_monitoramento_perfil = lista_perfil_monitorados(cliente_usuario)
