"""
Carregamento e validação de credenciais para a Fase 0 (recon + backfill).

REGRA DE SEGURANÇA: este módulo carrega segredos do .env mas NUNCA os imprime.
Se faltar credencial, ele para com uma mensagem clara pedindo para preencher o .env
— sem jamais pedir as chaves pelo chat/log.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # raiz do repo (worker/ está um nível abaixo)
ENV_PATH = PROJECT_ROOT / ".env"

# Endpoints base oficiais do GHL API v2.
GHL_BASE_URL = "https://services.leadconnectorhq.com"
GHL_API_VERSION = "2021-07-28"


def _require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        sys.exit(
            f"[BLOQUEADO] Variável '{name}' ausente ou vazia no .env.\n"
            f"Preencha {ENV_PATH} (use .env.example como modelo) e rode de novo.\n"
            f"NUNCA cole a chave no chat — apenas edite o arquivo .env local."
        )
    return val


def load():
    if not ENV_PATH.exists():
        sys.exit(
            f"[BLOQUEADO] Arquivo .env não encontrado em {ENV_PATH}.\n"
            f"Copie .env.example para .env e preencha GHL_API_TOKEN, GHL_LOCATION_ID, "
            f"URABLE_API_KEY e ANTHROPIC_API_KEY."
        )
    load_dotenv(ENV_PATH)
    return {
        "GHL_API_TOKEN": _require("GHL_API_TOKEN"),
        "GHL_LOCATION_ID": _require("GHL_LOCATION_ID"),
        # Opcionais — carregados sem exigir; cada consumidor valida o que precisa.
        "URABLE_API_KEY": os.environ.get("URABLE_API_KEY", "").strip(),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "").strip(),
        "DEEPGRAM_API_KEY": os.environ.get("DEEPGRAM_API_KEY", "").strip(),
        "SUPABASE_URL": os.environ.get("SUPABASE_URL", "").strip(),
        "SUPABASE_ANON_KEY": os.environ.get("SUPABASE_ANON_KEY", "").strip(),
        "SUPABASE_SERVICE_ROLE_KEY": os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
    }


def ghl_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Version": GHL_API_VERSION,
        "Accept": "application/json",
    }
