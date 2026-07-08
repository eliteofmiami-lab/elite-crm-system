"""
MVP — backlog de sínteses de estado (Regra Zero) para TODOS os leads elegíveis.
Fases: --estimate (conta e custa, não roda) · --run (executa dentro do teto $40).

1. Candidatos = opps abertas do New Pipeline + no-shows (mesma coleta da análise total).
2. Calls atendidas ainda sem análise → Deepgram (sync) + análise (Batch; fallback sync
   se a gramática do schema for rejeitada pelo Batch).
3. Linha do tempo por lead → síntese de estado via Batch (schema pequeno) → lead_states.
4. apply_state + rescore v3 + fila regenerada.
ZERO escrita no GHL (writer congelado); Supabase é o único destino.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
import ghl  # noqa: E402
from brain import cards, transcribe, analyze, lead_state, score_engine  # noqa: E402
import analise_total as at  # noqa: E402  (reusa gather/enrich)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
CAP_USD = 40.0
_spend = {"usd": 0.0}


def log(m):
    print(f"[{dt.datetime.now():%H:%M:%S}] {m}", flush=True)


def add_cost(call_id, provider, model, units, usd):
    _spend["usd"] += usd
    cards._sb("POST", "cost_log", json={"call_id": call_id, "provider": provider,
                                        "model": model, "units": units, "est_usd": usd})


def gather():
    cands = at.gather_candidates()
    enriched = {}
    for i, (cid, info) in enumerate(cands.items(), 1):
        try:
            e = at.enrich(cid, info)
            if e:
                enriched[cid] = e
        except Exception as ex:
            log(f"  [warn] enrich {cid}: {str(ex)[:60]}")
        if i % 100 == 0:
            log(f"  enriquecidos {i}/{len(cands)}")
    # calls atendidas sem análise
    pend_calls = []
    for cid, info in enriched.items():
        lc = info.get("last_call")
        if lc and not cards._sb("GET", f"analyses?call_id=eq.{lc['id']}&select=call_id&limit=1"):
            pend_calls.append((cid, info))
    return enriched, pend_calls


def main():
    mode = "--run" if "--run" in sys.argv else "--estimate"
    log("== MVP backlog: coleta ==")
    enriched, pend_calls = gather()
    n_synth = len(enriched)
    mins = sum(i["last_call"]["dur"] for _, i in pend_calls) / 60
    est_calls = mins * 0.0043 + len(pend_calls) * 0.013      # deepgram + sonnet batch
    est_synth = n_synth * 0.014                               # estado: batch 50% + caching
    est = est_calls + est_synth
    log(f"== ESTIMATIVA: {len(pend_calls)} calls a analisar ({mins:.0f} min, ~${est_calls:.2f})"
        f" + {n_synth} sínteses de estado (~${est_synth:.2f}) = ~${est:.2f} (teto ${CAP_USD}) ==")
    json.dump({"pend_calls": len(pend_calls), "synth": n_synth,
               "estimate_usd": round(est, 2)}, open(OUT / "mvp_estimate.json", "w"))
    if mode == "--estimate":
        return
    if est > CAP_USD:
        log("!! acima do teto — ABORTAR e reportar (ordem do Rafael)")
        return

    client = analyze.get_client()
    h2 = {"Prefer": "resolution=merge-duplicates"}

    # ---- fase 1: transcrever pendentes (sync) e analisar via Batch ----
    reqs = []
    for n, (cid, info) in enumerate(pend_calls, 1):
        if _spend["usd"] >= CAP_USD * 0.9:
            log("teto de segurança na transcrição — parando novas transcrições")
            break
        call = info["last_call"]
        audio = None
        for a in range(3):
            try:
                audio = transcribe.download_recording(call["id"])
                if audio:
                    break
            except Exception:
                pass
            time.sleep(2 ** a)
        if not audio:
            continue
        try:
            t = transcribe.transcribe(audio)
        except Exception:
            continue
        add_cost(call["id"], "deepgram", "nova-2", round(call["dur"] / 60, 2),
                 round(call["dur"] / 60 * 0.0043, 5))
        cards._sb("POST", "calls", headers_extra=h2, json={
            "id": call["id"], "contact_id": cid, "direction": call["direction"],
            "duration_sec": call["dur"], "called_at": call["ts"],
            "recording_downloaded": True})
        cards._sb("POST", "transcripts", headers_extra=h2, json={
            "call_id": call["id"], "language": t.get("language"),
            "diarized": t["diarized"], "full_text": t["full_text"]})
        text = transcribe.diarized_as_text(t["diarized"]) or t["full_text"]
        reqs.append({"custom_id": call["id"],
                     "params": {"model": analyze.MODEL, "max_tokens": 8000,
                                "system": [{"type": "text", "text": analyze.SYSTEM,
                                            "cache_control": {"type": "ephemeral"}}],
                                "output_config": {"format": {"type": "json_schema",
                                                             "schema": analyze.ANALYSIS_SCHEMA}},
                                "messages": [{"role": "user", "content": (
                                    f"Metadados da chamada: {json.dumps({'direction': call['direction'], 'duration_sec': call['dur']})}\n\n"
                                    f"Transcrição diarizada:\n{text}")}]}})
        if n % 25 == 0:
            log(f"  transcritas {n}/{len(pend_calls)} · ${_spend['usd']:.2f}")

    analyzed = {}
    if reqs:
        # teste de gramática com 1 request antes do lote inteiro
        probe = client.messages.batches.create(requests=reqs[:1])
        while True:
            b = client.messages.batches.retrieve(probe.id)
            if b.processing_status == "ended":
                break
            time.sleep(20)
        probe_ok = any(e.result.type == "succeeded"
                       for e in client.messages.batches.results(probe.id))
        log(f"probe do batch de análises: {'ok' if probe_ok else 'REJEITADO (gramática?)'}")
        rest = reqs[1:] if probe_ok else reqs
        if probe_ok and rest:
            batch = client.messages.batches.create(requests=rest)
            log(f"batch análises {batch.id} ({len(rest)} reqs) — aguardando…")
            while True:
                b = client.messages.batches.retrieve(batch.id)
                if b.processing_status == "ended":
                    break
                time.sleep(45)
            it, ot = 0, 0
            for entry in list(client.messages.batches.results(probe.id)) + \
                    list(client.messages.batches.results(batch.id)):
                if entry.result.type != "succeeded":
                    continue
                msg = entry.result.message
                it += msg.usage.input_tokens
                ot += msg.usage.output_tokens
                pay = json.loads(next(bl.text for bl in msg.content if bl.type == "text"))
                analyzed[entry.custom_id] = pay
                cards._sb("POST", "analyses", headers_extra=h2, json={
                    "call_id": entry.custom_id, "model": f"{analyze.MODEL} (batch)",
                    "payload": pay})
            add_cost("mvp-batch-analises", "anthropic", f"{analyze.MODEL} (batch)",
                     it + ot, round((it / 1e6 * 3.0 + ot / 1e6 * 15.0) * 0.5, 3))
        else:
            # fallback: sync (gramática rejeitada no batch)
            log("fallback SYNC para análises…")
            for rq_ in reqs:
                if _spend["usd"] >= CAP_USD * 0.9:
                    break
                try:
                    r = client.messages.create(**{k: v for k, v in rq_["params"].items()})
                    pay = json.loads(next(bl.text for bl in r.content if bl.type == "text"))
                    analyzed[rq_["custom_id"]] = pay
                    add_cost(rq_["custom_id"], "anthropic", analyze.MODEL,
                             r.usage.input_tokens + r.usage.output_tokens,
                             round(r.usage.input_tokens / 1e6 * 3.0
                                   + r.usage.output_tokens / 1e6 * 15.0, 5))
                    cards._sb("POST", "analyses", headers_extra=h2, json={
                        "call_id": rq_["custom_id"], "model": analyze.MODEL, "payload": pay})
                except Exception as ex:
                    log(f"  [warn] análise sync {rq_['custom_id']}: {str(ex)[:80]}")
        log(f"análises novas: {len(analyzed)} · ${_spend['usd']:.2f}")

    # ---- fase 2: linhas do tempo + sínteses via Batch ----
    log(f"== montando {n_synth} linhas do tempo ==")
    hoje = f"{dt.datetime.now():%Y-%m-%d}"
    sreqs = []
    for n, (cid, info) in enumerate(enriched.items(), 1):
        try:
            tl = lead_state.build_timeline(cid)
            sreqs.append({"custom_id": cid,
                          "params": {"model": analyze.MODEL, "max_tokens": 6000,
                                     "system": [{"type": "text",
                                                 "text": lead_state.SYSTEM.replace("{HOJE}", hoje),
                                                 "cache_control": {"type": "ephemeral"}}],
                                     "output_config": {"format": {"type": "json_schema",
                                                                  "schema": lead_state.STATE_SCHEMA}},
                                     "messages": [{"role": "user", "content":
                                                   f"LINHA DO TEMPO DO LEAD:\n{json.dumps(tl, ensure_ascii=False)}"}]}})
        except Exception as ex:
            log(f"  [warn] timeline {cid}: {str(ex)[:60]}")
        if n % 100 == 0:
            log(f"  timelines {n}/{n_synth}")
    log(f"batch de sínteses: {len(sreqs)} reqs")
    states = {}
    if sreqs:
        batch = client.messages.batches.create(requests=sreqs)
        log(f"batch estados {batch.id} — aguardando…")
        while True:
            b = client.messages.batches.retrieve(batch.id)
            log(f"  {b.processing_status} · {b.request_counts}")
            if b.processing_status == "ended":
                break
            time.sleep(60)
        it, ot, nerr = 0, 0, 0
        for entry in client.messages.batches.results(batch.id):
            if entry.result.type != "succeeded":
                nerr += 1
                continue
            msg = entry.result.message
            it += msg.usage.input_tokens
            ot += msg.usage.output_tokens
            try:
                st = json.loads(next(bl.text for bl in msg.content if bl.type == "text"))
            except StopIteration:
                nerr += 1
                continue
            st["_computed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            states[entry.custom_id] = st
            cards._sb("POST", "lead_states?on_conflict=contact_id", headers_extra=h2,
                      json={"contact_id": entry.custom_id, "state": st,
                            "situacao": st.get("situacao"),
                            "computed_at": st["_computed_at"].replace("+00:00", "Z")})
        add_cost("mvp-batch-estados", "anthropic", f"{analyze.MODEL} (batch)",
                 it + ot, round((it / 1e6 * 3.0 + ot / 1e6 * 15.0) * 0.5, 3))
        log(f"estados sintetizados: {len(states)} ({nerr} erros) · ${_spend['usd']:.2f}")

    # ---- fase 3: aplicar estados + rescore + fila ----
    log("== aplicando estados + rescore ==")
    dist = {}
    for n, (cid, st) in enumerate(states.items(), 1):
        try:
            lead_state.apply_state(cid, st)
            dist[st.get("situacao") or "?"] = dist.get(st.get("situacao") or "?", 0) + 1
        except Exception as ex:
            log(f"  [warn] apply {cid}: {str(ex)[:60]}")
        if n % 100 == 0:
            log(f"  aplicados {n}/{len(states)}")
    log(f"situações: {dist}")
    for n, (cid, info) in enumerate(enriched.items(), 1):
        try:
            score_engine.compute_for(cid, opp=info.get("opp"), contact=info["contact"],
                                     msgs=info["msgs"])
        except Exception:
            pass
        if n % 100 == 0:
            log(f"  rescore {n}/{n_synth}")
    stats = cards.sync_all()
    log(f"fila: {stats}")
    json.dump({"synth": len(states), "situacoes": dist,
               "spend_usd": round(_spend["usd"], 2),
               "finished": dt.datetime.now(dt.timezone.utc).isoformat()},
              open(OUT / "mvp_result.json", "w"), indent=2)
    log(f"== FIM: ${_spend['usd']:.2f} / teto ${CAP_USD} ==")


if __name__ == "__main__":
    main()
