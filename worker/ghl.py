"""Cliente GHL API v2 — SOMENTE LEITURA (GET + POST de busca; nunca escreve)."""
import time
import requests
import config

_cfg = config.load()
TOKEN = _cfg["GHL_API_TOKEN"]
LOCATION_ID = _cfg["GHL_LOCATION_ID"]
BASE = config.GHL_BASE_URL
H = config.ghl_headers(TOKEN)


def get(path, params=None, tries=4):
    """GET com retry/backoff p/ 429 E erros de rede (timeout, conexão).

    429 (Lote 1): distingue rajada de cota DIÁRIA. Se x-ratelimit-daily-remaining=0,
    a cota do dia acabou (só volta em ~1h) — devolve o 429 na hora, sem retry inútil,
    pra o worker abortar o ciclo e preservar o board. 429 de rajada → backoff curto.
    """
    url = path if path.startswith("http") else f"{BASE}{path}"
    last_exc = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=H, params=params, timeout=45)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_exc = e
            time.sleep(2 ** i)
            continue
        if r.status_code == 429:
            daily_left = (r.headers.get("x-ratelimit-daily-remaining") or "").strip()
            if daily_left == "0":
                return r  # cota diária zerada: retry não adianta, aborta já
            time.sleep(min(2 ** i, 8))  # 429 de rajada: espera curta e tenta de novo
            continue
        return r
    if last_exc:
        raise last_exc
    return r


def get_json(path, params=None):
    r = get(path, params)
    r.raise_for_status()
    return r.json()


def post(path, body=None, tries=4):
    """POST de BUSCA (ex.: /locations/{id}/tasks/search) — não escreve nada no GHL.
    Mesma proteção do get(): backoff em 429 de rajada, aborta se a cota diária zerou."""
    url = path if path.startswith("http") else f"{BASE}{path}"
    last_exc = None
    for i in range(tries):
        try:
            r = requests.post(url, headers=H, json=body or {}, timeout=45)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_exc = e
            time.sleep(2 ** i)
            continue
        if r.status_code == 429:
            daily_left = (r.headers.get("x-ratelimit-daily-remaining") or "").strip()
            if daily_left == "0":
                return r
            time.sleep(min(2 ** i, 8))
            continue
        return r
    if last_exc:
        raise last_exc
    return r
