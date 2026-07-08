"""
Fila do painel (M3): o cérebro cria/fecha cards na tabela `cards` do Supabase.

Camadas:
  1 = interrupções (ligação perdida, lead respondeu)  → topo, vermelho
  2 = dia planejado (confirmar appointments, quotes pendentes)
  3 = cold/warm calls ranqueadas por score

Fechamento por evidência: call/SMS outbound pro contato depois da criação do card.
"""
import os
import json
import datetime as dt

import requests

import ghl
from brain import rules

SB_URL = os.environ.get("SUPABASE_URL", "").strip()
SB_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
H = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}",
     "Content-Type": "application/json", "Prefer": "return=representation"}
LOC = ghl.LOCATION_ID
GHL_LINK = "https://app.gohighlevel.com/v2/location/{loc}/contacts/detail/{cid}"

CALENDARS = {  # os 3 calendários reais de booking (recon)
    "Booking Request": "iktsAzvv6tKgKOyPrxWJ",
    "ELITE BOCA RATON": "7rf1T22XmV09LZsBXPVR",
    "Ceramic Pro Silver Package": "q3WUy31NULnQsIi76E3O",
}


def _sb(method, path, **kw):
    if not SB_URL:
        return None
    r = requests.request(method, f"{SB_URL}/rest/v1/{path}", headers=H, timeout=20, **kw)
    if r.status_code >= 300:
        print(f"  [warn] supabase {method} {path}: {r.status_code} {r.text[:120]}")
        return None
    try:
        return r.json()
    except Exception:
        return []


def open_cards():
    return _sb("GET", "cards?status=eq.open&select=*") or []


def create_card(type_, layer, contact_id, title, why, how, opportunity_id=None,
                score=None, due_at=None, draft=None):
    existing = _sb("GET", f"cards?status=eq.open&type=eq.{type_}&contact_id=eq.{contact_id}&select=id")
    if existing:
        return None  # já tem card aberto igual
    return _sb("POST", "cards", json={
        "type": type_, "layer": layer, "contact_id": contact_id,
        "opportunity_id": opportunity_id, "title": title, "why": why,
        "how": how, "score": score, "due_at": due_at, "draft_message": draft,
        "ghl_link": GHL_LINK.format(loc=LOC, cid=contact_id),
    })


def close_card(card_id, result, evidence=None, closed_by="auto"):
    return _sb("PATCH", f"cards?id=eq.{card_id}", json={
        "status": "done", "result": result, "closed_by": closed_by,
        "evidence": evidence or {}, "closed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })


# ---------- geração ----------
def sync_appointment_confirmations():
    """Appointments das próximas 48h → card de confirmação (camada 2)."""
    now = dt.datetime.now(dt.timezone.utc)
    start = int(now.timestamp() * 1000)
    end = int((now + dt.timedelta(hours=48)).timestamp() * 1000)
    n = 0
    for cal_name, cal_id in CALENDARS.items():
        r = ghl.get("/calendars/events", {"locationId": LOC, "calendarId": cal_id,
                                          "startTime": start, "endTime": end})
        if r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            if e.get("appointmentStatus") not in ("new", "booked", None):
                continue  # já confirmado/cancelado
            cid = e.get("contactId")
            if not cid:
                continue
            made = create_card(
                "confirm_appt", 2, cid,
                f"Confirm appointment: {e.get('title') or 'booking'}",
                f"Scheduled for {e.get('startTime')} ({cal_name}) and still unconfirmed.",
                {"passos": ["Send a confirmation SMS or call",
                            "No reply by 11 AM: call directly",
                            "A no-show costs a slot — confirming prevents it"]},
                due_at=None)
            n += made is not None
    return n


SCORE_CF_ID = "OKX1hfCHkn2FWZud9lj1"  # opportunity.elite_score


def opp_score(o):
    for cf in o.get("customFields", []):
        if cf.get("id") == SCORE_CF_ID:
            try:
                return int(cf.get("fieldValue") or 0) or None
            except Exception:
                return None
    return None


def sync_quote_followups():
    """Opps em Quote Sent → follow-up da quote (camada 2)."""
    r = ghl.get("/opportunities/search", {"location_id": LOC,
                                          "pipeline_id": rules.NEW_PIPELINE_ID,
                                          "pipeline_stage_id": rules.STAGES["Quote Sent"],
                                          "limit": 50})
    n = 0
    if r.status_code == 200:
        for o in r.json().get("opportunities", []):
            made = create_card(
                "quote_followup", 2, o["contactId"],
                f"Quote follow-up: {o.get('name') or 'lead'}",
                "Quote sent, no reply yet. This lead cools down every day.",
                {"passos": ["Call and ask what they thought of the quote",
                            "If price pushback: offer a smaller package (never a straight discount)",
                            "Mention this week's schedule availability"]},
                opportunity_id=o["id"], score=opp_score(o))
            n += made is not None
    return n


def sync_warm_calls(limit=25):
    """Camada 3: HOT LEADS + New Lead por score (dos custom fields gravados no G0-B)."""
    n = 0
    for stage in ("HOT LEADS", "New Lead", "Great Cars"):
        r = ghl.get("/opportunities/search", {"location_id": LOC,
                                              "pipeline_id": rules.NEW_PIPELINE_ID,
                                              "pipeline_stage_id": rules.STAGES[stage],
                                              "limit": 100})
        if r.status_code != 200:
            continue
        opps = r.json().get("opportunities", [])
        def sc(o):
            for cf in o.get("customFields", []):
                if cf.get("id") == "OKX1hfCHkn2FWZud9lj1":
                    try:
                        return int(cf.get("fieldValue") or 0)
                    except Exception:
                        return 0
            return 0
        for o in sorted(opps, key=sc, reverse=True)[:limit]:
            made = create_card(
                "warm_call", 3, o["contactId"],
                f"Call {o.get('name') or 'lead'} ({stage})",
                f"Score {sc(o) or '?'} — {stage} lead; the sooner you call, the better the odds.",
                {"passos": ["Open the contact in GHL and read the notes",
                            "Call; if no answer, send a short personal SMS",
                            "Goal: book a visit or send a quote"]},
                opportunity_id=o["id"], score=sc(o) or None)
            n += made is not None
    return n


def reopen_snoozed():
    """Snoozed com due_at vencido volta pra fila (5 min antes já reabre)."""
    now = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    rows = _sb("PATCH", f"cards?status=eq.snoozed&due_at=lt.{now}",
               json={"status": "open"}) or []
    return len(rows)


# ---------- fechamento por evidência ----------
def autoclose():
    """Fecha cards quando há call/SMS outbound pro contato após a criação do card."""
    n = 0
    for c in open_cards():
        created = dt.datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))
        r = ghl.get("/conversations/search", {"locationId": LOC, "contactId": c["contact_id"]})
        if r.status_code != 200:
            continue
        convs = r.json().get("conversations", [])
        closed = False
        for cv in convs[:1]:
            m = ghl.get(f"/conversations/{cv['id']}/messages")
            if m.status_code != 200:
                continue
            for msg in m.json().get("messages", {}).get("messages", []):
                ts = msg.get("dateAdded")
                if not ts:
                    continue
                when = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if when <= created or msg.get("direction") != "outbound":
                    continue
                if msg.get("messageType") in ("TYPE_CALL", "TYPE_SMS"):
                    kind = "call made" if msg["messageType"] == "TYPE_CALL" else "SMS sent"
                    close_card(c["id"], kind, {"message_id": msg.get("id"), "at": ts})
                    closed = True
                    n += 1
                    break
            if closed:
                break
    return n


def sync_all():
    a = sync_appointment_confirmations()
    q = sync_quote_followups()
    w = sync_warm_calls()
    x = autoclose()
    r = reopen_snoozed()
    return {"appt": a, "quotes": q, "warm": w, "fechados": x, "reabertos": r}
