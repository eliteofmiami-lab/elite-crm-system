"""
A12-a: motor de score v3 — a CAUSA RAIZ do bug da K WASHINGTON era o cálculo ler só
opp_name + mensagens da 1ª conversa, esquecendo veículo (CFs/análise), a análise SALVA
no Supabase (só a do ciclo contava), a quote enviada e a visita à loja.

Este módulo junta TODAS as fontes, com precedência documentada, e persiste em
`lead_scores` (Supabase = livre). A escrita do CF no GHL continua gated (G2/G-SCORE-FIX).

Fontes por componente:
  Carro       manual (Log call VENCE) > CFs do contato > análise de call > nome da opp
  Momento     manual > transcrição > '?'
  Engajamento mensagens de TODAS as conversas (não só a 1ª)
  Intenção    visita à loja (prova) > transcrição > quote enviada > proxy how_soon
Selo: call-verified quando Momento/Intenção têm evidência real; senão partial.
Visita à loja (convenção Rafael 2026-07-07): appointment `showed` OU tag `visitou-loja`
OU confirmação no painel = PROVA; menção em transcrição = visita_provavel (só pontua
depois de confirmada com 1 clique).
"""
import datetime as dt

import ghl
import score
from brain import rules, cards

CF_HOW_SOON = "21s4ZqYAMUEAD30f0Xyd"
CF_VEH = {"make": "CiRd678lAFn854igklGR", "model": "LHwTnTb8TPz5BbJ0I2XV",
          "year": "C01IzbXlbESCLfhoHkrZ"}
VISIT_TAG = "visitou-loja"


def latest_analysis(contact_id):
    rows = cards._sb("GET", ("analyses?select=payload,created_at,calls!inner(contact_id)"
                             f"&calls.contact_id=eq.{contact_id}"
                             "&order=created_at.desc&limit=1")) or []
    return rows[0]["payload"] if rows else None


def all_messages(contact_id, max_convs=3):
    """Engajamento lê TODAS as conversas (bug antigo: só a primeira)."""
    msgs = []
    r = ghl.get("/conversations/search", {"locationId": ghl.LOCATION_ID,
                                          "contactId": contact_id})
    if r.status_code == 200:
        for cv in r.json().get("conversations", [])[:max_convs]:
            m = ghl.get(f"/conversations/{cv['id']}/messages")
            if m.status_code == 200:
                msgs += m.json().get("messages", {}).get("messages", [])
    return msgs


def manual_fields(contact_id):
    """Último Log call details sincronizado — entrada manual VENCE o cérebro."""
    rows = cards._sb("GET", f"manual_logs?contact_id=eq.{contact_id}"
                            "&order=created_at.desc&limit=1&select=fields") or []
    return rows[0]["fields"] if rows else {}


def visit_proof(contact, contact_id):
    """(provado, motivo) — tag OU showed OU confirmação no painel."""
    if VISIT_TAG in (contact.get("tags") or []):
        return True, "tag visitou-loja"
    fl = cards._sb("GET", f"lead_flags?contact_id=eq.{contact_id}&select=visited_store") or []
    if fl and fl[0].get("visited_store"):
        return True, "visita confirmada no painel"
    r = ghl.get(f"/contacts/{contact_id}/appointments")
    if r.status_code == 200:
        for e in r.json().get("events", []):
            if e.get("appointmentStatus") == "showed":
                return True, f"appointment showed ({str(e.get('startTime'))[:10]})"
    return False, None


def quote_signal(opp, msgs):
    st = rules.STAGE_BY_ID.get((opp or {}).get("pipelineStageId"))
    if st == "Quote Sent":
        return True, "opp em Quote Sent"
    for m in msgs:
        if (m.get("messageType") == "TYPE_SMS" and m.get("direction") == "outbound"
                and rules.URABLE_LINK.search(m.get("body") or "")):
            return True, "link Urable enviado por SMS"
    return False, None


def compute_for(contact_id, opp=None, analysis=None, contact=None, msgs=None,
                persist=True):
    """Score v3 de um lead juntando todas as fontes. Persiste em lead_scores e
    espelha nos cards abertos (score/max/selo/breakdown). Retorna o dict do score."""
    if contact is None:
        cr = ghl.get(f"/contacts/{contact_id}")
        contact = cr.json().get("contact", {}) if cr.status_code == 200 else {}
    if opp is None:
        r = ghl.get("/opportunities/search",
                    {"location_id": ghl.LOCATION_ID, "contact_id": contact_id, "limit": 5})
        if r.status_code == 200:
            opps = r.json().get("opportunities", [])
            opp = next((o for o in opps if o.get("status") == "open"),
                       opps[0] if opps else None)
    if msgs is None:
        msgs = all_messages(contact_id)
    if analysis is None:
        analysis = latest_analysis(contact_id)

    cfs = {f.get("id"): f.get("value") for f in contact.get("customFields", [])}
    manual = manual_fields(contact_id)
    av = (analysis or {}).get("vehicle") or {}

    # veículo: manual > CF > análise (nome da opp entra como fallback dentro do score)
    veh_src = None
    make = model = year = None
    for src, m_, mo_, y_ in (("manual", manual.get("make"), manual.get("model"), manual.get("year")),
                             ("cf", cfs.get(CF_VEH["make"]), cfs.get(CF_VEH["model"]), cfs.get(CF_VEH["year"])),
                             ("call", av.get("make"), av.get("model"), av.get("year"))):
        if m_ or mo_ or y_:
            make, model, year, veh_src = m_, mo_, y_, src
            break

    visited, visit_r = visit_proof(contact, contact_id)
    q_sent, q_r = quote_signal(opp, msgs)

    s = score.compute(make=make, model=model, year=year,
                      opp_name=(opp or {}).get("name"),
                      how_soon=cfs.get(CF_HOW_SOON),
                      msgs=msgs, call_analysis=analysis,
                      momento_manual=manual.get("momento"),
                      visited_store=visited, visit_reason=visit_r,
                      quote_sent=q_sent, quote_reason=q_r)
    s["car_src"] = veh_src or "nome_opp"

    if persist:
        components = {
            "car": {"value": s["car"], "reason": s["car_reason"], "source": s["car_src"]},
            "momento": {"value": s["momento"], "reason": s["momento_reason"],
                        "source": s.get("momento_src")},
            "eng": {"value": s["eng"], "reason": s["eng_reason"], "source": "mensagens"},
            "int": {"value": s["int"], "reason": s["int_reason"],
                    "source": s.get("int_src")},
        }
        cards._sb("POST", "lead_scores?on_conflict=contact_id", json={
            "contact_id": contact_id, "known": s["known"],
            "max_possible": s["max_possible"], "badge": s["badge"],
            "components": components, "breakdown": s["breakdown"],
            "visited_store": s["visited_store"],
            "computed_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        }, headers_extra={"Prefer": "resolution=merge-duplicates"})
        cards._sb("PATCH", f"cards?status=eq.open&contact_id=eq.{contact_id}", json={
            "score": s["known"], "score_max": s["max_possible"],
            "score_badge": s["badge"], "score_breakdown": s["breakdown"],
        })
    return s
