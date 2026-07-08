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
    if not card_eligible(contact_id, layer):
        return None  # regra dura: Win/delete nunca; Lost só camada 3
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


# ---------- ELEGIBILIDADE (regra dura — adendo A7.4 / bug 2026-07-08) ----------
# Win NUNCA gera card e FECHA os abertos (+ confirma comissão) · dup usa a opp
# mais avançada · Lost só na Camada 3 · delete/spam nunca.
STAGE_RANK = {  # quanto maior, mais avançada no funil
    "Win": 100, "Appointment Booked": 90, "Quote Sent": 80, "Follow Up": 70,
    "Contact 3 (PM)": 65, "Contact 3 (AM)": 64, "Contact 2 (PM)": 63,
    "Contact 2 (AM)": 62, "Contact 1 (PM)": 61, "Contact 1 (AM)": 60,
    "New Lead": 50, "HOT LEADS": 45, "Great Cars": 40,
    "Lost": 10, "delete": 0,
}


def most_advanced_stage(contact_id):
    """Entre TODAS as opps do contato, o stage mais avançado (regra do dup)."""
    r = ghl.get("/opportunities/search",
                {"location_id": LOC, "contact_id": contact_id, "limit": 20})
    if r.status_code != 200:
        return None
    best, best_rank = None, -1
    for o in r.json().get("opportunities", []):
        st = rules.STAGE_BY_ID.get(o.get("pipelineStageId"))
        rk = STAGE_RANK.get(st, -1)
        # status won conta como Win mesmo se o stage não bater
        if o.get("status") == "won":
            st, rk = "Win", 100
        if rk > best_rank:
            best, best_rank = st, rk
    return best


def confirm_commissions(contact_id):
    """Opp virou Win → comissões 'potencial' do lead viram 'confirmado' (A4)."""
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    rows = _sb("PATCH",
               f"commissions?contact_id=eq.{contact_id}&status=eq.potencial",
               json={"status": "confirmado", "resolved_at": now}) or []
    return len(rows)


def eligibility_sync(verbose=False):
    """Expurga cards inelegíveis contra o stage REAL atual. Roda antes da geração."""
    purged = []
    for c in open_cards():
        st = most_advanced_stage(c["contact_id"])
        if st is None:
            continue
        if st == "Win":
            close_card(c["id"], "won — cliente fechou", {"stage": st})
            n_comm = confirm_commissions(c["contact_id"])
            purged.append((c["title"], "Win" + (f" (+{n_comm} comissão confirmada)" if n_comm else "")))
        elif st == "delete":
            close_card(c["id"], "inelegível — stage delete/spam", {"stage": st})
            purged.append((c["title"], "delete"))
        elif st == "Lost" and c["layer"] in (1, 2):
            close_card(c["id"], "movido p/ Lost — só Camada 3 (cold)", {"stage": st})
            purged.append((c["title"], "Lost em L1/L2"))
        if verbose and purged and purged[-1][0] == c["title"]:
            print(f"  expurgado: {c['title'][:50]} ({purged[-1][1]})")
    return purged


def card_eligible(contact_id, layer):
    """Guard usado na CRIAÇÃO de cards."""
    st = most_advanced_stage(contact_id)
    if st == "Win" or st == "delete":
        return False
    if st == "Lost" and layer in (1, 2):
        return False
    return True


def has_any_outbound(contact_id):
    """True se JÁ houve alguma tentativa de contato (call/SMS/email outbound)."""
    r = ghl.get("/conversations/search", {"locationId": LOC, "contactId": contact_id})
    if r.status_code != 200:
        return True  # em dúvida, não marca como intocado
    for cv in r.json().get("conversations", []):
        m = ghl.get(f"/conversations/{cv['id']}/messages")
        if m.status_code != 200:
            continue
        for msg in m.json().get("messages", {}).get("messages", []):
            if msg.get("direction") == "outbound" and msg.get("messageType") in (
                    "TYPE_CALL", "TYPE_SMS", "TYPE_EMAIL"):
                return True
    return False


def sync_first_touch():
    """REGRA DO RAFAEL (urgência 1): New Lead/HOT LEADS sem NENHUMA tentativa de
    contato → topo da Camada 2 (type first_touch; painel ordena acima dos demais)."""
    n = 0
    for stage in ("New Lead", "HOT LEADS"):
        r = ghl.get("/opportunities/search", {"location_id": LOC,
                                              "pipeline_id": rules.NEW_PIPELINE_ID,
                                              "pipeline_stage_id": rules.STAGES[stage],
                                              "limit": 100})
        if r.status_code != 200:
            continue
        for o in r.json().get("opportunities", []):
            if o.get("status") != "open":
                continue
            cid = o["contactId"]
            # já avaliado? (qualquer card first_touch, aberto ou fechado, = já visto)
            seen = _sb("GET", f"cards?type=eq.first_touch&contact_id=eq.{cid}&select=id&limit=1")
            if seen:
                continue
            if has_any_outbound(cid):
                # registra card fechado "já contatado" p/ não re-checar a cada ciclo
                _sb("POST", "cards", json={
                    "type": "first_touch", "layer": 2, "contact_id": cid,
                    "opportunity_id": o["id"], "title": f"(checked) {o.get('name')}",
                    "why": "contact already attempted", "status": "done",
                    "result": "já havia tentativa de contato", "closed_by": "auto",
                    "ghl_link": GHL_LINK.format(loc=LOC, cid=cid)})
                continue
            made = create_card(
                "first_touch", 2, cid,
                f"FIRST CONTACT — {o.get('name') or 'lead'} ({stage})",
                "Zero contact attempts so far. Untouched lead — always beats scheduled follow-ups.",
                {"passos": ["Call now — first voice wins the deal",
                            "No answer: voicemail + short intro SMS",
                            "Goal: qualify the car and book a visit"]},
                opportunity_id=o["id"], score=opp_score(o))
            if made:
                n += 1
                # substitui warm_call duplicado do mesmo contato
                _sb("PATCH", f"cards?status=eq.open&type=eq.warm_call&contact_id=eq.{cid}",
                    json={"status": "done", "result": "superseded por first_touch",
                          "closed_by": "auto"})
    return n


def flush_manual_logs():
    """Formulário 'Log call details' (urgência 2): entrada manual do painel →
    write-through no GHL (custom fields do contato + nota estruturada).
    Escrita INICIADA PELO USUÁRIO = autorizada (não é o cérebro decidindo)."""
    import requests as rq
    import config
    Hw = dict(config.ghl_headers(config.load()["GHL_API_TOKEN"]))
    Hw["Content-Type"] = "application/json"
    CF_VEH = {"make": "CiRd678lAFn854igklGR", "model": "LHwTnTb8TPz5BbJ0I2XV",
              "year": "C01IzbXlbESCLfhoHkrZ"}  # contact.vehicle_* (IDs reais, recon F0)
    rows = _sb("GET", "manual_logs?status=eq.pending&select=*") or []
    n = 0
    for row in rows:
        f = row["fields"]
        cid = row["contact_id"]
        try:
            cfs = [{"id": CF_VEH[k], "field_value": f[k]} for k in ("make", "model", "year")
                   if f.get(k)]
            if cfs:
                rq.put(f"{config.GHL_BASE_URL}/contacts/{cid}", headers=Hw,
                       json={"customFields": cfs}, timeout=30)
            nota = ["📋 CALL LOG (manual — painel)"]
            labels = [("outcome", "Outcome"), ("make", "Make"), ("model", "Model"),
                      ("year", "Year"), ("momento", "Car timing"), ("interest", "Interest"),
                      ("keep_or_trade", "Keep or trade"),
                      ("seen_other_quotes", "Seen other quotes"),
                      ("other_quotes_detail", "Other quotes detail"),
                      ("lost_reason", "Lost reason"),
                      ("prices", "Prices discussed"), ("hook", "Personal note"),
                      ("next_step", "Next step"), ("next_date", "When"), ("notes", "Notes")]
            for k, lab in labels:
                if f.get(k):
                    nota.append(f"{lab}: {f[k]}")
            nota.append(f"— logged by {row['logged_by']} via panel")
            rq.post(f"{config.GHL_BASE_URL}/contacts/{cid}/notes", headers=Hw,
                    json={"body": "\n".join(nota)}, timeout=30)
            _sb("PATCH", f"manual_logs?id=eq.{row['id']}",
                json={"status": "synced",
                      "synced_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")})
            n += 1
        except Exception as e:
            _sb("PATCH", f"manual_logs?id=eq.{row['id']}",
                json={"status": "error", "error": str(e)[:200]})
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


def sync_prices():
    """prices.json (repo) = fonte única → config.prices (painel lê do banco)."""
    import json as _json
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent.parent / "config" / "prices.json"
    if not p.exists():
        return 0
    import requests as rq
    rq.post(f"{SB_URL}/rest/v1/config",
            headers={**H, "Prefer": "resolution=merge-duplicates"},
            json={"key": "prices", "value": _json.load(open(p))}, timeout=15)
    return 1


def bonus_guard_check():
    """A5.1 — lembretes PROATIVOS a favor do bônus (horários em ET):
    10:15 appointment de amanhã não confirmado · 15:00 quote pendente do dia
    (16:30 vira card urgente) · lead 80+ chegando nas 24h órfão → card urgente."""
    from zoneinfo import ZoneInfo
    now_et = dt.datetime.now(ZoneInfo("America/New_York"))
    items = []
    oc = open_cards()
    hhmm = now_et.hour * 60 + now_et.minute

    appts = [c for c in oc if c["type"] == "confirm_appt"]
    quotes = [c for c in oc if c["type"] == "quote_followup"]
    if hhmm >= 615 and appts:   # 10:15
        items.append(f"{len(appts)} appointment(s) still unconfirmed — confirm before 11 AM")
    if hhmm >= 900 and quotes:  # 15:00
        items.append(f"{len(quotes)} quote(s) pending follow-up today")
    if hhmm >= 990:             # 16:30 → urgência de verdade
        for c in quotes:
            create_card("callback", 1, c["contact_id"],
                        f"⏰ BONUS GUARD — quote day closing: {c['title'].replace('Quote follow-up: ','')}",
                        "Quote pending and the day is ending. This protects your $50 bonus.",
                        {"passos": ["Call or text about the quote NOW",
                                    "Log the outcome after"]},
                        opportunity_id=c.get("opportunity_id"), score=c.get("score"))
    # 80+ órfão chegando nas 24h (card aberto há 20h+ sem fechamento)
    for c in oc:
        if (c.get("score") or 0) >= 80:
            age_h = (dt.datetime.now(dt.timezone.utc)
                     - dt.datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))
                     ).total_seconds() / 3600
            if age_h >= 20:
                items.append(f"Score-{c['score']} lead approaching the 24h orphan limit: {c['title'][:40]}")
                create_card("callback", 1, c["contact_id"],
                            f"🚨 80+ lead about to orphan: {c['title'][:44]}",
                            "High-score lead with no closure in ~24h — critical miss territory.",
                            {"passos": ["Contact NOW by any channel", "Log the attempt"]},
                            opportunity_id=c.get("opportunity_id"), score=c.get("score"))
    import requests as rq
    rq.post(f"{SB_URL}/rest/v1/config",
            headers={**H, "Prefer": "resolution=merge-duplicates"},
            json={"key": "bonus_guard",
                  "value": {"items": items, "at": now_et.isoformat()}}, timeout=15)
    return len(items)


def flush_outbox(dry_run=True):
    """Nice-to-talk aprovados no painel → SMS via GHL. SÓ com G2 ativo."""
    rows = _sb("GET", "outbox?status=eq.approved&select=*") or []
    if dry_run or not rows:
        return 0
    from brain import writer
    n = 0
    for row in rows:
        try:
            writer.send_sms(row["contact_id"], row["message"], gate="G2",
                            motivo=f"nice-to-talk aprovado por {row['approved_by']}")
            _sb("PATCH", f"outbox?id=eq.{row['id']}",
                json={"status": "sent",
                      "sent_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")})
            n += 1
        except Exception as e:
            _sb("PATCH", f"outbox?id=eq.{row['id']}",
                json={"status": "error", "error": str(e)[:200]})
    return n


def sync_all():
    el = len(eligibility_sync())
    ft = sync_first_touch()
    a = sync_appointment_confirmations()
    q = sync_quote_followups()
    w = sync_warm_calls()
    x = autoclose()
    r = reopen_snoozed()
    ml = flush_manual_logs()
    sync_prices()
    bg = bonus_guard_check()
    from brain import writer as _w
    ob = flush_outbox(dry_run=_w.DRY_RUN)
    return {"expurgados": el, "first_touch": ft, "appt": a, "quotes": q, "warm": w,
            "fechados": x, "reabertos": r, "manual_logs": ml, "guard": bg, "outbox": ob}
