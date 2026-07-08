"""
MVP item 6 — Verificador pós-call: compara o que foi DITO na call (análise, com
evidência literal) vs. o que está REGISTRADO no GHL. Lacuna vira Pendência no card.

REGRAS DURAS DE REDAÇÃO:
- Formato fixo: [FATO com evidência e data] → [AÇÃO exata no GHL].
- Zero coach, zero opinião, zero suposição. Sem evidência literal = a pendência
  NÃO existe (fail-closed, mesma Regra nº 1 do advice).
- Resoluções alternativas: a pendência some com QUALQUER resolução válida,
  detectada por LEITURA no ciclo seguinte. O sistema JAMAIS preenche/envia/move.
"""
import datetime as dt

import ghl
from brain import cards, rules, score_engine

CF_VEH = score_engine.CF_VEH
CF_INTERESSE = "D5TgphY9HlZMoS8wcWj1"


def _hora(ts):
    try:
        return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")) \
            .astimezone(dt.timezone(dt.timedelta(hours=-4))).strftime("%d/%m %H:%M")
    except Exception:
        return str(ts)[:16]


def _open_pend(contact_id, kind):
    return cards._sb("GET", f"pendencias?status=eq.open&contact_id=eq.{contact_id}"
                            f"&kind=eq.{kind}&select=id&limit=1")


def _add(contact_id, call_id, kind, fato, acao, resolucoes, snapshot=None):
    if _open_pend(contact_id, kind):
        return 0
    cards._sb("POST", "pendencias", json={
        "contact_id": contact_id, "call_id": call_id, "kind": kind,
        "fato": fato, "acao": acao, "resolucoes": resolucoes,
        "snapshot": snapshot or {}})
    return 1


def check_call(msg, contact, opp, analysis):
    """Roda após cada call analisada. Só aponta com evidência literal (fail-closed)."""
    cid = msg["contactId"]
    call_id = msg["id"]
    quando = _hora(msg.get("dateAdded"))
    meta = (msg.get("meta") or {}).get("call") or {}
    answered = bool(meta.get("duration") and meta["duration"] > 20)
    cfs = {f.get("id"): f.get("value") for f in (contact or {}).get("customFields", [])}
    stage = rules.STAGE_BY_ID.get((opp or {}).get("pipelineStageId"))
    n = 0

    # (UI 100% em inglês — ordem do Rafael 2026-07-08: o Eugene é quem lê)
    if analysis and answered:
        v = analysis.get("vehicle") or {}
        veh_txt = " ".join(str(x) for x in (v.get("year"), v.get("make"), v.get("model")) if x)
        # 1) veículo dito na call e ausente no perfil
        if (v.get("make") or v.get("model")) and not (cfs.get(CF_VEH["make"]) or cfs.get(CF_VEH["model"])):
            n += _add(cid, call_id, "veiculo_faltando",
                      f"Call {quando} — customer stated the vehicle: {veh_txt}.",
                      "Vehicle is not on the profile → add make/model/year to the contact.",
                      [{"tipo": "cf_preenchido", "cf": "vehicle"}],
                      {"stage": stage})
        # 2) interesse dito e ausente
        interesse = analysis.get("servico_interesse") or ""
        if interesse and not cfs.get(CF_INTERESSE):
            ev = (analysis.get("intencao") or {}).get("evidencia") or interesse
            n += _add(cid, call_id, "interesse_faltando",
                      f"Call {quando} — interest stated: \"{ev[:120]}\".",
                      f"Interest is not on the contact → fill the interest field with '{interesse}'.",
                      [{"tipo": "cf_preenchido", "cf": "interesse"}],
                      {"stage": stage})
        # 3) call atendida sem fechamento registrado
        desinteresse = (analysis.get("resolucao_da_call") == "desqualificou")
        ev_des = (analysis.get("intencao") or {}).get("evidencia") or ""
        if desinteresse and ev_des:
            n += _add(cid, call_id, "sem_fechamento",
                      f"Call {quando} — customer said: \"{ev_des[:120]}\".",
                      "Mark the opportunity Lost with the reason.",
                      [{"tipo": "stage", "alvo": "Lost"}],
                      {"stage": stage, "call_ts": msg.get("dateAdded")})
        elif not desinteresse:
            n += _add(cid, call_id, "sem_fechamento",
                      f"Call answered {quando} ({meta.get('duration')}s) with no closure logged after.",
                      "Send today's follow-up OR, if the customer has no interest, "
                      "mark Lost with the reason.",
                      [{"tipo": "sms_apos", "ts": msg.get("dateAdded")},
                       {"tipo": "stage", "alvo": "Lost"}],
                      {"stage": stage, "call_ts": msg.get("dateAdded")})
    if analysis and not answered:
        # 4) não atendida sem voicemail — só com o fato registrado pela análise
        if analysis.get("voicemail_left") is False:
            n += _add(cid, call_id, "voicemail_nao_deixado",
                      f"Voicemail was not left (attempt {quando}).",
                      "Move the lead to the next cadence stage so the attempt "
                      "message fires.",
                      [{"tipo": "stage_mudou", "de": stage}],
                      {"stage": stage})
    return n


def sweep_resolutions(limit=200):
    """Resolve pendências por LEITURA: qualquer resolução válida a apaga sozinha."""
    rows = cards._sb("GET", f"pendencias?status=eq.open&select=*&limit={limit}") or []
    resolved = 0
    by_contact = {}
    for p in rows:
        by_contact.setdefault(p["contact_id"], []).append(p)
    for cid, pends in by_contact.items():
        cr = ghl.get(f"/contacts/{cid}")
        contact = cr.json().get("contact", {}) if cr.status_code == 200 else {}
        cfs = {f.get("id"): f.get("value") for f in contact.get("customFields", [])}
        opr = ghl.get("/opportunities/search", {"location_id": ghl.LOCATION_ID,
                                                "contact_id": cid, "limit": 5})
        opps = opr.json().get("opportunities", []) if opr.status_code == 200 else []
        stages = {rules.STAGE_BY_ID.get(o.get("pipelineStageId")) for o in opps}
        msgs = None
        for p in pends:
            done = None
            for r in p.get("resolucoes") or []:
                t = r.get("tipo")
                if t == "cf_preenchido":
                    if r["cf"] == "vehicle" and (cfs.get(CF_VEH["make"]) or cfs.get(CF_VEH["model"])):
                        done = "veículo preenchido no contato"
                    if r["cf"] == "interesse" and cfs.get(CF_INTERESSE):
                        done = "interesse preenchido no contato"
                elif t == "stage" and r.get("alvo") in stages:
                    done = f"stage {r['alvo']} confirmado"
                elif t == "stage_mudou" and stages and r.get("de") not in stages:
                    done = f"stage avançou ({r.get('de')} → {'/'.join(s or '?' for s in stages)})"
                elif t == "sms_apos":
                    if msgs is None:
                        msgs = score_engine.all_messages(cid, max_convs=1)
                    if any(m.get("messageType") == "TYPE_SMS"
                           and m.get("direction") == "outbound"
                           and (m.get("dateAdded") or "") > (r.get("ts") or "")
                           for m in msgs):
                        done = "follow-up (SMS outbound) detectado após a call"
                if done:
                    break
            if done:
                cards._sb("PATCH", f"pendencias?id=eq.{p['id']}", json={
                    "status": "resolved", "resolved_by": done,
                    "resolved_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")})
                resolved += 1
    return resolved
