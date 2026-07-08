"""
FAXINA EXECUTORA — ordem direta do Rafael no chat (08/jul/2026, noite):
"vamos limpar esses 189 hot leads que nao fazem sentido... migramos e nao servem"
+ item 8 do checklist: "FAXINA: faz a limpeza" (>90d → Lost 'no response').

Escritas no GHL autorizadas pelo dono NESTA ordem (supera o 'zero escritas' do
painel só para esta operação). Tudo vai pro out/write_log.jsonl.

Alvos:
  A) 189 opps abertas em HOT LEADS com lastStageChangeAt no lote da migração
     (2026-07-07T22h) → stage Lost + tag contato faxina-hot-migrado
  B) stages ativos parados >90 dias (critério FAXINA_DIA_ZERO) → stage Lost
     + tag contato faxina-90d-sem-resposta

Guard-rails: PROTECTED_STAGES nunca; contato com appointment futuro nunca;
teste-interno nunca. Canário de 1 lead antes do lote (verifica que nenhum
workflow manda SMS). As tags faxina-* ficam FORA do warm-up (config), senão o
updatedAt=hoje colocaria 361 leads mortos no TOPO da ração.

Uso:  python worker/faxina_executor.py canary   (só o canário)
      python worker/faxina_executor.py run      (canário + lote completo)
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
import requests  # noqa: E402
from board_sync import paged_opps, parse_ts  # noqa: E402
from brain import cards as sb  # noqa: E402
from brain import rules  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "out" / "write_log.jsonl"
LOST_ID = rules.STAGES["Lost"]
MIGRATION_HOUR = "2026-07-07T22"
TESTE = {"GIEjjPmMs3CqUCzIUWpU"}
now_utc = lambda: dt.datetime.now(dt.timezone.utc)  # noqa: E731


def wlog(action, **kw):
    entry = {"ts": now_utc().isoformat(), "action": action,
             "by": "faxina ordem Rafael chat 08/jul", **kw}
    with LOG.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _req(method, url, body, tries=4):
    """Escrita com retry/backoff p/ 429 E erros de rede (mesma política do ghl.get)."""
    last = None
    for i in range(tries):
        try:
            r = requests.request(method, url, headers=ghl.H, json=body, timeout=45)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last = e
            time.sleep(2 ** (i + 1))
            continue
        if r.status_code == 429:
            time.sleep(2 ** (i + 1))
            continue
        return r
    if last:
        raise last
    return r


def put_stage(opp_id):
    return _req("PUT", f"{ghl.BASE}/opportunities/{opp_id}",
                {"pipelineId": rules.NEW_PIPELINE_ID, "pipelineStageId": LOST_ID})


def add_tag(cid, tag):
    r = _req("POST", f"{ghl.BASE}/contacts/{cid}/tags", {"tags": [tag]})
    return r.status_code in (200, 201)


def appt_contacts():
    cids = set()
    start = now_utc() - dt.timedelta(hours=6)
    for cal_id in sb.CALENDARS.values():
        r = ghl.get("/calendars/events", {"locationId": ghl.LOCATION_ID,
            "calendarId": cal_id,
            "startTime": int(start.timestamp() * 1000),
            "endTime": int((start + dt.timedelta(days=90)).timestamp() * 1000)})
        if r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            if e.get("appointmentStatus") not in ("cancelled", "invalid", "noshow") \
                    and e.get("contactId"):
                cids.add(e["contactId"])
    return cids


def alvo_a():
    """HOT LEADS do lote migrado (ontem 22h UTC)."""
    hot = [o for o in paged_opps(rules.STAGES["HOT LEADS"]) if o.get("status") == "open"]
    return [o for o in hot if (o.get("lastStageChangeAt") or "").startswith(MIGRATION_HOUR)]


def alvo_b():
    """Stages ativos parados >90 dias (critério FAXINA_DIA_ZERO)."""
    stages_ativos = ["New Lead", "HOT LEADS", "Contact 1 (AM)", "Contact 1 (PM)",
                     "Contact 2 (AM)", "Contact 2 (PM)", "Contact 3 (AM)",
                     "Contact 3 (PM)", "Follow Up"]
    out = []
    for stage in stages_ativos:
        for o in paged_opps(rules.STAGES[stage]):
            if o.get("status") != "open":
                continue
            ts = parse_ts(o.get("lastStageChangeAt") or o.get("updatedAt") or o.get("createdAt"))
            if ts and (now_utc() - ts).days > 90:
                out.append((stage, o))
    return out


def mover(opp, stage_from, tag, skip):
    cid = opp["contactId"]
    if cid in skip:
        return "skipped (guard)"
    r = put_stage(opp["id"])
    if r.status_code not in (200, 201):
        wlog("move_stage_FAIL", opp_id=opp["id"], contact_id=cid,
             http=r.status_code, body=r.text[:150])
        return f"FAIL {r.status_code}"
    add_tag(cid, tag)
    wlog("move_stage", opp_id=opp["id"], contact_id=cid, nome=opp.get("name"),
         de=stage_from, para="Lost", tag=tag)
    return "ok"


def fechar_cards_board(cids, motivo):
    """Fecha no board os cards de stage dos contatos limpos (espelho instantâneo)."""
    n = 0
    for chunk in [list(cids)[i:i + 40] for i in range(0, len(cids), 40)]:
        ids = ",".join(chunk)
        rows = sb._sb("PATCH",
                      f"board_cards?status=eq.open&contact_id=in.({ids})"
                      "&kind=in.(hot,new_lead,pipeline,followup_notask,quote_notask)",
                      json={"status": "resolved", "resolved_by": motivo,
                            "resolved_at": now_utc().isoformat()}) or []
        n += len(rows)
    return n


def canary(skip):
    alvos = alvo_a()
    if not alvos:
        print("nada em HOT LEADS pra limpar")
        return None
    # canário: prefere o contato chamado SCAM (dano zero por definição)
    c = next((o for o in alvos if (o.get("name") or "").strip().upper() == "SCAM"), alvos[0])
    print(f"CANÁRIO: {c.get('name')} opp={c['id']} contact={c['contactId']}")
    res = mover(c, "HOT LEADS", "faxina-hot-migrado", skip)
    print("  move:", res)
    if res != "ok":
        return False
    time.sleep(75)  # janela pra qualquer workflow disparar
    cs = ghl.get("/conversations/search", {"locationId": ghl.LOCATION_ID,
                                           "contactId": c["contactId"]})
    sms_apos = []
    for cv in (cs.json().get("conversations", []) if cs.status_code == 200 else []):
        mj = ghl.get(f"/conversations/{cv['id']}/messages")
        msgs = (mj.json().get("messages", {}) or {}).get("messages", []) if mj.status_code == 200 else []
        lim = (now_utc() - dt.timedelta(minutes=3)).isoformat()
        sms_apos += [m for m in msgs if m.get("dateAdded", "") > lim
                     and m.get("direction") == "outbound"
                     and m.get("messageType") in ("TYPE_SMS", "TYPE_EMAIL")]
    r2 = ghl.get("/opportunities/search", {"location_id": ghl.LOCATION_ID,
                                           "contact_id": c["contactId"], "limit": 5})
    stages_now = [rules.STAGE_BY_ID.get(o.get("pipelineStageId"))
                  for o in (r2.json().get("opportunities", []) if r2.status_code == 200 else [])]
    print(f"  stage agora: {stages_now} · SMS/email disparados: {len(sms_apos)}")
    if sms_apos:
        print("  ⚠️ WORKFLOW MANDOU MENSAGEM — ABORTAR LOTE:",
              [(m.get("source"), (m.get("body") or "")[:60]) for m in sms_apos])
        return False
    return "Lost" in stages_now and not sms_apos


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "canary"
    skip = appt_contacts() | TESTE
    print(f"guard-rails: {len(skip)} contatos protegidos (appointments + teste)")

    ok = canary(skip)
    if ok is None:
        return
    if not ok:
        print("CANÁRIO FALHOU — lote NÃO executado.")
        sys.exit(1)
    print("canário limpo ✔")
    if modo != "run":
        return

    # ---- lote A: HOT LEADS migrados ----
    a = alvo_a()
    print(f"lote A (hot migrados restantes): {len(a)}")
    ra = {"ok": 0, "fail": 0, "skip": 0}
    cids_a = set()
    for o in a:
        res = mover(o, "HOT LEADS", "faxina-hot-migrado", skip)
        ra["ok" if res == "ok" else "skip" if "skip" in res else "fail"] += 1
        if res == "ok":
            cids_a.add(o["contactId"])
        time.sleep(0.15)
    print("  A:", ra)

    # ---- lote B: >90d parados ----
    b = alvo_b()
    print(f"lote B (>90d parados): {len(b)}")
    rb = {"ok": 0, "fail": 0, "skip": 0}
    cids_b = set()
    for stage, o in b:
        res = mover(o, stage, "faxina-90d-sem-resposta", skip)
        rb["ok" if res == "ok" else "skip" if "skip" in res else "fail"] += 1
        if res == "ok":
            cids_b.add(o["contactId"])
        time.sleep(0.15)
    print("  B:", rb)

    n1 = fechar_cards_board(cids_a, "faxina: legacy migrado → Lost (ordem do Rafael)")
    n2 = fechar_cards_board(cids_b, "faxina: >90d sem resposta → Lost (ordem do Rafael)")
    print(f"cards fechados no board: A={n1} B={n2}")
    # cold_excluded: exclusão O(1) do warm-up (as tags são o registro no GHL;
    # o flag evita 361 contact_brief por ciclo só pra descobrir a tag)
    for cid in cids_a | cids_b:
        sb._sb("POST", "lead_flags?on_conflict=contact_id",
               json={"contact_id": cid, "cold_excluded": True},
               headers_extra={"Prefer": "resolution=merge-duplicates"})
    wlog("faxina_resumo", lote_a=ra, lote_b=rb, cards_fechados=n1 + n2)
    print("FAXINA COMPLETA.")


if __name__ == "__main__":
    main()
