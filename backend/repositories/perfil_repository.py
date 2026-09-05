from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import PerfilSalvo, Monitoramento, HistoricoPerfil
from backend.database.sync import sincronizar_historico, sincronizar_perfil
from backend.services.common import PUBLIC_CLIENTE, data_root, load_json
from toolFarejador.perfis.toolRemoverPerfil import carregar_dados_perfil_salvos
from toolFarejador.monitoramento.toolAtivarMonitoramento import lista_perfil_monitorados


def _db_profiles(cliente_usuario):
    with Session(get_engine()) as session:
        registros = session.scalars(
            select(PerfilSalvo)
            .where(PerfilSalvo.cliente_usuario == cliente_usuario)
            .order_by(PerfilSalvo.id)
        ).all()
        return [
            {
                "perfil": r.perfil or {},
                "monitoramento": {"monitorando": False, "sleep": 10},
                "caminho_historico_salvo": r.caminho_historico_salvo,
            }
            for r in registros
        ]


def _db_monitoring(cliente_usuario):
    with Session(get_engine()) as session:
        registros = session.scalars(
            select(Monitoramento).where(Monitoramento.cliente_usuario == cliente_usuario)
        ).all()
        return {str(r.instagram_pk): (r.dados or {"pk": r.instagram_pk, "username": r.username, "monitorando": r.monitorando, "sleep": r.sleep}) for r in registros}


def get_saved_profiles(cliente_usuario):
    try:
        items = _db_profiles(cliente_usuario)
        monitoring = _db_monitoring(cliente_usuario)
        if items:
            for item in items:
                pk = str(item.get("perfil", {}).get("pk"))
                item["monitoramento"] = monitoring.get(pk, {"monitorando": False, "sleep": 10})
            return items
    except Exception as erro:
        print(f"[postgres] Falha ao consultar perfis salvos: {erro}")

    if cliente_usuario == PUBLIC_CLIENTE:
        pasta = data_root(cliente_usuario) / "perfil_salvos"
        pasta_monitoramento = data_root(cliente_usuario) / "monitoramento"
        items = []
        if pasta.exists():
            for arquivo in sorted(pasta.glob("*.json")):
                dados = load_json(arquivo, None)
                if isinstance(dados, dict):
                    items.append(dados)
        monitoring = {}
        if pasta_monitoramento.exists():
            for arquivo in pasta_monitoramento.glob("*.json"):
                dados = load_json(arquivo, None)
                if isinstance(dados, dict):
                    monitoring[str(dados.get("pk"))] = dados
        return [
            {
                "perfil": item.get("perfil", {}),
                "monitoramento": monitoring.get(str(item.get("perfil", {}).get("pk")), {"monitorando": False, "sleep": 10}),
                "caminho_historico_salvo": item.get("caminho_historico_salvo"),
            }
            for item in items
        ]

    result = carregar_dados_perfil_salvos(cliente_usuario)
    monitoring = {str(x.get("pk")): x for x in lista_perfil_monitorados(cliente_usuario)}
    return [
        {
            "perfil": item.get("perfil", {}),
            "monitoramento": monitoring.get(str(item.get("perfil", {}).get("pk")), {"monitorando": False, "sleep": 10}),
            "caminho_historico_salvo": item.get("caminho_historico_salvo"),
        }
        for item in result.get("dados_perfil", [])
    ]


def get_profile_by_pk(cliente_usuario, pk):
    try:
        with Session(get_engine()) as session:
            registro = session.scalar(select(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente_usuario, PerfilSalvo.instagram_pk == str(pk)))
            if registro:
                return {"perfil": registro.perfil or {}, "caminho_historico_salvo": registro.caminho_historico_salvo}
    except Exception as erro:
        print(f"[postgres] Falha ao consultar perfil: {erro}")

    legado = load_json(data_root(cliente_usuario) / "perfil_salvos" / f"{pk}.json", {})
    if isinstance(legado, dict) and isinstance(legado.get("perfil"), dict):
        try:
            sincronizar_perfil(cliente_usuario, legado)
        except Exception as erro:
            print(f"[postgres] Falha ao sincronizar perfil legado: {erro}")
    return legado


def get_history(cliente_usuario, pk):
    try:
        with Session(get_engine()) as session:
            registros = session.scalars(
                select(HistoricoPerfil)
                .where(HistoricoPerfil.cliente_usuario == cliente_usuario, HistoricoPerfil.instagram_pk == str(pk))
                .order_by(HistoricoPerfil.timestamp_capture, HistoricoPerfil.id)
            ).all()
            if registros:
                return [
                    {
                        "perfil": r.perfil or {},
                        **(r.dados or {}),
                        "timestamp_capture": r.timestamp_capture.isoformat() if r.timestamp_capture else None,
                    }
                    for r in registros
                ]
    except Exception as erro:
        print(f"[postgres] Falha ao consultar histórico: {erro}")

    # Compatibilidade temporária: se o histórico ainda não estiver no banco,
    # lê o JSON legado e replica seus snapshots para o PostgreSQL.
    historico = load_json(data_root(cliente_usuario) / "historico" / f"{pk}.json", [])
    if not isinstance(historico, list):
        return []
    try:
        for item in historico:
            if isinstance(item, dict):
                sincronizar_historico(cliente_usuario, item)
    except Exception as erro:
        print(f"[postgres] Falha ao sincronizar histórico legado: {erro}")
    return historico
