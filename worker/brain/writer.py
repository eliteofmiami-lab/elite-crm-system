"""
Toda ESCRITA no GHL/Urable passa por aqui — e por mais nenhum lugar.

- DRY_RUN=True (padrão): nada é enviado; a intenção é registrada em out/write_log.jsonl
  com dry_run=true. Vira o material dos gates.
- DRY_RUN=False: só após gate aprovado (G0/G1/G2...). Cada escrita real também é logada.
- DELETE é proibido por construção: não existe método delete aqui.
"""
import json
import time
import datetime as dt
from pathlib import Path

import requests

import config

LOG_PATH = Path(config.PROJECT_ROOT) / "out" / "write_log.jsonl"
DRY_RUN = True  # segurança: só o runner muda isso, e só com gate aprovado

_cfg = config.load()
H = config.ghl_headers(_cfg["GHL_API_TOKEN"])
H["Content-Type"] = "application/json"
LOC = _cfg["GHL_LOCATION_ID"]


def _log(entry):
    entry["ts"] = dt.datetime.now(dt.timezone.utc).isoformat()
    entry["dry_run"] = DRY_RUN
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _payload_resumo(payload, limit=400):
    s = json.dumps(payload, ensure_ascii=False, default=str)
    return s[:limit]


def _send(method, url, payload, gate, motivo):
    entry = {"gate": gate, "motivo": motivo, "method": method, "url": url,
             "payload": _payload_resumo(payload)}
    if DRY_RUN:
        entry["status"] = "DRY_RUN"
        _log(entry)
        return {"dry_run": True}
    for i in range(3):
        r = requests.request(method, url, headers=H, json=payload, timeout=30)
        if r.status_code == 429:
            time.sleep(2 ** i)
            continue
        break
    entry["status"] = r.status_code
    try:
        body = r.json()
    except Exception:
        body = {"text": r.text[:200]}
    entry["response_id"] = (body.get("id") or (body.get("opportunity") or {}).get("id")
                            or (body.get("contact") or {}).get("id"))
    _log(entry)
    if r.status_code >= 300:
        raise RuntimeError(f"write falhou {r.status_code}: {r.text[:200]} ({motivo})")
    return body


BASE = config.GHL_BASE_URL


# ---------- operações permitidas (NUNCA delete) ----------
def update_opportunity(opp_id, fields, gate, motivo):
    """PUT /opportunities/{id} — stage, customFields, etc."""
    return _send("PUT", f"{BASE}/opportunities/{opp_id}", fields, gate, motivo)


def update_contact(contact_id, fields, gate, motivo):
    return _send("PUT", f"{BASE}/contacts/{contact_id}", fields, gate, motivo)


def add_tag(contact_id, tags, gate, motivo):
    """POST /contacts/{id}/tags — adiciona (não remove) tags."""
    return _send("POST", f"{BASE}/contacts/{contact_id}/tags",
                 {"tags": tags if isinstance(tags, list) else [tags]}, gate, motivo)


def create_note(contact_id, body, gate, motivo, user_id=None):
    p = {"body": body}
    if user_id:
        p["userId"] = user_id
    return _send("POST", f"{BASE}/contacts/{contact_id}/notes", p, gate, motivo)


def create_task(contact_id, title, body, due_iso, assigned_to, gate, motivo):
    return _send("POST", f"{BASE}/contacts/{contact_id}/tasks",
                 {"title": title, "body": body, "dueDate": due_iso,
                  "assignedTo": assigned_to, "completed": False}, gate, motivo)


def send_sms(contact_id, message, gate, motivo):
    return _send("POST", f"{BASE}/conversations/messages",
                 {"type": "SMS", "contactId": contact_id, "message": message}, gate, motivo)


def create_custom_field(payload, gate, motivo):
    return _send("POST", f"{BASE}/locations/{LOC}/customFields", payload, gate, motivo)


# ---------- Urable (Customer + Item apenas; sem delete) ----------
def urable(method, path, payload, gate, motivo):
    url = f"https://app.urable.com/api{path}"
    entry = {"gate": gate, "motivo": motivo, "method": method, "url": url,
             "payload": _payload_resumo(payload)}
    if DRY_RUN:
        entry["status"] = "DRY_RUN"
        _log(entry)
        return {"dry_run": True}
    hh = {"Authorization": f"Bearer {_cfg['URABLE_API_KEY']}",
          "Content-Type": "application/json"}
    r = requests.request(method, url, headers=hh, json=payload, timeout=30)
    entry["status"] = r.status_code
    _log(entry)
    if r.status_code >= 300:
        raise RuntimeError(f"urable write falhou {r.status_code}: {r.text[:200]}")
    return r.json()
