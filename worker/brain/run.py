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


def load_state():
    if STATE_PATH.exists():
        return json.load(open(STATE_PATH))
    return {"last_scan_iso": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)).isoformat(),
            "processed_call_ids": []}


def save_state(st):
    STATE_PATH.parent.mkdir(exist_ok=True)
    json.dump(st, open(STATE_PATH, "w"), indent=2)


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


def send_capi(event_name, contact_id, opportunity_id, value=None):
    """Evento CAPI p/ Meta (QualifiedLead / AppointmentBooked / Purchase).
    Respeita o dry-run global: só envia de verdade quando G2 estiver ativo."""
    from brain import capi
    if writer.DRY_RUN:
        capi._log({"motivo": f"CAPI {event_name} opp={opportunity_id}",
                   "status": "DRY_RUN", "url": "graph.facebook.com"})
        return
    cr = ghl.get(f"/contacts/{contact_id}")
    contact = cr.json().get("contact", {}) if cr.status_code == 200 else {}
    try:
        capi.send_event(event_name, contact, opportunity_id, value=value)
    except Exception as e:
        print(f"  [warn] CAPI {event_name} falhou: {e}")


def process_call(msg, st):
    call_id = msg["id"]
    if call_id in st["processed_call_ids"]:
        return
    meta = (msg.get("meta") or {}).get("call") or {}
    direction = msg.get("direction")
    answered = bool(meta.get("duration"))
    opp = opportunity_for_contact(msg["contactId"])

    analysis = None
    if answered and meta.get("duration", 0) > 20:
        try:
            audio = transcribe.download_recording(call_id)
            if audio:
                t = transcribe.transcribe(audio)
                from brain import analyze
                analysis = analyze.analyze_call(
                    transcribe.diarized_as_text(t["diarized"]) or t["full_text"],
                    {"direction": direction, "duration_sec": meta.get("duration"),
                     "status": msg.get("status")})
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
        elif not answered:
            actions += rules.on_no_answer(opp)
    apply_actions(actions)

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

    st["last_scan_iso"] = cycle_start.isoformat()
    save_state(st)
    print(f"ciclo OK: {n_calls} calls novas, {n_quotes} quotes detectadas "
          f"(dry_run={writer.DRY_RUN})")


if __name__ == "__main__":
    main()
