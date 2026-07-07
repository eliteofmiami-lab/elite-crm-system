"""
Meta Conversions API (CAPI) — conexão direta servidor→Meta, sem depender de workflow GHL.

Funil de eventos (proposta aprovável pelo Rafael):
  QualifiedLead     → lead virou Great Cars OU score alto com engajamento
  AppointmentBooked → appointment criado
  Purchase          → opp Win (com valor da invoice quando existir)

Boas práticas implementadas:
  - event_id determinístico (dedup se o mesmo evento for reenviado)
  - user_data com email/telefone SHA-256 (exigência do Meta)
  - fbc/fbp/fbclid quando disponíveis no contato (casa o evento com o clique do anúncio)
  - action_source = "system_generated" (evento de CRM)

Config no .env:  META_PIXEL_ID=...   META_CAPI_TOKEN=...
Enquanto não existirem, send_event() apenas loga a intenção (dry-run natural).
"""
import hashlib
import json
import re
import time

import requests

import config

_cfg = config.load()
PIXEL_ID = __import__("os").environ.get("META_PIXEL_ID", "").strip()
TOKEN = __import__("os").environ.get("META_CAPI_TOKEN", "").strip()
GRAPH = "https://graph.facebook.com/v21.0"


def _h(v):
    """SHA-256 normalizado (padrão Meta)."""
    if not v:
        return None
    return hashlib.sha256(v.strip().lower().encode()).hexdigest()


def _norm_phone(p):
    if not p:
        return None
    return re.sub(r"\D", "", p)


def build_user_data(contact):
    """Monta user_data a partir do contato GHL (email/phone hasheados + ids de clique)."""
    ud = {}
    if contact.get("email"):
        ud["em"] = [_h(contact["email"])]
    if contact.get("phone"):
        ud["ph"] = [_h(_norm_phone(contact["phone"]))]
    if contact.get("firstName"):
        ud["fn"] = [_h(contact["firstName"])]
    if contact.get("lastName"):
        ud["ln"] = [_h(contact["lastName"])]
    # ids de clique do Meta, se o GHL tiver guardado (attribution)
    attrs = contact.get("attributions") or []
    for a in attrs:
        for k_src, k_dst in (("fbc", "fbc"), ("fbp", "fbp"), ("fbclid", None)):
            v = a.get(k_src)
            if v and k_dst:
                ud.setdefault(k_dst, v)
            elif v and k_src == "fbclid" and "fbc" not in ud:
                ud["fbc"] = f"fb.1.{int(time.time()*1000)}.{v}"
    return ud


def send_event(event_name, contact, opportunity_id, value=None, currency="USD",
               test_event_code=None):
    """Envia 1 evento CAPI. Sem PIXEL/TOKEN → loga intenção e retorna None."""
    payload = {
        "data": [{
            "event_name": event_name,
            "event_time": int(time.time()),
            "event_id": f"{event_name}:{opportunity_id}",  # dedup
            "action_source": "system_generated",
            "user_data": build_user_data(contact),
            **({"custom_data": {"value": value, "currency": currency}} if value else {}),
        }]
    }
    if test_event_code:
        payload["test_event_code"] = test_event_code

    entry = {"motivo": f"CAPI {event_name} opp={opportunity_id}",
             "url": f"{GRAPH}/{PIXEL_ID}/events", "payload_resumo": event_name}
    if not (PIXEL_ID and TOKEN):
        entry["status"] = "SEM_CONFIG (META_PIXEL_ID/META_CAPI_TOKEN ausentes)"
        _log(entry)
        return None
    r = requests.post(f"{GRAPH}/{PIXEL_ID}/events",
                      params={"access_token": TOKEN}, json=payload, timeout=30)
    entry["status"] = r.status_code
    _log(entry)
    if r.status_code >= 300:
        raise RuntimeError(f"CAPI falhou {r.status_code}: {r.text[:200]}")
    return r.json()


def _log(entry):
    import datetime as dt
    from pathlib import Path
    p = Path(config.PROJECT_ROOT) / "out" / "write_log.jsonl"
    entry["ts"] = dt.datetime.now(dt.timezone.utc).isoformat()
    entry["gate"] = "CAPI"
    with open(p, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
