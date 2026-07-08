"""
Runner do cérebro (M2) — ciclo de 5 min via GitHub Actions.
DRY-RUN por padrão: até o GATE G2 ser aprovado, nenhuma escrita sai — as intenções
vão para out/write_log.jsonl (dry_run=true) e para o relatório do ciclo.

Fluxo por ciclo:
  1. carregar estado (última varredura) — Supabase se configurado, senão out/state.json
  2. varrer conversas recentes por mensagens novas
  3. TYPE_CALL nova: baixar áudio → Deepgram → análise Claude → regras 2.3
  4. SMS outbound com link Urable → regra de quote
  5. gravar estado + log
"""
import json
import sys
import os
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ghl  # noqa: E402
import score  # noqa: E402
from brain import rules, transcribe, writer  # noqa: E402

STATE_PATH = Path(__file__).resolve().parent.parent.parent / "out" / "state.json"
LOC = ghl.LOCATION_ID


def _supabase():
    import os
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url, {"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"}
    return None, None


DEFAULT_STATE = {"last_scan_iso": None, "processed_call_ids": [], "capi_qualified_sent": []}


def load_state():
    import requests
    url, h = _supabase()
    if url:
        try:
            r = requests.get(f"{url}/rest/v1/worker_state?key=eq.brain&select=value",
                             headers=h, timeout=15)
            rows = r.json() if r.status_code == 200 else []
            if rows:
                return rows[0]["value"]
        except Exception as e:
            print(f"  [warn] estado Supabase indisponível ({e}); usando local")
    if STATE_PATH.exists():
        return json.load(open(STATE_PATH))
    st = dict(DEFAULT_STATE)
    st["last_scan_iso"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)).isoformat()
    return st


def save_state(st):
    import requests
    STATE_PATH.parent.mkdir(exist_ok=True)
    json.dump(st, open(STATE_PATH, "w"), indent=2)   # backup local sempre
    url, h = _supabase()
    if url:
        try:
            requests.post(f"{url}/rest/v1/worker_state",
                          headers={**h, "Prefer": "resolution=merge-duplicates"},
                          json={"key": "brain", "value": st}, timeout=15)
        except Exception as e:
            print(f"  [warn] não gravou estado no Supabase: {e}")


def recent_conversations(limit=100):
    """Conversas mais recentes da location (ordenadas por última mensagem)."""
    r = ghl.get("/conversations/search",
                {"locationId": LOC, "limit": limit, "sortBy": "last_message_date", "sort": "desc"})
    if r.status_code != 200:
        return []
    return r.json().get("conversations", [])


def opportunity_for_contact(contact_id):
    r = ghl.get("/opportunities/search", {"location_id": LOC, "contact_id": contact_id, "limit": 5})
    if r.status_code != 200:
        return None
    opps = [o for o in r.json().get("opportunities", []) if o.get("status") == "open"]
    return opps[0] if opps else (r.json().get("opportunities") or [None])[0]


def apply_actions(actions):
    """Executa (ou dry-run-loga) a lista de ações vinda das regras."""
    for func_name, kwargs, motivo in actions:
        fn = getattr(writer, func_name)
        fn(**kwargs, gate="G2", motivo=motivo)


def is_test_contact(contact):
    """Tag teste-interno: fora de score write-back, CAPI, relatórios, comissões."""
    return "teste-interno" in (contact.get("tags") or [])


def register_test_contact(contact_id):
    """Guarda os ids de teste no config p/ o botão 'limpar dados de teste' do painel."""
    import requests
    url, h = _supabase()
    if not url:
        return
    try:
        r = requests.get(f"{url}/rest/v1/config?key=eq.test_contact_ids&select=value",
                         headers=h, timeout=10)
        ids = set((r.json() or [{}])[0].get("value", []) if r.json() else [])
        if contact_id not in ids:
            ids.add(contact_id)
            requests.post(f"{url}/rest/v1/config",
                          headers={**h, "Prefer": "resolution=merge-duplicates"},
                          json={"key": "test_contact_ids", "value": sorted(ids)}, timeout=10)
    except Exception:
        pass


def send_capi(event_name, contact_id, opportunity_id, value=None):
    """Evento CAPI p/ Meta (QualifiedLead / AppointmentBooked / Purchase).
    CAPI está LIVE desde 2026-07-07 (pedido do Rafael) — independe do dry-run das
    escritas GHL. event_id determinístico protege contra duplicidade."""
    from brain import capi
    cr = ghl.get(f"/contacts/{contact_id}")
    contact = cr.json().get("contact", {}) if cr.status_code == 200 else {}
    if is_test_contact(contact):
        register_test_contact(contact_id)
        print(f"  [teste-interno] CAPI {event_name} PULADO p/ contato de teste")
        return
    try:
        capi.send_event(event_name, contact, opportunity_id, value=value)
    except Exception as e:
        print(f"  [warn] CAPI {event_name} falhou: {e}")


SCORE_CF = {"score": "OKX1hfCHkn2FWZud9lj1", "breakdown": "b7HYU3fGCvWTs8lTHVXS"}


def refresh_score(contact_id, opp, analysis=None):
    """SCORE EM TEMPO REAL — A12-a: delega ao motor v3 (score_engine), que junta
    veículo (manual/CF/análise), análise SALVA no Supabase (não só a do ciclo),
    todas as conversas, quote enviada e visita à loja. Persistência no Supabase é
    livre; o CF no GHL respeita o gate global (G2/G-SCORE-FIX)."""
    import requests
    try:
        cr = ghl.get(f"/contacts/{contact_id}")
        contact_obj = cr.json().get("contact", {}) if cr.status_code == 200 else {}
        if is_test_contact(contact_obj):
            register_test_contact(contact_id)
            print(f"  [teste-interno] score write-back PULADO p/ contato de teste")
            return None
        from brain import score_engine
        s = score_engine.compute_for(contact_id, opp=opp, analysis=analysis,
                                     contact=contact_obj)
        if opp and not writer.DRY_RUN:
            payload = {"customFields": [
                {"id": SCORE_CF["score"], "field_value": s["known"]},
                {"id": SCORE_CF["breakdown"], "field_value": s["breakdown"]},
            ]}
            requests.put(f"{ghl.BASE}/opportunities/{opp['id']}",
                         headers={**ghl.H, "Content-Type": "application/json"},
                         json=payload, timeout=30)
        print(f"  score v3: {(opp or {}).get('name')!r} -> {s['known']}/{s['max_possible']} "
              f"[{s['badge']}] (GHL write={'on' if not writer.DRY_RUN else 'gated'})")
        return s
    except Exception as e:
        print(f"  [warn] refresh_score falhou: {e}")
        return None


def _log_cost(call_id, provider, model, units, est_usd):
    """A8: cada centavo de IA registrado (cost_log)."""
    import requests
    url, h = _supabase()
    if not url:
        return
    try:
        requests.post(f"{url}/rest/v1/cost_log", headers=h, json={
            "call_id": call_id, "provider": provider, "model": model,
            "units": units, "est_usd": est_usd}, timeout=10)
    except Exception:
        pass


def persist_call(msg, meta, opp, analysis, transcript_text=None):
    """Grava call + transcript + análise no Supabase (alimenta Advice e KPIs)."""
    import requests
    url, h = _supabase()
    if not url:
        return
    h2 = {**h, "Prefer": "resolution=merge-duplicates"}
    try:
        requests.post(f"{url}/rest/v1/calls", headers=h2, json={
            "id": msg["id"], "contact_id": msg["contactId"],
            "conversation_id": msg.get("conversationId"),
            "opportunity_id": (opp or {}).get("id"),
            "direction": msg.get("direction"), "status": msg.get("status"),
            "duration_sec": meta.get("duration"), "dialed_number": msg.get("to"),
            "user_id": msg.get("userId"), "called_at": msg.get("dateAdded"),
            "recording_downloaded": analysis is not None,
        }, timeout=15)
        if transcript_text:
            requests.post(f"{url}/rest/v1/transcripts", headers=h2, json={
                "call_id": msg["id"], "full_text": transcript_text,
            }, timeout=15)
        if analysis:
            requests.post(f"{url}/rest/v1/analyses", headers=h2, json={
                "call_id": msg["id"], "model": "claude-sonnet-5",
                "payload": analysis,
            }, timeout=15)
    except Exception as e:
        print(f"  [warn] persistência da call falhou: {e}")


def post_analysis_signals(msg, opp, analysis):
    """A11.1 (observação de pergunta técnica) + A12-c (visita provável) +
    A9.1 (validação de ballpark falado vs. tabela/starting)."""
    from brain import cards as _c
    cid = msg["contactId"]
    try:
        from brain import pricing
        v = (analysis or {}).get("vehicle") or {}
        veh_text = f"{v.get('make', '')} {v.get('model', '')} {(opp or {}).get('name', '')}"
        n_alerts = pricing.check_ballparks(analysis, cid, msg["id"], vehicle_text=veh_text)
        if n_alerts:
            print(f"  [price-alert] {n_alerts} divergência(s) de preço falado")
    except Exception as e:
        print(f"  [warn] ballpark check: {e}")
    pt = (analysis or {}).get("pergunta_tecnica") or {}
    if pt.get("houve"):
        dup = _c._sb("GET", f"technical_observations?call_id=eq.{msg['id']}&select=id&limit=1")
        if not dup:
            _c._sb("POST", "technical_observations", json={
                "call_id": msg["id"], "contact_id": cid,
                "contact_name": (opp or {}).get("name"),
                "pergunta": pt.get("pergunta"), "categoria": pt.get("categoria"),
                "transferida": pt.get("transferida"),
                "resposta_improvisada": pt.get("resposta_improvisada"),
                "como_tratou": ("transferida ao vivo" if pt.get("transferida")
                                else "callback prometido" if pt.get("prometeu_callback")
                                else "respondida na hora"),
                "promised_callback": pt.get("prometeu_callback", False)})
            # EXCEÇÃO do modo observação: callback PROMETIDO ao cliente não espera
            # calibragem → task pro Rafael (via writer: executa pós-G2, logada antes)
            if pt.get("prometeu_callback"):
                due = (dt.datetime.now(dt.timezone.utc)
                       + dt.timedelta(hours=4)).isoformat()
                writer.create_task(
                    cid, f"Callback técnico — {(opp or {}).get('name') or 'lead'}: "
                         f"\"{(pt.get('pergunta') or '')[:80]}\"",
                    "Pergunta técnica com callback prometido na call. Prazo: mesmo dia.",
                    due, rules.RAFAEL_USER_ID, gate="G2",
                    motivo="A11: callback técnico prometido ao cliente")
    cp = (analysis or {}).get("cupom_oferecido") or {}
    if cp.get("houve"):
        dup = _c._sb("GET", f"coupons?call_id=eq.{msg['id']}&select=id&limit=1")
        if not dup:
            _c._sb("POST", "coupons", json={
                "contact_id": cid, "call_id": msg["id"], "source": "call",
                "contexto": (cp.get("contexto") or "")[:300],
                "offered_by": "detectado na transcrição"})
            print(f"  [cupom-$200] registrado p/ {cid}: {str(cp.get('contexto'))[:50]!r}")
    vl = (analysis or {}).get("visita_loja") or {}
    if vl.get("ja_visitou_mencionado"):
        fl = _c._sb("GET", f"lead_flags?contact_id=eq.{cid}&select=visited_store,visit_probable") or []
        if not (fl and fl[0].get("visited_store")):
            _c._sb("POST", "lead_flags?on_conflict=contact_id",
                   headers_extra={"Prefer": "resolution=merge-duplicates"},
                   json={"contact_id": cid, "visit_probable": {
                       "evidencia": vl.get("evidencia"), "call_id": msg["id"],
                       "detected_at": dt.datetime.now(dt.timezone.utc).isoformat()}})
            print(f"  [visita_provavel] {cid}: {str(vl.get('evidencia'))[:60]!r}")


def process_call(msg, st):
    call_id = msg["id"]
    if call_id in st["processed_call_ids"]:
        return
    meta = (msg.get("meta") or {}).get("call") or {}
    direction = msg.get("direction")
    answered = bool(meta.get("duration"))
    opp = opportunity_for_contact(msg["contactId"])

    analysis = None
    transcript_text = None
    if answered and meta.get("duration", 0) > 20:   # A8: skip <20s
        try:
            audio = transcribe.download_recording(call_id)
            if not audio:
                # gravação ainda indisponível → retry (até 3 ciclos) + flag
                att = st.setdefault("rec_attempts", {})
                att[call_id] = att.get(call_id, 0) + 1
                if att[call_id] < 3:
                    print(f"  [retry] gravação indisponível ({att[call_id]}/3): {call_id}")
                    return None  # NÃO marca processado → tenta de novo no próximo ciclo
                print(f"  [flag] gravação nunca disponível p/ {call_id}")
            else:
                t = transcribe.transcribe(audio)
                _log_cost(call_id, "deepgram", "nova-2",
                          round(meta["duration"] / 60, 2),
                          round(meta["duration"] / 60 * 0.0043, 5))
                transcript_text = transcribe.diarized_as_text(t["diarized"]) or t["full_text"]
                from brain import analyze
                analysis = analyze.analyze_call(
                    transcript_text,
                    {"direction": direction, "duration_sec": meta.get("duration"),
                     "status": msg.get("status")})
                m = analysis.get("_meta", {})
                if m:
                    _log_cost(call_id, "anthropic", m["model"],
                              m["in_tokens"] + m["out_tokens"], m["est_usd"])
                # A12-d: crítico Haiku valida o advice ANTES de qualquer exibição
                from brain import advice_gate
                analysis, _, _ = advice_gate.gate_analysis(
                    analysis, transcript_text, call_id=call_id,
                    contact_id=msg["contactId"])
                # (decisão do Rafael: NÃO marcar espanhol automaticamente —
                #  ele/Eugene tentam em inglês primeiro e marcam manual no painel)
        except Exception as e:
            # chave faltando / falha de transcrição não pode derrubar o ciclo
            print(f"  [warn] análise da call {call_id} pulada: {e}")

    actions = []
    if opp:
        if direction == "inbound":
            actions += rules.on_inbound_call(opp)
            if not answered:  # regra do Rafael: inbound perdida = alerta duplo urgente
                import os
                actions += rules.on_missed_inbound(
                    opp, msg["contactId"], opp.get("name") or "lead",
                    called_number=msg.get("to"), lead_phone=msg.get("from"),
                    eugene_phone=os.environ.get("EUGENE_PHONE"),
                    rafael_phone=os.environ.get("RAFAEL_PHONE"))
                # card VERMELHO no painel (Supabase — imediato, sem gate)
                from brain import cards as _cards
                origem = " (Google Ads)" if msg.get("to") == rules.GOOGLE_ADS_NUMBER else ""
                _cards.create_card(
                    "callback", 1, msg["contactId"],
                    f"📞 MISSED CALL{origem}: {opp.get('name') or 'lead'}",
                    f"Called from {msg.get('from')} and nobody answered. Call back NOW — "
                    "first one to call handles it.",
                    {"passos": ["Call back immediately",
                                "No answer: text 'saw your call, how can I help?'",
                                "Log the outcome in GHL"]},
                    opportunity_id=opp.get("id"))
        elif not answered:
            actions += rules.on_no_answer(opp)
    apply_actions(actions)
    persist_call(msg, meta, opp, analysis, transcript_text)
    if analysis:
        post_analysis_signals(msg, opp, analysis)  # A11 observação + A12-c visita provável
    refresh_score(msg["contactId"], opp, analysis)  # score em tempo real
    # A9: interesse vivo — call analisada atualiza a trilha + o card
    if analysis and analysis.get("servico_interesse"):
        import requests
        url, h = _supabase()
        if url:
            try:
                requests.post(f"{url}/rest/v1/interest_history", headers=h, json={
                    "contact_id": msg["contactId"],
                    "interest": analysis["servico_interesse"],
                    "source": "call", "set_by": "brain"}, timeout=10)
                # espelha no(s) card(s) abertos (Supabase é livre)
                from brain import cards as _c
                for c in (_c._sb("GET", f"cards?status=eq.open&contact_id=eq.{msg['contactId']}&select=id,how") or []):
                    how = dict(c.get("how") or {})
                    how["interest"] = {"value": analysis["servico_interesse"],
                                       "source": "call",
                                       "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")}
                    _c._sb("PATCH", f"cards?id=eq.{c['id']}", json={"how": how})
                # CF no GHL: manual vence; cérebro escreve só pós-G2
                if not writer.DRY_RUN:
                    import requests as rq
                    rq.put(f"{ghl.BASE}/contacts/{msg['contactId']}",
                           headers={**ghl.H, "Content-Type": "application/json"},
                           json={"customFields": [{"id": "D5TgphY9HlZMoS8wcWj1",
                                                   "field_value": analysis["servico_interesse"]}]},
                           timeout=30)
            except Exception as e:
                print(f"  [warn] interesse vivo: {e}")

    st["processed_call_ids"] = (st["processed_call_ids"] + [call_id])[-2000:]
    return analysis


def main():
    # G2 ainda não aprovado → writer.DRY_RUN permanece True (default)
    st = load_state()
    since = dt.datetime.fromisoformat(st["last_scan_iso"])
    cycle_start = dt.datetime.now(dt.timezone.utc)
    n_calls = n_quotes = 0

    for cv in recent_conversations():
        m = ghl.get(f"/conversations/{cv['id']}/messages")
        if m.status_code != 200:
            continue
        for msg in m.json().get("messages", {}).get("messages", []):
            ts = msg.get("dateAdded")
            if not ts or dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) <= since:
                continue
            if msg.get("messageType") == "TYPE_CALL":
                process_call(msg, st)
                n_calls += 1
            elif msg.get("messageType") == "TYPE_SMS" and msg.get("direction") == "outbound":
                mlink = rules.URABLE_LINK.search(msg.get("body") or "")
                if mlink:
                    opp = opportunity_for_contact(msg["contactId"])
                    if opp:
                        apply_actions(rules.on_quote_detected(opp, msg["contactId"], mlink.group(0)))
                        n_quotes += 1
            elif msg.get("messageType") == "TYPE_SMS" and msg.get("direction") == "inbound":
                # lead respondeu → engajamento mudou → score em tempo real
                key = f"sms:{msg['id']}"
                if key not in st["processed_call_ids"]:
                    opp = opportunity_for_contact(msg["contactId"])
                    refresh_score(msg["contactId"], opp)
                    st["processed_call_ids"] = (st["processed_call_ids"] + [key])[-2000:]

    # CAPI watcher: quem ENTROU em Great Cars desde o último ciclo → QualifiedLead
    # (event_id determinístico no Meta impede duplicar mesmo se reprocessar)
    sent = set(st.get("capi_qualified_sent", []))
    n_capi = 0
    gc = ghl.get("/opportunities/search",
                 {"location_id": LOC, "pipeline_id": rules.NEW_PIPELINE_ID,
                  "pipeline_stage_id": rules.STAGES["Great Cars"], "limit": 100})
    if gc.status_code == 200:
        for o in gc.json().get("opportunities", []):
            if o["id"] not in sent:
                send_capi("QualifiedLead", o["contactId"], o["id"])
                sent.add(o["id"])
                n_capi += 1
    st["capi_qualified_sent"] = list(sent)[-5000:]

    # fila do painel: gerar/fechar cards
    try:
        from brain import cards
        stats = cards.sync_all()
    except Exception as e:
        stats = {"erro": str(e)[:80]}

    # M5: pool frio (refresh semanal) + manter a fila abastecida
    try:
        from brain import cold
        cold.maybe_weekly_refresh()
        stats["cold"] = cold.top_up_queue()
    except Exception as e:
        stats["cold_erro"] = str(e)[:60]

    # snapshot do funil de HOJE p/ a vista do dono (config key stats_today)
    try:
        import requests
        url, h = _supabase()
        if url:
            today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            funil = {}
            for label, stage in (("novos", None), ("qualificados", "Great Cars"),
                                 ("quotes", "Quote Sent"), ("appointments", "Appointment Booked"),
                                 ("win", "Win"), ("hot", "HOT LEADS")):
                p = {"location_id": LOC, "pipeline_id": rules.NEW_PIPELINE_ID, "limit": 1}
                if stage:
                    p["pipeline_stage_id"] = rules.STAGES[stage]
                r = ghl.get("/opportunities/search", p)
                funil[label] = (r.json().get("meta", {}) or {}).get("total") if r.status_code == 200 else None
            requests.post(f"{url}/rest/v1/config",
                          headers={**h, "Prefer": "resolution=merge-duplicates"},
                          json={"key": "stats_today",
                                "value": {"date": today, "funil": funil,
                                          "atualizado": cycle_start.isoformat()}},
                          timeout=15)
    except Exception as e:
        print(f"  [warn] stats_today: {e}")

    st["last_scan_iso"] = cycle_start.isoformat()
    save_state(st)
    print(f"ciclo OK: {n_calls} calls novas, {n_quotes} quotes, "
          f"{n_capi} QualifiedLead p/ Meta, cards={stats} (dry_run GHL={writer.DRY_RUN})")


if __name__ == "__main__":
    main()
