import ipaddress
import json
import os
import time
from typing import Optional
from urllib.parse import parse_qs, urlparse
from urllib.request import Request as UrlRequest, urlopen
from fastapi import HTTPException, Request
from backend.core.auth import get_user

_PROVEDOR_IP_CACHE = {}
_RATE_WINDOW_SECONDS = 60
_RATE_LIMIT = int(os.getenv("FAREJADOR_RATE_LIMIT", "30"))
_RATE_BUCKET = {}

def consultar_provedor_ip(ip: Optional[str]) -> dict:
    vazio = {"provedor": None, "organizacao": None, "asn": None, "pais": None, "cidade": None, "regiao": None, "timezone": None, "localizacao": None}
    if not ip:
        return vazio
    try:
        endereco = ipaddress.ip_address(ip)
        if endereco.is_private or endereco.is_loopback or endereco.is_reserved or endereco.is_unspecified:
            return vazio
    except ValueError:
        return vazio
    if ip in _PROVEDOR_IP_CACHE:
        return dict(_PROVEDOR_IP_CACHE[ip])
    resultado = dict(vazio)
    try:
        token = os.getenv("IPINFO_TOKEN", "").strip()
        url = f"https://ipinfo.io/{ip}/json"
        if token:
            url += f"?token={token}"
        req = UrlRequest(url, headers={"User-Agent": "Farejador/1.0"})
        with urlopen(req, timeout=5) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        org = str(dados.get("org") or "").strip()
        asn = None
        if org and org.split(" ", 1)[0].upper().startswith("AS"):
            asn = org.split(" ", 1)[0].upper()
        resultado.update({"provedor": org or None, "organizacao": org or None, "asn": asn, "pais": dados.get("country"), "cidade": dados.get("city"), "regiao": dados.get("region"), "timezone": dados.get("timezone"), "localizacao": dados.get("loc")})
    except Exception as erro:
        print(f"[ipinfo] Falha ao consultar {ip}: {erro}")
    _PROVEDOR_IP_CACHE[ip] = dict(resultado)
    return resultado

def dados_acesso_request(request: Request, dispositivo_cliente: Optional[dict] = None) -> dict:
    headers = request.headers
    dispositivo_cliente = dispositivo_cliente if isinstance(dispositivo_cliente, dict) else {}
    referer = headers.get("referer")
    user_agent = headers.get("user-agent")
    sec_ch_ua = headers.get("sec-ch-ua")
    sec_ch_platform = headers.get("sec-ch-ua-platform")
    sec_ch_mobile = headers.get("sec-ch-ua-mobile")
    host = request.client.host if request.client else None
    forwarded = headers.get("x-forwarded-for")
    cf_ip = headers.get("cf-connecting-ip")
    trust_proxy = os.getenv("FAREJADOR_TRUST_PROXY", "0") == "1"
    if trust_proxy and cf_ip:
        ip, origem_ip = cf_ip.strip(), "cloudflare"
    elif trust_proxy and forwarded:
        ip, origem_ip = forwarded.split(",")[0].strip(), "proxy_confiavel"
    else:
        ip, origem_ip = host, "direto"
    origem_site = None
    source = medium = campaign = term = content = None
    if referer:
        try:
            parsed = urlparse(referer)
            origem_site = parsed.netloc or None
            params = parse_qs(parsed.query)
            source = params.get("utm_source", [None])[0]
            medium = params.get("utm_medium", [None])[0]
            campaign = params.get("utm_campaign", [None])[0]
            term = params.get("utm_term", [None])[0]
            content = params.get("utm_content", [None])[0]
        except Exception:
            pass
    permissao_cliente = dispositivo_cliente.get("permissoes") or {}
    rede = consultar_provedor_ip(ip)
    return {"conexao": {"ip": ip, "tipo_ip": "IPv6" if ip and ":" in ip else "IPv4" if ip else None, "origem_ip": origem_ip, "rede": rede}, "origem": {"referer": referer, "site": origem_site, "campanha": {"source": source, "medium": medium, "campaign": campaign, "term": term, "content": content}}, "dispositivo": {"user_agent": user_agent, "navegador": (dispositivo_cliente.get("navegador") or {}).get("nome"), "versao_navegador": (dispositivo_cliente.get("navegador") or {}).get("versao"), "sistema": sec_ch_platform.strip('"') if sec_ch_platform else dispositivo_cliente.get("sistema"), "plataforma": (dispositivo_cliente.get("navegador") or {}).get("plataforma") or sec_ch_platform, "modelo": dispositivo_cliente.get("modelo"), "idioma": dispositivo_cliente.get("idioma") or headers.get("accept-language", "").split(",")[0].strip() or None, "sec_ch_ua": sec_ch_ua, "sec_ch_mobile": sec_ch_mobile, "timezone": dispositivo_cliente.get("timezone"), "tela": dispositivo_cliente.get("tela") or {"largura": None, "altura": None, "pixel_ratio": None}, "touch": dispositivo_cliente.get("touch")}, "permissoes": permissao_cliente}

def current_user(request: Request) -> Optional[str]:
    return get_user(request.cookies.get("farejador_token"))

def require_user(request: Request) -> str:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login necessário para esta ação.")
    return user

def rate_limit(request: Request, bucket="default"):
    now = time.monotonic()
    host = request.client.host if request.client else "unknown"
    key = f"{bucket}:{host}"
    recentes = [t for t in _RATE_BUCKET.get(key, []) if now - t < _RATE_WINDOW_SECONDS]
    if len(recentes) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Muitas solicitações. Aguarde um momento e tente novamente.")
    recentes.append(now)
    _RATE_BUCKET[key] = recentes

def cookie_kwargs():
    return {"httponly": True, "samesite": os.getenv("FAREJADOR_COOKIE_SAMESITE", "lax"), "secure": os.getenv("FAREJADOR_COOKIE_SECURE", "0") == "1", "max_age": 604800}
