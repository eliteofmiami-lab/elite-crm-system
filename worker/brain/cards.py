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
    hh = {**H, **kw.pop("headers_extra", {})}
    r = requests.request(method, f"{SB_URL}/rest/v1/{path}", headers=hh, timeout=20, **kw)
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
    # A6(3): advice mais recente do lead entra no "How to play it" (insight vira ação)
    try:
        adv = _sb("GET", ("analyses?select=payload,calls!inner(contact_id)"
                          f"&calls.contact_id=eq.{contact_id}"
                          "&order=created_at.desc&limit=1")) or []
        tip = adv and (adv[0]["payload"].get("advice_en") or "")
        if tip:
            how = dict(how or {})
            how["advice"] = tip
    except Exception:
        pass
    # A9: interesse vivo em TODO card + quote real quando o lead está em Quote Sent
    try:
        how = dict(how or {})
        intr = interest_for(contact_id)
        if intr:
            how["interest"] = intr
        if most_advanced_stage(contact_id) == "Quote Sent" and "quote" not in how:
            q = quote_facts(contact_id)
            how["quote"] = q
            how["passos"] = build_quote_passos(q)
    except Exception:
        pass
    # A12-b: exibição honesta — score do motor v3 (lead_scores) vence o CF estale do GHL
    s_max = s_badge = s_break = None
    try:
        ls = _sb("GET", f"lead_scores?contact_id=eq.{contact_id}"
                        "&select=known,max_possible,badge,breakdown") or []
        if ls:
            score = ls[0]["known"]
            s_max, s_badge, s_break = ls[0]["max_possible"], ls[0]["badge"], ls[0]["breakdown"]
    except Exception:
        pass
    return _sb("POST", "cards", json={
        "type": type_, "layer": layer, "contact_id": contact_id,
        "opportunity_id": opportunity_id, "title": title, "why": why,
        "how": how, "score": score, "score_max": s_max, "score_badge": s_badge,
        "score_breakdown": s_break, "due_at": due_at, "draft_message": draft,
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


CF_INTERESSE = "D5TgphY9HlZMoS8wcWj1"      # contact.elite_interesse_atual (A9)
CF_FORM_SERVICES = None  # preenchido no primeiro uso (what_services do formulário)


def interest_for(contact_id):
    """A9 — interesse vivo: elite_interesse_atual → fallback seed do formulário.
    Retorna {value, source, updated} ou {}."""
    global CF_FORM_SERVICES
    if CF_FORM_SERVICES is None:
        import json as _j
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent.parent / "out" / "cf_contact.json"
        CF_FORM_SERVICES = ""
        if p.exists():
            for f in _j.load(open(p))["customFields"]:
                if "what_services" in f["fieldKey"]:
                    CF_FORM_SERVICES = f["id"]
    r = ghl.get(f"/contacts/{contact_id}")
    if r.status_code != 200:
        return {}
    cfs = {f["id"]: f.get("value") for f in r.json().get("contact", {}).get("customFields", [])}
    if cfs.get(CF_INTERESSE):
        hist = _sb("GET", f"interest_history?contact_id=eq.{contact_id}"
                          "&order=created_at.desc&limit=1&select=created_at,source") or []
        return {"value": cfs[CF_INTERESSE], "source": (hist[0]["source"] if hist else "manual"),
                "updated": (hist[0]["created_at"][:10] if hist else None)}
    # trilha (call analisada / manual) — vale mesmo antes do CF ser gravado (pré-G2)
    hist = _sb("GET", f"interest_history?contact_id=eq.{contact_id}"
                      "&order=created_at.desc&limit=1&select=interest,source,created_at") or []
    if hist and hist[0].get("interest") and hist[0]["interest"] != "?":
        return {"value": hist[0]["interest"], "source": hist[0]["source"],
                "updated": hist[0]["created_at"][:10]}
    seed = cfs.get(CF_FORM_SERVICES)
    if seed:
        # registra o seed uma única vez na trilha
        prev = _sb("GET", f"interest_history?contact_id=eq.{contact_id}&select=id&limit=1")
        if not prev:
            _sb("POST", "interest_history", json={"contact_id": contact_id,
                "interest": str(seed)[:120], "source": "form_seed", "set_by": "seed"})
        return {"value": str(seed)[:120], "source": "form_seed", "updated": None}
    return {}


def build_quote_passos(q):
    """A9.4 — How to play it SEMPRE dos dados reais da quote. A10: fecha na VISITA."""
    if not (q.get("items") or q.get("link")):
        return ["Details pending analysis — open the conversation in GHL and read "
                "the quote before calling. Never quote from the generic table here.",
                "Close the VISIT: \"come by the shop — we lock the exact number here.\""]
    passos = []
    if q.get("items"):
        it = q["items"][0]
        passos.append(f"They were quoted: {it.get('servico') or it.get('service')} — "
                      f"{it.get('valor') or it.get('value')}. Anchor the talk on THIS number.")
    if q.get("sentiment"):
        passos.append(f"Last call sentiment: {q['sentiment']} — open accordingly.")
    if q.get("link"):
        passos.append("Reference the quote you sent (link on this card) and ask what they thought.")
    passos.append("Price pushback: smaller package or a call with Rafael — never a straight discount.")
    passos.append("End on the VISIT: \"come by, see it on your car — final number on the spot.\"")
    return passos


def quote_facts(contact_id):
    """spec 6.1 — a QUOTE REAL do cliente: link+data do SMS detectado,
    valores exatos + sentimento da call analisada (se existir)."""
    q = {}
    # link + data: varre o histórico atrás do SMS com go.urable.com
    r = ghl.get("/conversations/search", {"locationId": LOC, "contactId": contact_id})
    if r.status_code == 200:
        for cv in r.json().get("conversations", [])[:1]:
            m = ghl.get(f"/conversations/{cv['id']}/messages")
            if m.status_code != 200:
                continue
            for msg in m.json().get("messages", {}).get("messages", []):
                if msg.get("messageType") == "TYPE_SMS" and msg.get("direction") == "outbound":
                    mt = rules.URABLE_LINK.search(msg.get("body") or "")
                    if mt:
                        q["link"] = mt.group(0).rstrip(".,)")
                        q["sent_date"] = msg.get("dateAdded")
    # valores + sentimento: última análise do lead
    a = _sb("GET", ("analyses?select=payload,calls!inner(contact_id)"
                    f"&calls.contact_id=eq.{contact_id}"
                    "&order=created_at.desc&limit=1")) or []
    if a:
        pay = a[0]["payload"]
        if pay.get("precos_falados"):
            q["items"] = pay["precos_falados"]
        s = (pay.get("sentimento") or {})
        if s.get("geral"):
            q["sentiment"] = s["geral"][:60]
    return q


def sync_quote_followups():
    """Opps em Quote Sent → follow-up com A QUOTE REAL no card (spec 6.1)."""
    r = ghl.get("/opportunities/search", {"location_id": LOC,
                                          "pipeline_id": rules.NEW_PIPELINE_ID,
                                          "pipeline_stage_id": rules.STAGES["Quote Sent"],
                                          "limit": 50})
    n = 0
    if r.status_code == 200:
        for o in r.json().get("opportunities", []):
            q = quote_facts(o["contactId"])
            made = create_card(
                "quote_followup", 2, o["contactId"],
                f"Quote follow-up: {o.get('name') or 'lead'}",
                "Quote sent, no reply yet. This lead cools down every day.",
                {"passos": build_quote_passos(q), "quote": q},
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
                            "Any price you give is a STARTING price — never final by phone",
                            "Goal: book the VISIT — final number happens at the shop"]},
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
                            "Prices by phone = starting prices only",
                            "Goal: qualify the car and CLOSE THE VISIT"]},
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
            # A12-c: confirmação de visita no painel → tag visitou-loja (prova) no GHL
            # + flag persistente. Clique do usuário = escrita autorizada (write-through).
            if f.get("visit_confirmed"):
                rq.post(f"{config.GHL_BASE_URL}/contacts/{cid}/tags", headers=Hw,
                        json={"tags": ["visitou-loja"]}, timeout=30)
                rq.post(f"{SB_URL}/rest/v1/lead_flags?on_conflict=contact_id",
                        headers={**H, "Prefer": "resolution=merge-duplicates"},
                        json={"contact_id": cid, "visited_store": True,
                              "visit_probable": None,
                              "set_by": f"visita confirmada por {row['logged_by']}"},
                        timeout=15)
                if not any(k != "visit_confirmed" and v for k, v in f.items()):
                    _sb("PATCH", f"manual_logs?id=eq.{row['id']}",
                        json={"status": "synced",
                              "synced_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")})
                    n += 1
                    continue
            cfs = [{"id": CF_VEH[k], "field_value": f[k]} for k in ("make", "model", "year")
                   if f.get(k)]
            if f.get("service_interest"):
                cfs.append({"id": CF_INTERESSE, "field_value": f["service_interest"]})
            if cfs:
                rq.put(f"{config.GHL_BASE_URL}/contacts/{cid}", headers=Hw,
                       json={"customFields": cfs}, timeout=30)
            # A13: toggle "Offered $200 booking coupon" → registro em coupons
            if f.get("coupon_offered"):
                dupc = _sb("GET", f"coupons?contact_id=eq.{cid}&source=eq.manual"
                                  f"&created_at=gte.{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}"
                                  "&select=id&limit=1")
                if not dupc:
                    _sb("POST", "coupons", json={
                        "contact_id": cid, "source": "manual",
                        "contexto": f.get("coupon_context") or "offered via Log call details",
                        "offered_by": row["logged_by"]})
            nota = ["📋 CALL LOG (manual — painel)"]
            labels = [("outcome", "Outcome"), ("make", "Make"), ("model", "Model"),
                      ("year", "Year"), ("momento", "Car timing"), ("garaged", "Garaged or street"), ("arrival", "Car arrival"),
                      ("motivation", "Main motivation"), ("service_interest", "Service interest"), ("interest", "Interest"),
                      ("keep_or_trade", "Keep or trade"),
                      ("seen_other_quotes", "Seen other quotes"),
                      ("other_quotes_detail", "Other quotes detail"),
                      ("lost_reason", "Lost reason"),
                      ("prices", "Prices discussed"), ("hook", "Personal note"),
                      ("coupon_offered", "⚠️ $200 booking coupon OFFERED"),
                      ("next_step", "Next step"), ("next_date", "When"), ("notes", "Notes")]
            for k, lab in labels:
                if f.get(k):
                    nota.append(f"{lab}: {f[k]}")
            nota.append(f"— logged by {row['logged_by']} via panel")
            rq.post(f"{config.GHL_BASE_URL}/contacts/{cid}/notes", headers=Hw,
                    json={"body": "\n".join(nota)}, timeout=30)
            # A7.1c: Not interested + lost reason → opp vai pra Lost (ação do usuário)
            TERMINAL = ("Bought elsewhere", "Sold / returned the car", "Spam", "Wrong number")
            if f.get("lost_reason"):
                opp_r = ghl.get("/opportunities/search",
                                {"location_id": LOC, "contact_id": cid, "limit": 5})
                for o in (opp_r.json().get("opportunities", []) if opp_r.status_code == 200 else []):
                    if o.get("status") == "open":
                        rq.put(f"{config.GHL_BASE_URL}/opportunities/{o['id']}", headers=Hw,
                               json={"pipelineId": rules.NEW_PIPELINE_ID,
                                     "pipelineStageId": rules.STAGES["Lost"]}, timeout=30)
                        break
                if f["lost_reason"] in TERMINAL:
                    rq.post(f"{SB_URL}/rest/v1/lead_flags",
                            headers={**H, "Prefer": "resolution=merge-duplicates"},
                            json={"contact_id": cid, "cold_excluded": True,
                                  "spanish_only": False,
                                  "set_by": f"lost terminal: {f['lost_reason']}"}, timeout=15)
                # fecha cards abertos do lead (foi trabalhado e perdido)
                _sb("PATCH", f"cards?status=eq.open&contact_id=eq.{cid}",
                    json={"status": "done", "result": f"lost — {f['lost_reason']}",
                          "closed_by": "manual"})
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


def _analyses_for(contact_id, limit=5):
    return _sb("GET", ("analyses?select=payload,created_at,calls!inner(contact_id)"
                       f"&calls.contact_id=eq.{contact_id}"
                       f"&order=created_at.desc&limit={limit}")) or []


def _upsell_suggestions(profile):
    """A10.4 — sugestões por perfil (leasing/street/keep/chegando/interesse)."""
    out = []
    kt = (profile.get("keep_or_trade") or "").lower()
    if "leasing" in kt:
        out.append("Leasing → PPF against lease-return wear fees")
    if kt.startswith("keeping"):
        out.append("Keeping the car → Ceramic Gold (lifetime) pays off")
    if (profile.get("garaged") or "").lower() == "street":
        out.append("Parks on the street → full protection package")
    if (profile.get("momento") or "") in ("chegando", "recem_entregue", "Arriving soon",
                                          "Just delivered / brand new"):
        out.append("Car just arriving → urgency angle: install slots fill fast")
    il = (profile.get("interest") or "").lower()
    if "wrap" in il or "color" in il:
        out.append("Wrap/color change → show materials in hand; deposit locks material + date")
    return out


def build_visit_briefing():
    """A10.4 / spec 6.5 — 'Visitas de hoje e amanhã': dossiê por appointment na visão
    do Rafael. Gerado das análises + Log call details; atualiza a cada ciclo."""
    from zoneinfo import ZoneInfo
    from brain import pricing
    et = ZoneInfo("America/New_York")
    today0 = dt.datetime.now(et).replace(hour=0, minute=0, second=0, microsecond=0)
    end = today0 + dt.timedelta(days=2)
    visits = []
    for cal_name, cal_id in CALENDARS.items():
        r = ghl.get("/calendars/events", {"locationId": LOC, "calendarId": cal_id,
                                          "startTime": int(today0.timestamp() * 1000),
                                          "endTime": int(end.timestamp() * 1000)})
        if r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            if e.get("appointmentStatus") in ("cancelled", "invalid", "noshow"):
                continue
            cid = e.get("contactId")
            if not cid:
                continue
            ana = _analyses_for(cid)
            pay = ana[0]["payload"] if ana else {}
            v = pay.get("vehicle") or {}
            veh = " ".join(str(x) for x in (v.get("year"), v.get("make"), v.get("model")) if x)
            manual = (_sb("GET", f"manual_logs?contact_id=eq.{cid}"
                                 "&order=created_at.desc&limit=1&select=fields") or [{}])
            mf = manual[0].get("fields", {}) if manual else {}
            precos = []
            for a in ana:
                for it in (a["payload"].get("precos_falados") or []):
                    precos.append({"servico": it.get("servico"), "valor": it.get("valor"),
                                   "date": a["created_at"][:10]})
            intr = interest_for(cid)
            fl = _sb("GET", f"lead_flags?contact_id=eq.{cid}&select=visited_store") or []
            profile = {"keep_or_trade": mf.get("keep_or_trade"),
                       "garaged": mf.get("garaged"),
                       "momento": mf.get("momento") or (pay.get("momento") or {}).get("faixa"),
                       "interest": intr.get("value")}
            # A13: cupom prometido aparece OBRIGATORIAMENTE no briefing
            cps = _sb("GET", f"coupons?contact_id=eq.{cid}&status=eq.offered"
                             "&order=created_at.desc&limit=1&select=created_at,contexto") or []
            # A14: cliente repetido (Win anterior) — marcado; nunca gera card (card_eligible)
            repeat = most_advanced_stage(cid) == "Win"
            visits.append({
                "start": e.get("startTime"), "calendar": cal_name,
                "status": e.get("appointmentStatus"),
                "name": (e.get("title") or "").strip() or cid,
                "contact_id": cid,
                "vehicle": veh or None, "tier": pricing.tier_for(veh),
                "interest": intr or None,
                "precos_falados": precos,
                "sentiment": (pay.get("sentimento") or {}).get("geral") or None,
                "hooks": {k: v2 for k, v2 in {
                    "gancho": pay.get("gancho_pessoal") or mf.get("hook"),
                    "motivacao": pay.get("motivacao_principal") or mf.get("motivation"),
                    "garaged": mf.get("garaged"),
                    "keep_or_trade": mf.get("keep_or_trade")}.items() if v2},
                "quote": quote_facts(cid) or None,
                "visited_store": bool(fl and fl[0].get("visited_store")),
                "coupon": ({"date": cps[0]["created_at"][:10],
                            "contexto": cps[0].get("contexto")} if cps else None),
                "repeat_customer": repeat,
                "upsells": _upsell_suggestions(profile),
                "ghl_link": GHL_LINK.format(loc=LOC, cid=cid),
                "event_id": e.get("id"),
            })
    visits.sort(key=lambda x: str(x.get("start")))
    import requests as rq
    rq.post(f"{SB_URL}/rest/v1/config",
            headers={**H, "Prefer": "resolution=merge-duplicates"},
            json={"key": "visit_briefing",
                  "value": {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "visits": visits}}, timeout=15)
    return len(visits)


def build_appointments_board():
    """A14 / spec 6.6 — Appointments Board (visão do Rafael): hoje, amanhã e
    últimos 7 dias, com estado, cliente repetido e cupom prometido."""
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    today0 = dt.datetime.now(et).replace(hour=0, minute=0, second=0, microsecond=0)
    start = today0 - dt.timedelta(days=7)
    end = today0 + dt.timedelta(days=2)
    items = []
    for cal_name, cal_id in CALENDARS.items():
        r = ghl.get("/calendars/events", {"locationId": LOC, "calendarId": cal_id,
                                          "startTime": int(start.timestamp() * 1000),
                                          "endTime": int(end.timestamp() * 1000)})
        if r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            cid = e.get("contactId")
            if not cid:
                continue
            cps = _sb("GET", f"coupons?contact_id=eq.{cid}&status=eq.offered"
                             "&select=created_at&limit=1") or []
            items.append({
                "event_id": e.get("id"), "calendar": cal_name,
                "start": e.get("startTime"), "status": e.get("appointmentStatus"),
                "name": (e.get("title") or "").strip() or cid, "contact_id": cid,
                "repeat_customer": most_advanced_stage(cid) == "Win",
                "coupon": bool(cps),
                "ghl_link": GHL_LINK.format(loc=LOC, cid=cid),
            })
    items.sort(key=lambda x: str(x.get("start")), reverse=True)
    import requests as rq
    rq.post(f"{SB_URL}/rest/v1/config",
            headers={**H, "Prefer": "resolution=merge-duplicates"},
            json={"key": "appointments_board",
                  "value": {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "items": items}}, timeout=15)
    return len(items)


# A14: toque → status no GHL. Meta/CAPI configurável (meta_events_map).
_APPT_STATUS = {"confirmado": "confirmed", "showed": "showed", "noshow": "noshow"}
META_EVENTS_DEFAULT = {"showed": "QualifiedVisit", "comprou": "Purchase", "noshow": None}


def flush_appointment_actions():
    """Toques do Rafael no Appointments Board → write-through no GHL.
    Escrita INICIADA PELO USUÁRIO (toque) = autorizada; tudo vai pro write_log."""
    import requests as rq
    import config
    import json as _json
    from pathlib import Path
    Hw = dict(config.ghl_headers(config.load()["GHL_API_TOKEN"]))
    Hw["Content-Type"] = "application/json"
    log_path = Path(config.PROJECT_ROOT) / "out" / "write_log.jsonl"

    def wlog(method, url, payload, motivo, status):
        with open(log_path, "a") as fh:
            fh.write(_json.dumps({
                "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
                "gate": "user-initiated (Appointments Board)", "motivo": motivo,
                "method": method, "url": url, "payload": str(payload)[:300],
                "status": status, "dry_run": False}, ensure_ascii=False) + "\n")

    rows = _sb("GET", "appointment_actions?status=eq.pending&select=*") or []
    n = 0
    for row in rows:
        try:
            act, cid, eid = row["action"], row.get("contact_id"), row["event_id"]
            if act in _APPT_STATUS:
                url = f"{config.GHL_BASE_URL}/calendars/events/appointments/{eid}"
                pr = rq.put(url, headers=Hw,
                            json={"appointmentStatus": _APPT_STATUS[act]}, timeout=30)
                wlog("PUT", url, {"appointmentStatus": _APPT_STATUS[act]},
                     f"board: {act} por {row.get('acted_by')}", pr.status_code)
                if act == "showed" and cid:
                    _sb("POST", "lead_flags?on_conflict=contact_id",
                        headers_extra={"Prefer": "resolution=merge-duplicates"},
                        json={"contact_id": cid, "visited_store": True,
                              "visit_probable": None,
                              "set_by": f"board showed por {row.get('acted_by')}"})
            elif act == "comprou" and cid:
                # opp aberta do contato → Win + valor (fluxo manual do Rafael, atalho)
                opr = ghl.get("/opportunities/search",
                              {"location_id": LOC, "contact_id": cid, "limit": 10})
                opp = next((o for o in (opr.json().get("opportunities", [])
                                        if opr.status_code == 200 else [])
                            if o.get("status") == "open"), None)
                if opp:
                    url = f"{config.GHL_BASE_URL}/opportunities/{opp['id']}"
                    payload = {"pipelineId": rules.NEW_PIPELINE_ID,
                               "pipelineStageId": rules.STAGES["Win"], "status": "won"}
                    if row.get("value_usd") is not None:
                        payload["monetaryValue"] = float(row["value_usd"])
                    pr = rq.put(url, headers=Hw, json=payload, timeout=30)
                    wlog("PUT", url, payload,
                         f"board: Comprou (${row.get('value_usd')}) por {row.get('acted_by')}",
                         pr.status_code)
                # efeitos: fecha cards + confirma comissão + expira cupom aberto
                for c in _sb("GET", f"cards?status=eq.open&contact_id=eq.{cid}&select=id") or []:
                    close_card(c["id"], "won — comprou (board)", {"event_id": eid})
                confirm_commissions(cid)
                _sb("PATCH", f"coupons?contact_id=eq.{cid}&status=eq.offered",
                    json={"status": "converted_sale"})
            # CAPI conforme meta_events_map (teste-interno nunca reporta)
            ev_map = {**META_EVENTS_DEFAULT,
                      **(( _sb("GET", "config?key=eq.meta_events_map&select=value") or
                          [{}])[0].get("value") or {})}
            ev = ev_map.get(act)
            if ev and cid:
                cr = ghl.get(f"/contacts/{cid}")
                contact = cr.json().get("contact", {}) if cr.status_code == 200 else {}
                if "teste-interno" not in (contact.get("tags") or []):
                    try:
                        from brain import capi
                        capi.send_event(ev, contact, f"board-{eid}",
                                        value=(float(row["value_usd"])
                                               if act == "comprou" and row.get("value_usd") is not None
                                               else None))
                    except Exception as ce:
                        print(f"  [warn] CAPI board {ev}: {ce}")
            _sb("PATCH", f"appointment_actions?id=eq.{row['id']}",
                json={"status": "synced",
                      "synced_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")})
            n += 1
        except Exception as e:
            _sb("PATCH", f"appointment_actions?id=eq.{row['id']}",
                json={"status": "error", "error": str(e)[:200]})
    return n


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
    # A5.1: trilha dos lembretes (evita duplicar o mesmo lembrete no mesmo dia)
    for it in items:
        kind = ("appt_reminder" if "appointment" in it else
                "orphan80" if "orphan" in it else "quote_reminder")
        dup = _sb("GET", f"bonus_guard_events?kind=eq.{kind}"
                         f"&created_at=gte.{now_et.strftime('%Y-%m-%d')}&select=id&limit=1")
        if not dup:
            _sb("POST", "bonus_guard_events", json={"kind": kind, "detail": it})
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
    try:
        vb = build_visit_briefing()
    except Exception as e:
        vb = f"erro: {str(e)[:50]}"
    try:
        build_appointments_board()
        aa = flush_appointment_actions()
    except Exception as e:
        aa = f"erro: {str(e)[:50]}"
    from brain import writer as _w
    ob = flush_outbox(dry_run=_w.DRY_RUN)
    return {"expurgados": el, "first_touch": ft, "appt": a, "quotes": q, "warm": w,
            "fechados": x, "reabertos": r, "manual_logs": ml, "guard": bg,
            "briefing": vb, "board_actions": aa, "outbox": ob}
