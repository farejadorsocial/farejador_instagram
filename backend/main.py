import json
import os
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.core.config import BASE, FRONTEND
from backend.core.auth import preparar_usuarios
from backend.core.security import dados_acesso_request
from backend.api.auth import router as auth_router
from backend.api.dashboard import router as dashboard_router
from backend.api.feed import router as feed_router
from backend.api.perfis import router as perfis_router
from backend.api.comparador import router as comparador_router
from backend.api.historico import router as historico_router
from backend.api.exploracao import router as exploracao_router
from backend.api.monitoramento import router as monitoramento_router
from toolFarejador.monitoramento.toolMonitoramentoSistema import monitoramento_perfis_tempo_real, solicitar_parada_monitoramento
from toolFarejador.sistema.toolSistemaPublico import sincronizar_dados_publicos
from toolFarejador.usuarios.toolDadosUsuario import migrar_dados_legados

app = FastAPI(title="Farejador Instagram", version="1.8.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("FAREJADOR_CORS_ORIGINS", "").split(",") if x.strip()] or ["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

for router in (auth_router, dashboard_router, feed_router, perfis_router, comparador_router, historico_router, exploracao_router, monitoramento_router):
    app.include_router(router)

from backend.core.visitor import registrar_visitante

_monitor_thread = None

@app.get("/")
def index(): return FileResponse(FRONTEND / "index.html")

@app.get("/perfil/{username}")
def public_profile_page(username: str): return FileResponse(FRONTEND / "index.html")

@app.get("/comparar")
def compare_page(): return FileResponse(FRONTEND / "index.html")

@app.get("/explorar")
def explore_page(): return FileResponse(FRONTEND / "index.html")

def iniciar_monitoramento_sistema():
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive(): return
    _monitor_thread = threading.Thread(target=monitoramento_perfis_tempo_real, daemon=True, name="monitoramento-sistema")
    _monitor_thread.start()

@app.on_event("startup")
def startup_event():
    try: preparar_usuarios()
    except Exception as erro: print(f"[usuarios] Falha na preparação: {erro}")
    try: migrar_dados_legados()
    except Exception as erro: print(f"[dados] Falha na migração compatível: {erro}")
    try: sincronizar_dados_publicos()
    except Exception as erro: print(f"[publico] Falha na sincronização inicial: {erro}")
    if os.getenv("FAREJADOR_DISABLE_MONITOR", "0") != "1": iniciar_monitoramento_sistema()

@app.on_event("shutdown")
def shutdown_event():
    solicitar_parada_monitoramento()
    if _monitor_thread and _monitor_thread.is_alive(): _monitor_thread.join(timeout=2)
