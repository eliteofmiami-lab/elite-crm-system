"""
MISSÃO análise total — Onda 0 (síncrona, docs/missoes/prompt-analise-total.md, Adendo 2).

Escopo: leads com atividade/criação ≤90d, opp fora de Win/delete, sem lost terminal,
sem teste-interno, com call atendida >20s. FAIXA A (obrigatória, em ordem):
Quote Sent → appointment ≤3d → respondeu SMS ≤14d → inbound ≤30d → no-show 90d.
FAIXA B: pontos de análise (analysis_priority) em ordem decrescente.

Por lead: APENAS a última call atendida >20s. Já analisada = PULAR (reprocessamento
proibido) — só rescore v3. NENHUMA escrita no GHL (G2 fechado): tudo no Supabase.
Circuit breaker: 3 tentativas por call; falha = pula, loga, segue.
Teto de custo Onda 0: $15 (ordem da noite 2026-07-08). Custos em cost_log.
"""
import datetime as dt
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
import ghl  # noqa: E402
from brain import rules, cards, transcribe, analyze, advice_gate, score_engine  # noqa: E402

CAP_USD = 15.0
ET_NOW = dt.datetime.now(dt.timezone.utc)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
BLOCKED = []
_lock = threading.Lock()
_spend = {"usd": 0.0}

OPEN_STAGES = ["Quote Sent", "Appointment Booked", "Great Cars", "HOT LEADS", "New Lead",
               "Contact 1 (AM)", "Contact 1 (PM)", "Contact 2 (AM)", "Contact 2 (PM)",
               "Contact 3 (AM)", "Contact 3 (PM)", "Follow Up"]
CF_HOW_SOON = "21s4ZqYAMUEAD30f0Xyd"


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def paged_opps(stage_id):
    out, page = [], 1
    while True:
        r = ghl.get("/opportunities/search",
                    {"location_id": ghl.LOCATION_ID, "pipeline_id": rules.NEW_PIPELINE_ID,
                     "pipeline_stage_id": stage_id, "limit": 100, "page": page})
        if r.status_code != 200:
            break
        ops = r.json().get("opportunities", [])
        out += ops
        if len(ops) < 100:
            break
        page += 1
    return out


def gather_candidates():
    """contact_id → info (opp, stage, sinais). Só opps abertas do New Pipeline."""
    cands = {}
    for st in OPEN_STAGES:
        for o in paged_opps(rules.STAGES[st]):
            if o.get("status") != "open":
                continue
            cid = o["contactId"]
            cur = cands.get(cid)
            if not cur or cards.STAGE_RANK.get(st, 0) > cards.STAGE_RANK.get(cur["stage"], 0):
                cands[cid] = {"opp": o, "stage": st, "signals": set()}
    log(f"opps abertas: {sum(1 for _ in cands)} contatos em {len(OPEN_STAGES)} stages")

    # appointments ±: próximos 3d (faixa A2) e no-shows 90d (A5)
    now = dt.datetime.now(dt.timezone.utc)
    for cal_name, cal_id in cards.CALENDARS.items():
        r = ghl.get("/calendars/events",
                    {"locationId": ghl.LOCATION_ID, "calendarId": cal_id,
                     "startTime": int((now - dt.timedelta(days=90)).timestamp() * 1000),
                     "endTime": int((now + dt.timedelta(days=3)).timestamp() * 1000)})
        if r.status_code != 200:
            continue
        events = r.json().get("events", [])
        future_by_contact = {}
        for e in events:
            cid = e.get("contactId")
            st_time = str(e.get("startTime") or "")
            if cid and st_time >= f"{now:%Y-%m-%d}":
                future_by_contact.setdefault(cid, []).append(e)
        for e in events:
            cid = e.get("contactId")
            if not cid:
                continue
            st_time = str(e.get("startTime") or "")
            if e.get("appointmentStatus") in ("new", "booked", "confirmed") and st_time >= f"{now:%Y-%m-%d}":
                if cid in cands:
                    cands[cid]["signals"].add("appt_3d")
            if e.get("appointmentStatus") == "noshow" and cid not in future_by_contact:
                if cid not in cands:
                    cands[cid] = {"opp": None, "stage": "no-show", "signals": set()}
                cands[cid]["signals"].add("noshow")
    return cands


def enrich(cid, info):
    """Contato + mensagens (sinais, última call atendida). 1 contato por vez."""
    cr = ghl.get(f"/contacts/{cid}")
    if cr.status_code != 200:
        return None
    contact = cr.json().get("contact", {})
    if "teste-interno" in (contact.get("tags") or []):
        return None
    msgs = score_engine.all_messages(cid)
    now = dt.datetime.now(dt.timezone.utc)
    last_call = None
    for m in msgs:
        if m.get("messageType") != "TYPE_CALL":
            continue
        dur = ((m.get("meta") or {}).get("call") or {}).get("duration") or 0
        ts = m.get("dateAdded") or ""
        if dur > 20 and (not last_call or ts > last_call["ts"]):
            last_call = {"id": m["id"], "ts": ts, "dur": dur,
                         "direction": m.get("direction"), "status": m.get("status"),
                         "conversation_id": m.get("conversationId"), "to": m.get("to"),
                         "user_id": m.get("userId")}
        d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
        if d:
            age = (now - d).days
            if m.get("messageType") == "TYPE_CALL" and m.get("direction") == "inbound":
                if age <= 30:
                    info["signals"].add("inbound_30d")
                elif age <= 90:
                    info["signals"].add("inbound_old")
        if m.get("messageType") == "TYPE_SMS" and m.get("direction") == "inbound" and d:
            age = (now - d).days
            if age <= 14:
                info["signals"].add("sms_14d")
            elif age <= 90:
                info["signals"].add("sms_old")
    if info["stage"] == "Quote Sent":
        info["signals"].add("quote_sent")
    cfs = {f.get("id"): f.get("value") for f in contact.get("customFields", [])}
    # recência: criação do contato ou última mensagem
    last_ts = max((m.get("dateAdded") or "" for m in msgs), default="") or contact.get("dateAdded", "")
    info.update({"contact": contact, "msgs": msgs, "last_call": last_call,
                 "cfs": cfs, "last_activity": last_ts})
    return info


def faixa_a_rank(info):
    s = info["signals"]
    for rank, key in ((1, "quote_sent"), (2, "appt_3d"), (3, "sms_14d"),
                      (4, "inbound_30d"), (5, "noshow")):
        if key in s:
            return rank
    return None


def analysis_priority(info):
    """FAIXA B — pontos do Adendo 2."""
    pts = 0
    name = (info.get("opp") or {}).get("name") or ""
    blob = name.lower()
    import score as sc
    car, _ = sc.car_score(name=name)
    pts += {35: 30, 25: 20}.get(car, 0)  # exótico/premium 30 · 2026 20
    services = str(next((v for k, v in info.get("cfs", {}).items()
                         if isinstance(v, str) and ("ppf" in str(v).lower() or "coating" in str(v).lower())), "")).lower()
    if "both" in services:
        pts += 20
    elif "ppf" in services:
        pts += 15
    elif "coating" in services:
        pts += 8
    elif "not sure" in services or "help" in services:
        pts += 5
    hs = str(info.get("cfs", {}).get(CF_HOW_SOON) or "").lower()
    pts += {"as soon as possible": 15, "within the next 2 weeks": 12,
            "within the next month": 6}.get(hs, 0)
    if "inbound_old" in info["signals"]:
        pts += 10
    if "sms_old" in info["signals"]:
        pts += 8
    la = info.get("last_activity") or ""
    if la:
        age = (dt.datetime.now(dt.timezone.utc)
               - dt.datetime.fromisoformat(la.replace("Z", "+00:00"))).days
        pts += 10 if age <= 30 else 5 if age <= 60 else 2 if age <= 90 else 0
    return min(pts, 100)


def already_analyzed(call_id):
    return bool(cards._sb("GET", f"analyses?call_id=eq.{call_id}&select=call_id&limit=1"))


def add_cost(call_id, provider, model, units, usd):
    with _lock:
        _spend["usd"] += usd
    cards._sb("POST", "cost_log", json={"call_id": call_id, "provider": provider,
                                        "model": model, "units": units, "est_usd": usd})


def process_one(cid, info):
    """download → deepgram → sonnet (+ gate haiku) → persist → sinais → rescore."""
    call = info["last_call"]
    call_id = call["id"]
    client = analyze.get_client()
    audio = None
    for attempt in range(3):
        try:
            audio = transcribe.download_recording(call_id)
            if audio:
                break
        except Exception:
            pass
        time.sleep(2 ** attempt)
    if not audio:
        raise RuntimeError("gravação indisponível (3 tentativas)")
    t = transcribe.transcribe(audio)
    add_cost(call_id, "deepgram", "nova-2", round(call["dur"] / 60, 2),
             round(call["dur"] / 60 * 0.0043, 5))
    text = transcribe.diarized_as_text(t["diarized"]) or t["full_text"]
    if not text.strip():
        raise RuntimeError("transcrição vazia")
    analysis = analyze.analyze_call(text, {"direction": call["direction"],
                                           "duration_sec": call["dur"],
                                           "status": call.get("status")}, client=client)
    m = analysis.pop("_meta", {})
    if m:
        add_cost(call_id, "anthropic", m["model"], m["in_tokens"] + m["out_tokens"], m["est_usd"])
    analysis, ok, motivo = advice_gate.gate_analysis(analysis, text, call_id=call_id,
                                                     contact_id=cid, client=client)
    add_cost(call_id, "anthropic", "claude-haiku-4-5-critic", 1, 0.003)
    # persist (Supabase only — G2 fechado)
    h2 = {"Prefer": "resolution=merge-duplicates"}
    cards._sb("POST", "calls", headers_extra=h2, json={
        "id": call_id, "contact_id": cid, "conversation_id": call.get("conversation_id"),
        "opportunity_id": (info.get("opp") or {}).get("id"),
        "direction": call["direction"], "status": call.get("status"),
        "duration_sec": call["dur"], "dialed_number": call.get("to"),
        "user_id": call.get("user_id"), "called_at": call["ts"],
        "recording_downloaded": True})
    cards._sb("POST", "transcripts", headers_extra=h2, json={
        "call_id": call_id, "provider": "deepgram", "language": t.get("language"),
        "diarized": t["diarized"], "full_text": t["full_text"]})
    cards._sb("POST", "analyses", headers_extra=h2, json={
        "call_id": call_id, "model": analyze.MODEL, "payload": analysis})
    # sinais A9/A11/A12-c/A13
    if analysis.get("servico_interesse"):
        prev = cards._sb("GET", f"interest_history?contact_id=eq.{cid}&source=eq.call"
                                f"&interest=eq.{analysis['servico_interesse']}&select=id&limit=1")
        if not prev:
            cards._sb("POST", "interest_history", json={
                "contact_id": cid, "interest": analysis["servico_interesse"],
                "source": "call", "set_by": "analise-total"})
    pt = analysis.get("pergunta_tecnica") or {}
    if pt.get("houve"):
        dup = cards._sb("GET", f"technical_observations?call_id=eq.{call_id}&select=id&limit=1")
        if not dup:
            cards._sb("POST", "technical_observations", json={
                "call_id": call_id, "contact_id": cid,
                "contact_name": (info.get("opp") or {}).get("name"),
                "pergunta": pt.get("pergunta"), "categoria": pt.get("categoria"),
                "transferida": pt.get("transferida"),
                "resposta_improvisada": pt.get("resposta_improvisada"),
                "como_tratou": ("transferida ao vivo" if pt.get("transferida") else
                                "callback prometido" if pt.get("prometeu_callback") else
                                "respondida na hora"),
                "promised_callback": pt.get("prometeu_callback", False)})
    vl = analysis.get("visita_loja") or {}
    if vl.get("ja_visitou_mencionado"):
        fl = cards._sb("GET", f"lead_flags?contact_id=eq.{cid}&select=visited_store") or []
        if not (fl and fl[0].get("visited_store")):
            cards._sb("POST", "lead_flags?on_conflict=contact_id",
                      headers_extra=h2,
                      json={"contact_id": cid, "visit_probable": {
                          "evidencia": vl.get("evidencia"), "call_id": call_id,
                          "detected_at": dt.datetime.now(dt.timezone.utc).isoformat()}})
    cp = analysis.get("cupom_oferecido") or {}
    if cp.get("houve"):
        dup = cards._sb("GET", f"coupons?call_id=eq.{call_id}&select=id&limit=1")
        if not dup:
            cards._sb("POST", "coupons", json={
                "contact_id": cid, "call_id": call_id, "source": "call",
                "contexto": (cp.get("contexto") or "")[:300],
                "offered_by": "detectado na transcrição"})
    # score v3 (Supabase; GHL gated)
    s = score_engine.compute_for(cid, opp=info.get("opp"), analysis=analysis,
                                 contact=info["contact"], msgs=info["msgs"])
    return {"contact_id": cid, "call_id": call_id, "score": s["known"],
            "max": s["max_possible"], "badge": s["badge"],
            "resolucao": analysis.get("resolucao_da_call"),
            "advice_ok": ok}


def main():
    dry_estimate_only = "--estimate" in sys.argv
    log("== ONDA 0: coleta de candidatos ==")
    cands = gather_candidates()
    log(f"candidatos brutos: {len(cands)}")

    enriched = {}
    for i, (cid, info) in enumerate(cands.items(), 1):
        try:
            e = enrich(cid, info)
            if e:
                enriched[cid] = e
        except Exception as ex:
            BLOCKED.append({"contact_id": cid, "fase": "enrich", "causa": str(ex)[:120]})
        if i % 50 == 0:
            log(f"  enriquecidos {i}/{len(cands)}")
    log(f"elegíveis pós-contato: {len(enriched)} (teste-interno/erros fora)")

    # fila de análise: Faixa A (rank 1-5) → Faixa B (priority desc)
    to_do, skipped_done, no_call = [], 0, 0
    for cid, info in enriched.items():
        info["faixa_a"] = faixa_a_rank(info)
        info["priority"] = analysis_priority(info)
        cards._sb("POST", "lead_flags?on_conflict=contact_id",
                  headers_extra={"Prefer": "resolution=merge-duplicates"},
                  json={"contact_id": cid, "analysis_priority": info["priority"]})
        if not info["last_call"]:
            no_call += 1
            continue
        # elegibilidade extra p/ candidatos vindos só de no-show: Win/terminal fora
        if info["stage"] == "no-show":
            fl = cards._sb("GET", f"lead_flags?contact_id=eq.{cid}&select=cold_excluded") or []
            if fl and fl[0].get("cold_excluded"):
                continue
            if cards.most_advanced_stage(cid) in ("Win", "delete"):
                continue
        if already_analyzed(info["last_call"]["id"]):
            skipped_done += 1
            try:  # sem custo: rescore v3 com a análise existente
                score_engine.compute_for(cid, opp=info.get("opp"),
                                         contact=info["contact"], msgs=info["msgs"])
            except Exception:
                pass
            continue
        to_do.append((cid, info))
    to_do.sort(key=lambda x: (x[1]["faixa_a"] or 99, -x[1]["priority"]))

    n_a = sum(1 for _, i in to_do if i["faixa_a"])
    minutes = sum(i["last_call"]["dur"] for _, i in to_do) / 60
    est = minutes * 0.0043 + len(to_do) * 0.025
    log(f"== ESTIMATIVA: {len(to_do)} calls ({n_a} Faixa A, {len(to_do) - n_a} Faixa B) · "
        f"{minutes:.0f} min de áudio · ~${est:.2f} (teto ${CAP_USD}) · "
        f"já analisadas puladas: {skipped_done} · sem call atendida: {no_call}")
    json.dump({"estimate_usd": round(est, 2), "calls": len(to_do), "faixa_a": n_a,
               "skipped": skipped_done, "no_call": no_call,
               "at": dt.datetime.now(dt.timezone.utc).isoformat()},
              open(OUT / "onda0_estimate.json", "w"), indent=2)
    if dry_estimate_only:
        return
    if est > CAP_USD:
        cut = int(CAP_USD / (est / max(len(to_do), 1)))
        log(f"!! estimativa acima do teto — processando só os {cut} primeiros "
            f"(Faixa A completa tem prioridade); resto vai pra Onda 1 (Batch)")
        to_do = to_do[:max(cut, n_a)]

    log(f"== PROCESSANDO {len(to_do)} calls (5 paralelas, breaker 3x) ==")
    results, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {}
        for cid, info in to_do:
            if _spend["usd"] >= CAP_USD * 0.97:
                BLOCKED.append({"contact_id": cid, "fase": "budget",
                                "causa": f"teto ${CAP_USD} atingido — vai pra Onda 1"})
                continue
            futs[pool.submit(process_one, cid, info)] = cid
        for n, fut in enumerate(as_completed(futs), 1):
            cid = futs[fut]
            try:
                results.append(fut.result())
            except Exception as ex:
                BLOCKED.append({"contact_id": cid, "fase": "process", "causa": str(ex)[:150]})
            if n % 25 == 0:
                rate = n / (time.time() - t0)
                eta = (len(futs) - n) / max(rate, 0.01) / 60
                log(f"  {n}/{len(futs)} · ${_spend['usd']:.2f} gastos · ETA {eta:.0f} min")

    log(f"== FIM: {len(results)} analisadas · {len(BLOCKED)} bloqueadas · "
        f"custo real ${_spend['usd']:.2f} / teto ${CAP_USD} ==")
    verified = sum(1 for r in results if r["badge"] == "call-verified")
    json.dump({"processed": results, "blocked": BLOCKED,
               "spend_usd": round(_spend["usd"], 2),
               "skipped_already": skipped_done, "no_call": no_call,
               "finished": dt.datetime.now(dt.timezone.utc).isoformat()},
              open(OUT / "onda0_result.json", "w"), indent=2, ensure_ascii=False)
    if BLOCKED:
        lines = ["# BLOCKED — Onda 0 · " + f"{dt.datetime.now():%Y-%m-%d %H:%M}", ""]
        lines += [f"- `{b['contact_id']}` [{b['fase']}]: {b['causa']}" for b in BLOCKED]
        (ROOT / "BLOCKED.md").write_text("\n".join(lines))

    # baseline de tracking (daily_snapshots)
    ls = cards._sb("GET", "lead_scores?select=known,badge") or []
    open_cards = cards._sb("GET", "cards?status=eq.open&select=layer,score_badge") or []
    dist = {}
    for r in ls:
        b = (r["known"] // 20) * 20
        dist[f"{b}-{b + 19}"] = dist.get(f"{b}-{b + 19}", 0) + 1
    cards._sb("POST", "daily_snapshots?on_conflict=snapshot_date",
              headers_extra={"Prefer": "resolution=merge-duplicates"},
              json={"snapshot_date": f"{dt.datetime.now():%Y-%m-%d}",
                    "payload": {"score_dist": dist, "scored": len(ls),
                                "call_verified": sum(1 for r in ls if r["badge"] == "call-verified"),
                                "open_cards": len(open_cards),
                                "cards_by_layer": {str(l): sum(1 for c in open_cards if c["layer"] == l)
                                                   for l in (1, 2, 3)},
                                "analyzed_tonight": len(results),
                                "spend_usd": round(_spend["usd"], 2)}})
    log(f"snapshot diário gravado · call-verified novos: {verified}/{len(results)}")


if __name__ == "__main__":
    main()
