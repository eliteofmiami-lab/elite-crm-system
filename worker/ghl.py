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
    """GET com retry/backoff simples. Levanta em erro != 2xx (exceto passa o body)."""
    url = path if path.startswith("http") else f"{BASE}{path}"
    for i in range(tries):
        r = requests.get(url, headers=H, params=params, timeout=30)
        if r.status_code == 429:
            wait = 2 ** i
            time.sleep(wait)
            continue
        return r
    return r


def get_json(path, params=None):
    r = get(path, params)
    r.raise_for_status()
    return r.json()
