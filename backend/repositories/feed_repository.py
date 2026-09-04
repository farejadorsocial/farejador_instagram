from backend.services.common import data_root, load_json, limitar


def feed(cliente_usuario):
    data = load_json(data_root(cliente_usuario) / "feed" / "feed.json", [])
    ordenado = sorted(
        data,
        key=lambda x: x.get("timestamp_capture", ""),
        reverse=True,
    )
    return limitar(cliente_usuario, "feed", ordenado, 10)
