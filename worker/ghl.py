"""Cliente GHL API v2 — SOMENTE LEITURA (apenas GET) para a Fase 0."""
import time
import requests
import config

_cfg = config.load()
TOKEN = _cfg["GHL_API_TOKEN"]
LOCATION_ID = _cfg["GHL_LOCATION_ID"]
BASE = config.GHL_BASE_URL
H = config.ghl_headers(TOKEN)


def get(path, params=None, tries=4):
    """GET com retry/backoff p/ 429 E erros de rede (timeout, conexão)."""
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
            time.sleep(2 ** i)
            continue
        return r
    if last_exc:
        raise last_exc
    return r


def get_json(path, params=None):
    r = get(path, params)
    r.raise_for_status()
    return r.json()
