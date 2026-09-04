"""Análises derivadas para o Farejador.

Somente leitura. Este módulo transforma o histórico JSON existente em métricas,
comportamentos e descobertas para a interface pública. Nenhum dado original é
alterado.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from math import isfinite
from typing import Any

CAMPOS_NUMERICOS = ("seguidores", "seguindo", "total_posts", "total_reels", "total_destaques")


def _num(value):
    try:
        n = float(value)
        return n if isfinite(n) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _snapshots(historico):
    out = []
    for item in historico or []:
        if not isinstance(item, dict):
            continue
        perfil = item.get("perfil") or {}
        ts = _dt(item.get("timestamp_capture"))
        if ts and isinstance(perfil, dict):
            out.append({"timestamp": ts, "perfil": perfil, "raw": item})
    return sorted(out, key=lambda x: x["timestamp"])


def _eventos(resumo):
    if not isinstance(resumo, dict):
        return []
    eventos = resumo.get("timeline") or resumo.get("timiline") or []
    return [x for x in eventos if isinstance(x, dict)]


def _field_series(snaps, field):
    return [(x["timestamp"], _num(x["perfil"].get(field))) for x in snaps if field in x["perfil"]]


def _period(points, days):
    if not points:
        return []
    end = points[-1][0]
    start = end - timedelta(days=days)
    chosen = [p for p in points if p[0] >= start]
    before = [p for p in points if p[0] < start]
    if before:
        chosen.insert(0, before[-1])
    return chosen


def _period_metric(points, days):
    chosen = _period(points, days)
    base = {"dias": days, "inicio": 0, "atual": 0, "variacao": 0, "percentual": 0, "por_dia": 0, "pontos": len(chosen), "suficiente": len(chosen) >= 2}
    if not chosen:
        return base
    base["inicio"], base["atual"] = chosen[0][1], chosen[-1][1]
    if len(chosen) < 2:
        return base
    delta = chosen[-1][1] - chosen[0][1]
    elapsed = max((chosen[-1][0] - chosen[0][0]).total_seconds() / 86400, 1 / 1440)
    base.update({"variacao": delta, "percentual": delta / chosen[0][1] * 100 if chosen[0][1] else 0, "por_dia": delta / elapsed})
    return base


def _trend(points):
    if len(points) < 4:
        return {"direcao": "insuficiente", "aceleracao_percentual": 0, "ritmo_atual": 0, "ritmo_anterior": 0, "suficiente": False}
    mid = len(points) // 2
    a, b = points[:mid], points[mid:]

    def rate(group):
        if len(group) < 2:
            return 0
        elapsed = max((group[-1][0] - group[0][0]).total_seconds() / 86400, 1 / 1440)
        return (group[-1][1] - group[0][1]) / elapsed

    old, new = rate(a), rate(b)
    acc = ((new - old) / abs(old) * 100) if old else (100 if new > 0 else 0)
    if old < 0 and new < 0:
        direction = "queda_acelerando" if new < old else "recuperando" if new > old else "estavel"
    else:
        direction = "acelerando" if acc > 10 else "desacelerando" if acc < -10 else "estavel"
    return {"direcao": direction, "aceleracao_percentual": acc, "ritmo_atual": new, "ritmo_anterior": old, "suficiente": True}


def _record(points):
    if len(points) < 2:
        return {"maior_ganho": 0, "maior_queda": 0, "melhor_periodo": None, "pior_periodo": None}
    deltas = []
    for a, b in zip(points, points[1:]):
        delta = b[1] - a[1]
        deltas.append({"variacao": delta, "timestamp": b[0].isoformat(), "anterior": a[1], "atual": b[1], "intervalo_segundos": max(0, int((b[0] - a[0]).total_seconds()))})
    best = max(deltas, key=lambda x: x["variacao"])
    worst = min(deltas, key=lambda x: x["variacao"])
    return {"maior_ganho": max(0, best["variacao"]), "maior_queda": min(0, worst["variacao"]), "melhor_periodo": best, "pior_periodo": worst}


def _bio_changes(snaps):
    changes = []
    previous = None
    for s in snaps:
        current = s["perfil"].get("biografia") or ""
        if previous is not None and current != previous:
            changes.append({"timestamp": s["timestamp"].isoformat(), "anterior": previous, "atual": current})
        previous = current
    return changes


def _sequence(points):
    """Detecta sequências consecutivas de ganho/queda sem inventar eventos."""
    if len(points) < 2:
        return {"maior_sequencia_queda": 0, "maior_sequencia_ganho": 0, "ultima_sequencia": {"tipo": "estavel", "tamanho": 0}}
    current = None
    size = 0
    best_gain = best_loss = 0
    last_type = "estavel"
    last_size = 0
    for a, b in zip(points, points[1:]):
        delta = b[1] - a[1]
        kind = "ganho" if delta > 0 else "queda" if delta < 0 else "estavel"
        if kind == current and kind != "estavel":
            size += 1
        else:
            current, size = kind, 1 if kind != "estavel" else 0
        if kind == "ganho":
            best_gain = max(best_gain, size)
        elif kind == "queda":
            best_loss = max(best_loss, size)
        if kind != "estavel":
            last_type, last_size = kind, size
    return {"maior_sequencia_queda": best_loss, "maior_sequencia_ganho": best_gain, "ultima_sequencia": {"tipo": last_type, "tamanho": last_size}}


def _oscillation(points):
    if len(points) < 3:
        return {"ocorrencias": 0, "ultimo": False, "padrao": None}
    occurrences = 0
    examples = []
    for a, b, c in zip(points, points[1:], points[2:]):
        d1, d2 = b[1] - a[1], c[1] - b[1]
        if d1 != 0 and d2 != 0 and ((d1 > 0 > d2) or (d1 < 0 < d2)):
            occurrences += 1
            if len(examples) < 4:
                examples.append({"timestamp": c[0].isoformat(), "antes": a[1], "meio": b[1], "depois": c[1]})
    return {"ocorrencias": occurrences, "ultimo": occurrences > 0, "exemplos": examples}


def _timing(snaps):
    intervals = []
    for a, b in zip(snaps, snaps[1:]):
        seconds = max(0, (b["timestamp"] - a["timestamp"]).total_seconds())
        intervals.append(seconds)
    if not intervals:
        return {"intervalos": 0, "min_segundos": None, "max_segundos": None, "medio_segundos": None, "maior_gap_segundos": None}
    return {"intervalos": len(intervals), "min_segundos": min(intervals), "max_segundos": max(intervals), "medio_segundos": sum(intervals) / len(intervals), "maior_gap_segundos": max(intervals)}


def _heatmap(eventos):
    counter = Counter()
    for e in eventos:
        ts = _dt(e.get("timestamp"))
        if ts:
            counter[ts.date().isoformat()] += 1
    return [{"data": d, "eventos": n} for d, n in sorted(counter.items())]


def _quality(snaps, followers):
    if not snaps:
        return {"nivel": "sem_dados", "rotulo": "Sem histórico", "capturas": 0, "dias_observados": 0, "densidade": 0}
    span = max((snaps[-1]["timestamp"] - snaps[0]["timestamp"]).total_seconds() / 86400, 0)
    density = len(snaps) / max(span, 1 / 24)
    if len(snaps) >= 20 and span >= 7:
        level, label = "forte", "Histórico forte"
    elif len(snaps) >= 6 and span >= 1:
        level, label = "bom", "Histórico consistente"
    elif len(snaps) >= 3:
        level, label = "inicial", "Histórico inicial"
    else:
        level, label = "baixo", "Poucos registros"
    return {"nivel": level, "rotulo": label, "capturas": len(snaps), "dias_observados": span, "densidade": density}


def _insights(perfil, periods, trend, records, eventos, bio_changes, sequence, oscillation, timing, quality, field_changes):
    insights = []
    p7 = periods.get("7", {})
    if p7.get("suficiente") and p7.get("variacao", 0) > 0:
        insights.append({"tipo": "crescimento", "icone": "🚀", "titulo": "O perfil ganhou seguidores", "texto": f"Foram {p7['variacao']:+.0f} seguidores na janela recente disponível."})
    if trend.get("direcao") == "acelerando":
        insights.append({"tipo": "aceleracao", "icone": "⚡", "titulo": "Crescimento em aceleração", "texto": f"O ritmo recente está {abs(trend['aceleracao_percentual']):.0f}% acima da parte anterior do histórico."})
    elif trend.get("direcao") == "desacelerando":
        insights.append({"tipo": "desaceleracao", "icone": "📉", "titulo": "O ritmo perdeu força", "texto": f"O ritmo recente caiu {abs(trend['aceleracao_percentual']):.0f}% em relação à parte anterior."})
    elif trend.get("direcao") == "queda_acelerando":
        insights.append({"tipo": "queda_acelerando", "icone": "🔻", "titulo": "A queda ganhou velocidade", "texto": "As perdas recentes estão mais intensas que na parte anterior do histórico."})
    elif trend.get("direcao") == "recuperando":
        insights.append({"tipo": "recuperando", "icone": "↗️", "titulo": "Sinal de recuperação", "texto": "O ritmo recente está menos negativo que na parte anterior."})
    if sequence.get("maior_sequencia_queda", 0) >= 2:
        insights.append({"tipo": "sequencia", "icone": "📉", "titulo": "Sequência de perdas detectada", "texto": f"Foram registradas {sequence['maior_sequencia_queda']} quedas consecutivas de seguidores."})
    if oscillation.get("ocorrencias", 0):
        insights.append({"tipo": "oscilacao", "icone": "🔄", "titulo": "Oscilação de seguidores detectada", "texto": f"O histórico mostra {oscillation['ocorrencias']} reversão(ões) consecutiva(s) no número de seguidores."})
    if field_changes.get("seguindo", 0) >= 2:
        insights.append({"tipo": "rede", "icone": "👥", "titulo": "Movimentação no seguindo", "texto": f"O número de seguindo mudou {field_changes['seguindo']} vezes entre as capturas."})
    if bio_changes:
        insights.append({"tipo": "bio", "icone": "✏️", "titulo": "Biografia alterada", "texto": f"Foram registradas {len(bio_changes)} alteração(ões) de biografia."})
    if timing.get("min_segundos") is not None and timing["min_segundos"] < 120:
        insights.append({"tipo": "frequencia", "icone": "⏱️", "titulo": "Capturas muito próximas", "texto": f"O menor intervalo entre capturas foi de {timing['min_segundos']:.0f} segundos."})
    if records.get("maior_ganho", 0) > 0:
        insights.append({"tipo": "recorde", "icone": "🏆", "titulo": "Maior ganho registrado", "texto": f"A maior variação positiva entre duas capturas foi de +{records['maior_ganho']:.0f} seguidores."})
    if records.get("maior_queda", 0) < 0:
        insights.append({"tipo": "queda", "icone": "🔻", "titulo": "Maior queda registrada", "texto": f"A maior queda entre duas capturas foi de {records['maior_queda']:.0f} seguidores."})
    if eventos:
        insights.append({"tipo": "atividade", "icone": "🔥", "titulo": "Histórico de atividade", "texto": f"O Farejador registrou {len(eventos)} evento(s) de alteração."})
    return insights[:8]


def analisar_perfil(historico, resumo=None):
    snaps = _snapshots(historico)
    eventos = _eventos(resumo or {})
    perfil = snaps[-1]["perfil"] if snaps else {}
    followers = _field_series(snaps, "seguidores")
    following = _field_series(snaps, "seguindo")
    periods = {str(d): _period_metric(followers, d) for d in (7, 30, 90)}
    periods["total"] = _period_metric(followers, 36500)
    trend = _trend(followers)
    records = _record(followers)
    bio_changes = _bio_changes(snaps)
    sequence = _sequence(followers)
    oscillation = _oscillation(followers)
    timing = _timing(snaps)
    quality = _quality(snaps, followers)

    field_changes = Counter()
    content_changes = []
    previous = None
    for s in snaps:
        if previous is not None:
            for field in CAMPOS_NUMERICOS:
                if field in s["perfil"] and field in previous:
                    if _num(s["perfil"].get(field)) != _num(previous.get(field)):
                        field_changes[field] += 1
            delta_content = sum(_num(s["perfil"].get(k)) - _num(previous.get(k)) for k in ("total_posts", "total_reels", "total_destaques"))
            if delta_content:
                content_changes.append({"timestamp": s["timestamp"].isoformat(), "variacao": delta_content})
        previous = s["perfil"]

    last = followers[-1][1] if followers else _num(perfil.get("seguidores"))
    if periods["7"]["suficiente"]:
        rate = periods["7"]["por_dia"]
    elif trend["suficiente"]:
        rate = trend["ritmo_atual"]
    else:
        rate = 0
    projection30 = last + rate * 30 if rate else None
    activity_raw = len(eventos) + max(len(snaps) - 1, 0) + sum(field_changes.values())
    activity_score = min(100, round(activity_raw * 4.0)) if activity_raw else 0
    event_types = Counter(e.get("categoria") or "outro" for e in eventos)

    insights = _insights(perfil, periods, trend, records, eventos, bio_changes, sequence, oscillation, timing, quality, field_changes)
    return {
        "capturas": len(snaps),
        "primeira_captura": snaps[0]["timestamp"].isoformat() if snaps else None,
        "ultima_captura": snaps[-1]["timestamp"].isoformat() if snaps else None,
        "periodos": periods,
        "tendencia": trend,
        "recordes": records,
        "projecao": {"dias": 30, "ritmo_diario": rate, "seguidores_estimados": projection30},
        "atividade": {"score": activity_score, "score_bruto": activity_raw, "eventos": len(eventos), "tipos": dict(event_types)},
        "qualidade": quality,
        "comportamento": {
            "sequencia": sequence,
            "oscilacao_seguidores": oscillation,
            "intervalos": timing,
            "mudancas_por_campo": dict(field_changes),
            "mudancas_conteudo": content_changes,
            "alteracoes_biografia": len(bio_changes),
        },
        "heatmap": _heatmap(eventos),
        "insights": insights,
        "serie_seguidores": [{"timestamp": ts.isoformat(), "valor": val} for ts, val in followers],
        "serie_seguindo": [{"timestamp": ts.isoformat(), "valor": val} for ts, val in following],
    }
