"""
PAINEL DIÁRIO — motor-espelho (missão definitiva 2026-07-08, docs/PAINEL_DIARIO.md).

ESPELHA o GHL: zero IA, zero transcrição, zero escrita no GHL (somente leitura +
Supabase). Roda no cron de 5 min. Fonte única: metadados de calls/mensagens/stages/
tasks/appointments/notas.

Colunas (janelas do PLANO_GERAL §A):
  1 Return·Reply·Hot (3d) · 2 New Leads (7d) · 3 Tasks & Urable (7d/14d) ·
  4 Pipeline follow-ups (30d) · 5 Appointments 2d (to_confirm/confirmed+nota) ·
  6 Warm up (ração 20/dia + reabastecimento até a meta de 100 caber no dia)

REGRA DA RESOLUÇÃO: discagem não fecha card; resolução fecha (appointment · task ·
Urable+Quote Sent · Lost; não atendida → stage avançado; warm-up → SMS de reativação
ou Lost terminal). Call finalizada >15min sem resolução → card vermelho SEM RESOLUÇÃO
(por autor). Tentativa VÁLIDA: call do usuário atendida OU ≥25s + SMS manual DELE
≤10min. Comissões: 5 casos do Rafael (created_by / confirmação ativa em 48h).
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfgmod  # noqa: E402

cfgmod.load()
import ghl  # noqa: E402
from brain import cards as sb  # noqa: E402  (usamos só o _sb — cliente Supabase)
from brain import rules  # noqa: E402

ET = ZoneInfo("America/New_York")
URABLE = re.compile(r"go\.urable\.com/\S+", re.I)

DEFAULT_CFG = {
    "eugene_user_id": "EbVhbGHnGfuvbQurQoga",
    "rafael_user_id": "7dYD2aALTReBpvw0YYCM",
    # conta antiga do Rafael no mobile app (userId deletado; provado no caso Jamile)
    "rafael_aliases": ["AiqssnKwfohnWd7KBead"],
    "goal_calls": 100,
    "valid_min_sec": 25, "valid_sms_window_min": 10,
    "resolution_min": 15,
    "checkpoint": "13:00",
    "windows": {"col1_days": 3, "col2_days": 7, "task_overdue_days": 7,
                "urable_days": 14, "pipeline_days": 30, "stalled_days": 30},
    "ration": 20,
    # Warm up = casa de TODO o passivo recuperável (regra Rafael 08/jul noite).
    # Fora pra sempre SÓ quem foi dado como não interessado / número inválido
    # (dispositions). Os "no response" (incl. faxina) moram no FUNDO da fila.
    "warmup_excluded_tags": ["lost-invalid-number", "lost-not-interested"],
    "confirm_window_h": 48,
    "confirm_mode": "either",   # sms OU status confirmed
    "tiers": {"t1": 30, "t2": 35, "t3": 40, "rate1": 10, "rate2": 20,
              "bonus": 50, "cap": 600},
    # respostas que NÃO exigem ação (regra Greg/Coleen 2026-07-08) — string-match, sem IA
    "no_action_replies": ["thank you", "thanks", "thank u", "ty!", "ok", "okay", "okk",
                          "sounds good", "perfect", "great", "got it", "no worries",
                          "misdial", "miss dial", "wrong number", "by accident",
                          "dialed by accident", "no thanks", "all set", "👍", "🙏", "❤️"],
}


def no_action_reply(cfg, body):
    """Cortesia/encerramento: mensagem curta que casa com a lista → nenhuma ação."""
    t = (body or "").strip().lower()
    if not t or len(t) > 60:
        return False
    return any(p in t for p in cfg.get("no_action_replies", []))


def has_upcoming_appt(cid):
    """Appointment futuro (não cancelado) → o lead vive na coluna 5, não na 1."""
    r = ghl.get(f"/contacts/{cid}/appointments")
    if r.status_code != 200:
        return False
    lim = now_utc() - dt.timedelta(hours=3)
    for e in r.json().get("events", []):
        st = parse_ts(str(e.get("startTime")))
        if st and st > lim and e.get("appointmentStatus") not in ("cancelled", "invalid", "noshow"):
            return True
    return False

CLOSES = {
    "missed_inbound": "Closes when: return call made → then one resolution "
                      "(appointment · task · estimate+stage · Lost). Unanswered: next stage.",
    "sms_reply": "Closes when: reply sent.",
    "hot": "Closes when: call made → one resolution (appointment · task · "
           "estimate+stage · Lost). Unanswered: next stage.",
    "new_lead": "Closes when: call made → appointment · task · estimate+stage · Lost. "
                "Unanswered: move to Contact 1.",
    "task": "Closes when: task completed in GHL after the call + resolution.",
    "urable": "Closes when: call/SMS made → resolution (appointment · new task · Lost).",
    "pipeline": "Closes when: call made → resolution. Unanswered: next stage. "
                "2 stage moves today = done until tomorrow.",
    "appt_confirm": "Closes when: confirmation SMS sent OR status \"confirmed\" in GHL.",
    "warmup": "Closes when: call made → resolution; unanswered → reactivation SMS sent "
              "OR Lost terminal.",
    "followup": "BLUE — Follow Up with today's task. Closes when: the task is completed "
                "in GHL (after the call → one resolution) OR the stage moves.",
    "quote_task": "GREEN — Quote Sent with today's task: highest priority call. Closes "
                  "when: the task is completed OR the stage moves.",
    "followup_notask": "RED FLAG — in Follow Up with NO task. Create a follow-up task "
                       "with a date OR move to another stage. Closes when either happens.",
    "quote_notask": "RED FLAG — quote sent with NO follow-up task. Create the task so "
                    "you know when to call back. Closes when the task exists.",
}
CALL_KINDS = {"missed_inbound", "hot", "new_lead", "task", "urable", "pipeline",
              "warmup", "followup", "quote_task"}
# Regra Peter (report 08/jul): appointment futuro vence QUALQUER card de prioridade
# de contato — o lead vive na coluna 5. Tasks explícitas do GHL ficam de fora
# (podem ser preparação da própria visita).
APPT_WINS_KINDS = {"hot", "new_lead", "pipeline", "missed_inbound", "sms_reply",
                   "urable", "warmup", "followup_notask", "quote_notask",
                   "uncategorized"}

# FILA DE COLD CALLS (regra Rafael 08/jul): warm-up ordenado por importância —
# 1º no-show (reagendar) · 2º melhor/mais novo carro (mesmo sem resposta) · 3º resto.
# Ranking de carro determinístico, zero IA: exótico > premium > comum; ano novo > velho.
LUX_MAKES = ("ferrari", "lamborghini", "mclaren", "rolls royce", "rolls-royce",
             "bentley", "aston martin", "porsche", "maserati", "bugatti", "lotus")
PREMIUM_MAKES = ("mercedes", "benz", "bmw", "audi", "tesla", "corvette", "cadillac",
                 "escalade", "land rover", "range rover", "lexus", "rivian", "gmc",
                 "mustang", "camaro", "dodge", "ram trx", "jeep", "harley", "m2", "m3",
                 "m4", "m5", "amg")


def veh_rank(veh):
    """(tier_carro, ano): 2=exótico · 1=premium · 0=comum/sem carro."""
    t = (veh or "").lower()
    if not t:
        return 0, 0
    m = re.search(r"\b(19|20)\d{2}\b", t)
    yr = int(m.group()) if m else 0
    tier = 2 if any(mk in t for mk in LUX_MAKES) else \
        1 if any(mk in t for mk in PREMIUM_MAKES) else 0
    return tier, yr
# Regra Rafael 2026-07-08: Contact 1/2/3 = coluna 4 (mais novos primeiro; 2 moves/dia
# = completo por hoje). Follow Up = coluna 7, AMARRADO a task (sem task = vermelho).
# Regra Rafael (report 09/jul): Great Cars = NEW LEAD (carro premium/qualificado) →
# coluna New Leads, chamado PRIMEIRO. Grupo "great_car" prioriza + badge; a tag
# "great cars" persiste a prioridade quando o lead avança pro pipeline.
STAGE_COLS = {"HOT LEADS": (1, "hot"), "New Lead": (2, "new_lead"),
              "Great Cars": (2, "new_lead"),
              "Contact 1 (AM)": (4, "pipeline"), "Contact 1 (PM)": (4, "pipeline"),
              "Contact 2 (AM)": (4, "pipeline"), "Contact 2 (PM)": (4, "pipeline"),
              "Contact 3 (AM)": (4, "pipeline"), "Contact 3 (PM)": (4, "pipeline")}
GREAT_CARS_TAG = "great cars"


def is_great_car(stage, brief):
    tags = {str(t).lower() for t in (brief.get("tags") or [])} if brief else set()
    return stage == "Great Cars" or GREAT_CARS_TAG in tags


def add_contact_tag(cid, tag):
    """Aplica tag no contato (write autorizado — persiste prioridade Great Cars)."""
    import requests as _rq
    try:
        _rq.post(f"{ghl.BASE}/contacts/{cid}/tags", headers=ghl.H,
                 json={"tags": [tag]}, timeout=30)
        return True
    except Exception:
        return False
STAGE_KINDS = {"hot", "new_lead", "pipeline", "followup", "quote_task",
               "followup_notask", "quote_notask"}

CF_VEH = {"make": "CiRd678lAFn854igklGR", "model": "LHwTnTb8TPz5BbJ0I2XV",
          "year": "C01IzbXlbESCLfhoHkrZ"}
CF_INTEREST = "D5TgphY9HlZMoS8wcWj1"


def log(m):
    print(f"[{dt.datetime.now():%H:%M:%S}] {m}", flush=True)


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def iso(ts):
    return ts.isoformat().replace("+00:00", "Z")


def parse_ts(s):
    if not s:
        return None
    try:
        t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if t.tzinfo is None:  # GHL às vezes manda sem fuso → assumir UTC
            t = t.replace(tzinfo=dt.timezone.utc)
        return t
    except Exception:
        return None


def load_cfg():
    rows = sb._sb("GET", "config?key=eq.board_config&select=value") or []
    cfg = dict(DEFAULT_CFG)
    if rows:
        stored = rows[0]["value"] or {}
        for k, v in stored.items():
            cfg[k] = v
    else:
        sb._sb("POST", "config?on_conflict=key",
               headers_extra={"Prefer": "resolution=merge-duplicates"},
               json={"key": "board_config", "value": cfg})
    return cfg


def user_key(cfg, user_id, source=None):
    if source == "workflow":
        return "automation"
    if user_id == cfg["eugene_user_id"]:
        return "eugene"
    if user_id == cfg["rafael_user_id"] or user_id in (cfg.get("rafael_aliases") or []):
        return "rafael"
    return "other" if user_id else ("automation" if source == "workflow" else "other")


def call_answered(cfg, status, duration):
    """TENTATIVA VÁLIDA (esforço p/ meta/comissão): status completed OU ≥25s. Call de
    3-7s conta como esforço (bug caso Jamile: duration>0 não é conexão)."""
    return (status or "").lower() == "completed" or (duration or 0) >= cfg["valid_min_sec"]


def real_conversation(cfg, duration):
    """CONVERSA DE VERDADE (p/ EXIGIR desfecho/categorização): tempo de fala ≥25s.
    'completed 0m0s' = caixa postal / desligou = NÃO houve conversa (report 09/jul:
    retornamos chamada perdida, ele não atendeu — nada a categorizar)."""
    return (duration or 0) >= cfg["valid_min_sec"]


# -------------------- coleta GHL (somente leitura) --------------------
def paged_opps(stage_id):
    out, page = [], 1
    while True:
        r = ghl.get("/opportunities/search",
                    {"location_id": ghl.LOCATION_ID, "pipeline_id": rules.NEW_PIPELINE_ID,
                     "pipeline_stage_id": stage_id, "limit": 100, "page": page})
        if r.status_code != 200:
            break
        ops = r.json().get("opportunities", [])
        out += [o for o in ops if o.get("status") == "open" or stage_id == rules.STAGES["Lost"]]
        if len(ops) < 100:
            break
        page += 1
    return out


def last_note_for(contact_id):
    """Última nota do contato (HTML limpo) — 'facilita a visualização antes da ação'."""
    r = ghl.get(f"/contacts/{contact_id}/notes")
    notes = r.json().get("notes", []) if r.status_code == 200 else []
    if not notes:
        return None
    ln = max(notes, key=lambda x: x.get("dateAdded") or "")
    body = re.sub(r"<[^>]+>", " ", ln.get("body") or "").strip()
    body = re.sub(r"\s+", " ", body)
    ts = parse_ts(ln.get("dateAdded"))
    return f"Note ({ts:%b %d}): \"{body[:220]}\"" if body else None


def contact_brief(contact_id, cache={}):
    """nome, veh, interest, phone, tags (com cache do processo)."""
    if contact_id in cache:
        return cache[contact_id]
    r = ghl.get(f"/contacts/{contact_id}")
    b = {"nome": None, "veh": None, "interest": None, "phone": None, "tags": [],
         "dnd": False}
    if r.status_code == 200:
        c = r.json().get("contact", {})
        b["nome"] = f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip() or None
        b["phone"] = c.get("phone")
        b["tags"] = c.get("tags") or []
        # DND (report 09/jul: spam com DND ativado não deve gerar card de retorno).
        # Bloqueado = DND global OU Call+SMS ambos ativos (totalmente inalcançável).
        ds = c.get("dndSettings") or {}
        call_off = (ds.get("Call") or {}).get("status") == "active"
        sms_off = (ds.get("SMS") or {}).get("status") == "active"
        b["dnd"] = bool(c.get("dnd")) or (call_off and sms_off)
        cfs = {f.get("id"): f.get("value") for f in c.get("customFields", [])}
        veh = " ".join(str(x) for x in (cfs.get(CF_VEH["year"]), cfs.get(CF_VEH["make"]),
                                        cfs.get(CF_VEH["model"])) if x)
        b["veh"] = veh or None
        b["interest"] = cfs.get(CF_INTEREST) or next(
            (str(v) for k, v in cfs.items() if isinstance(v, str)
             and any(w in str(v).lower() for w in ("ppf", "coating", "wrap", "tint"))), None)
    cache[contact_id] = b
    return b


def scan_conversations(since, max_pages=4):
    """Eventos desde `since`: calls, sms in/out (com autor), comentários internos,
    última direção por conversa."""
    calls, sms_out, sms_in, comments, conv_last = [], [], [], [], {}
    page = 1
    while page <= max_pages:
        r = ghl.get("/conversations/search",
                    {"locationId": ghl.LOCATION_ID, "limit": 100, "page": page,
                     "sortBy": "last_message_date", "sort": "desc"})
        if r.status_code != 200:
            break
        convs = r.json().get("conversations", [])
        if not convs:
            break
        stop = False
        for cv in convs:
            last_ms = cv.get("lastMessageDate")
            try:
                last_dt = dt.datetime.fromtimestamp(int(last_ms) / 1000, dt.timezone.utc)
            except Exception:
                last_dt = None
            if last_dt and last_dt < since:
                stop = True
                break
            cid = cv.get("contactId")
            if not cid:
                continue
            m = ghl.get(f"/conversations/{cv['id']}/messages")
            if m.status_code != 200:
                continue
            msgs = m.json().get("messages", {}).get("messages", [])
            for msg in msgs:
                ts = parse_ts(msg.get("dateAdded"))
                if not ts:
                    continue
                rec = {"contact_id": cid, "ts": ts, "id": msg.get("id"),
                       "user_id": msg.get("userId"), "source": msg.get("source"),
                       "body": msg.get("body") or ""}
                if msg.get("messageType") == "TYPE_CALL":
                    meta = (msg.get("meta") or {}).get("call") or {}
                    rec["direction"] = msg.get("direction")
                    rec["duration"] = meta.get("duration") or 0
                    rec["status"] = msg.get("status")
                    calls.append(rec)
                elif msg.get("messageType") == "TYPE_SMS":
                    (sms_in if msg.get("direction") == "inbound" else sms_out).append(rec)
                elif msg.get("messageType") == "TYPE_INTERNAL_COMMENT":
                    comments.append(rec)
            if msgs:
                last = max(msgs, key=lambda x: x.get("dateAdded") or "")
                conv_last[cid] = {"ts": parse_ts(last.get("dateAdded")),
                                  "type": last.get("messageType"),
                                  "direction": last.get("direction"),
                                  "body": (last.get("body") or "")[:120]}
        if stop or len(convs) < 100:
            break
        page += 1
    return calls, sms_out, sms_in, comments, conv_last


# -------------------- elegibilidade --------------------
def excluded_sets():
    """teste-interno + pos_venda/spam + Win contacts (leitura Supabase/estágios)."""
    test_ids = set()
    rows = sb._sb("GET", "config?key=eq.test_contact_ids&select=value") or []
    if rows:
        test_ids = set(rows[0]["value"] or [])
    silent = {r["contact_id"] for r in
              (sb._sb("GET", "lead_states?situacao=in.(pos_venda,spam_nao_lead)"
                             "&select=contact_id") or [])}
    return test_ids, silent


# -------------------- cards --------------------
def open_cards():
    return sb._sb("GET", "board_cards?status=eq.open&select=*") or []


def upsert_card(coluna, kind, contact_id, origem, origem_ts, brief, grupo=None,
                opportunity_id=None, stage=None, task_id=None, event_id=None,
                appt_start=None, last_note=None, existing=None):
    """1 card aberto por (contact, kind). Retorna True se criou."""
    key = (contact_id, kind)
    if existing is not None and key in existing:
        return False
    dup = sb._sb("GET", f"board_cards?status=eq.open&contact_id=eq.{contact_id}"
                        f"&kind=eq.{kind}&select=id&limit=1")
    if dup:
        return False
    # ⚑ reportado ou fechado na mão: suprime só a MESMA ocorrência — evento NOVO
    # (origem_ts mais novo) recria normalmente (nova perdida volta; nova resposta idem)
    rep = sb._sb("GET", f"board_cards?contact_id=eq.{contact_id}&kind=eq.{kind}"
                        "&or=(resolved_by.like.*reported*,resolved_by.like.*closed%20manually*)"
                        "&select=origem_ts&order=resolved_at.desc&limit=1")
    if rep and origem_ts and rep[0].get("origem_ts"):
        if iso(origem_ts) <= rep[0]["origem_ts"]:
            return False  # mesma ocorrência já reportada — aguarda revisão
    elif rep and not origem_ts:
        return False
    if last_note is None:
        try:  # regra Rafael: toda nota/comentário interno aparece no card
            last_note = last_note_for(contact_id)
        except Exception:
            last_note = None
    sb._sb("POST", "board_cards", json={
        "coluna": coluna, "grupo": grupo, "kind": kind, "contact_id": contact_id,
        "opportunity_id": opportunity_id,
        "nome": brief["nome"], "veh": brief["veh"], "interest": brief["interest"],
        "phone": brief["phone"],
        "origem": origem, "origem_ts": iso(origem_ts) if origem_ts else None,
        "closes_when": CLOSES.get(kind, ""), "stage": stage,
        "task_id": task_id, "event_id": event_id,
        "appt_start": iso(appt_start) if appt_start else None,
        "last_note": last_note,
    })
    return True


def resolve_card(card, how, user="", extra=None):
    sb._sb("PATCH", f"board_cards?id=eq.{card['id']}", json={
        "status": "resolved", "resolved_by": how, "resolved_user": user or None,
        "resolved_at": iso(now_utc()), "unres": False})


def age_out(card, dest_note):
    sb._sb("PATCH", f"board_cards?id=eq.{card['id']}", json={
        "status": "aged_out", "resolved_by": dest_note, "resolved_at": iso(now_utc())})


# -------------------- ciclo --------------------
def cycle(full_task_pass=False):
    cfg = load_cfg()
    W = cfg["windows"]
    test_ids, silent = excluded_sets()
    st_rows = sb._sb("GET", "config?key=eq.board_state&select=value") or []
    state = st_rows[0]["value"] if st_rows else {}
    since = parse_ts(state.get("last_scan")) or (now_utc() - dt.timedelta(hours=6))
    lookback = min(since, now_utc() - dt.timedelta(minutes=30))
    today = f"{dt.datetime.now(ET):%Y-%m-%d}"

    def ok_contact(cid, brief=None):
        if cid in test_ids or cid in silent:
            return False
        if brief and "teste-interno" in (brief.get("tags") or []):
            return False
        # report 09/jul: spam/DND totalmente bloqueado (dnd global ou Call+SMS ativos)
        # não gera card nenhum — não dá pra ligar nem textar, nada a fazer.
        if brief and brief.get("dnd"):
            return False
        return True

    # ---- 1. espelho de stages ----
    # NOTA (caso Evangelist/Alejandro): o índice do GHL pode devolver a MESMA opp em
    # dois stages durante a atualização — dedupe por opp_id ficando com o
    # lastStageChangeAt mais NOVO (a verdade mais recente vence).
    by_opp = {}
    for stage, (col, kind) in STAGE_COLS.items():
        for o in paged_opps(rules.STAGES[stage]):
            oid = o["id"]
            prev = by_opp.get(oid)
            ots = o.get("lastStageChangeAt") or o.get("updatedAt") or ""
            if not prev or ots > (prev[1].get("lastStageChangeAt") or prev[1].get("updatedAt") or ""):
                by_opp[oid] = (stage, o)
    opps = {}
    for stage, o in by_opp.values():
        opps.setdefault(o["contactId"], []).append((stage, o))
    log(f"stages espelhados: {len(by_opp)} opps ({sum(len(v) for v in opps.values())} após dedupe)")

    # ---- 2. varredura de conversas ----
    calls, sms_out, sms_in, comments, conv_last = scan_conversations(lookback)
    log(f"scan: {len(calls)} calls · {len(sms_out)} sms out · {len(sms_in)} sms in · "
        f"{len(comments)} comentários")
    manual_sms = [s for s in sms_out if s.get("source") != "workflow" and s.get("user_id")]

    # regra Rafael: nota/comentário interno NOVO aparece nos cards abertos do lead
    freshened = set()
    for ev in comments:
        cid = ev["contact_id"]
        if cid in freshened:
            continue
        freshened.add(cid)
        body = re.sub(r"\s+", " ", (ev.get("body") or "").strip())
        if body:
            sb._sb("PATCH", f"board_cards?status=eq.open&contact_id=eq.{cid}",
                   json={"last_note": f"Internal ({ev['ts'].astimezone(ET):%b %d %H:%M}): "
                                      f"\"{body[:220]}\""})
    # eventos de contato (call/sms) também renovam a nota do card (nota pode ter mudado)
    for cid in {c["contact_id"] for c in calls} | {s["contact_id"] for s in sms_in}:
        if cid in freshened:
            continue
        freshened.add(cid)
        has_open = sb._sb("GET", f"board_cards?status=eq.open&contact_id=eq.{cid}&select=id&limit=1")
        if has_open:
            ln = last_note_for(cid)
            if ln:
                sb._sb("PATCH", f"board_cards?status=eq.open&contact_id=eq.{cid}",
                       json={"last_note": ln})

    # ---- 3. tentativas válidas (régua do PAINEL_DIARIO, determinística) ----
    # atendida ("completed") → válida · não atendida/voicemail com ≥25s + SMS manual
    # do MESMO usuário ≤10min → válida · toca-e-desliga → não conta.
    for c in calls:
        if c["direction"] != "outbound":
            continue
        uk = user_key(cfg, c.get("user_id"), c.get("source"))
        if uk not in ("eugene", "rafael"):
            continue
        dur = c.get("duration") or 0
        status = (c.get("status") or "").lower()
        answered = call_answered(cfg, status, dur)
        valid = False
        pending = False
        if answered:
            valid = True
        elif dur >= cfg["valid_min_sec"]:
            win_end = c["ts"] + dt.timedelta(minutes=cfg["valid_sms_window_min"])
            has_sms = any(s["contact_id"] == c["contact_id"]
                          and user_key(cfg, s.get("user_id"), s.get("source")) == uk
                          and c["ts"] <= s["ts"] <= win_end for s in manual_sms)
            valid = has_sms
            pending = (not has_sms) and (now_utc() - c["ts"]) < dt.timedelta(
                minutes=cfg["valid_sms_window_min"])
        sb._sb("POST", "board_attempts?on_conflict=call_id",
               headers_extra={"Prefer": "resolution=merge-duplicates"},
               json={"call_id": c["id"], "user_key": uk, "contact_id": c["contact_id"],
                     "call_ts": iso(c["ts"]), "answered": dur > 0, "duration": dur,
                     "valid": valid, "pending_sms": pending, "day": today})
    # revalidar pendentes de SMS
    for a in sb._sb("GET", f"board_attempts?pending_sms=eq.true&day=eq.{today}&select=*") or []:
        cts = parse_ts(a["call_ts"])
        win_end = cts + dt.timedelta(minutes=cfg["valid_sms_window_min"])
        has_sms = any(s["contact_id"] == a["contact_id"]
                      and user_key(cfg, s.get("user_id"), s.get("source")) == a["user_key"]
                      and cts <= s["ts"] <= win_end for s in manual_sms)
        if has_sms:
            sb._sb("PATCH", f"board_attempts?call_id=eq.{a['call_id']}",
                   json={"valid": True, "pending_sms": False})
        elif now_utc() > win_end:
            sb._sb("PATCH", f"board_attempts?call_id=eq.{a['call_id']}",
                   json={"pending_sms": False})

    oc = open_cards()
    # envelhecimento (PLANO §A): card aberto que saiu da janela viva → aged_out (vira
    # ração do warm-up); nada é deletado nem esquecido — só muda de coluna.
    AGE_WIN = {"missed_inbound": W["col1_days"], "sms_reply": W["col1_days"],
               "hot": W["col1_days"], "new_lead": W["col2_days"],
               "task": W["task_overdue_days"], "urable": W["urable_days"],
               "pipeline": W["pipeline_days"], "followup": W["pipeline_days"],
               "quote_task": W["pipeline_days"],
               "followup_notask": W["pipeline_days"], "quote_notask": W["pipeline_days"]}
    aged_n = 0
    for c in list(oc):
        win_d = AGE_WIN.get(c["kind"])
        ots = parse_ts(c.get("origem_ts"))
        if win_d and ots and (now_utc() - ots).days > win_d and not c.get("unres"):
            age_out(c, f"aged out of window ({win_d}d) → warm-up ration")
            oc.remove(c)
            aged_n += 1
    if aged_n:
        log(f"envelhecidos → ração: {aged_n}")
    existing = {(c["contact_id"], c["kind"]) for c in oc}
    by_contact = {}
    for c in oc:
        by_contact.setdefault(c["contact_id"], []).append(c)

    # Regra Peter: appointments futuros (todos os calendários, 90d) em UMA passada →
    # set de contatos que vivem na coluna 5 e não podem ter card de prioridade.
    appt_cids = set()
    a_start = dt.datetime.now(ET).replace(hour=0, minute=0, second=0, microsecond=0)
    for cal_id in sb.CALENDARS.values():
        r = ghl.get("/calendars/events", {"locationId": ghl.LOCATION_ID, "calendarId": cal_id,
                                          "startTime": int(a_start.timestamp() * 1000),
                                          "endTime": int((a_start + dt.timedelta(days=90)).timestamp() * 1000)})
        if r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            if e.get("appointmentStatus") in ("cancelled", "invalid", "noshow") \
                    or not e.get("contactId"):
                continue
            st = parse_ts(str(e.get("startTime")))
            if st and st > now_utc() - dt.timedelta(hours=3):
                appt_cids.add(e["contactId"])

    # ---- 4. colunas 1/2/4 (espelho com janelas) ----
    n_new = 0
    now = now_utc()

    def moves_today(cid):
        """Cadência (regra Rafael): 2 mudanças de stage HOJE = completo por hoje."""
        rows = sb._sb("GET", f"board_cards?contact_id=eq.{cid}&status=eq.resolved"
                             f"&resolved_at=gte.{today}T04:00:00Z"
                             "&resolved_by=like.stage*&select=id") or []
        return len(rows)

    for cid, lst in opps.items():
        if cid in appt_cids:
            continue  # regra Peter: appointment marcado → coluna 5 governa
        for stage, o in lst:
            col, kind = STAGE_COLS[stage]
            ots = parse_ts(o.get("lastStageChangeAt") or o.get("updatedAt") or o.get("createdAt")) or now
            age_days = (now - ots).days
            # PLANO §A: fora da janela viva → não vira card do dia (vira ração do warm-up)
            if kind == "pipeline" and age_days > W["pipeline_days"]:
                continue
            if kind == "new_lead" and age_days > W["col2_days"]:
                continue
            if kind == "hot" and age_days > W["col1_days"]:
                continue  # HOT envelhecido (ex.: legado migrado) → ração do warm-up
            if kind == "pipeline" and moves_today(cid) >= 2:
                continue  # 1-2 ligações/dia feitas → volta amanhã se ainda no pipeline
            brief = contact_brief(cid)
            if not ok_contact(cid, brief):
                continue
            # Great Cars: prioridade + tag persistente (report 09/jul)
            gc = is_great_car(stage, brief)
            grupo = "great_car" if gc else None
            if stage == "Great Cars" and GREAT_CARS_TAG not in \
                    {str(t).lower() for t in (brief.get("tags") or [])}:
                if add_contact_tag(cid, GREAT_CARS_TAG):
                    brief.setdefault("tags", []).append(GREAT_CARS_TAG)
            origem = ("Great Cars (qualified) · call FIRST" if stage == "Great Cars" else
                      f"HOT LEADS · in stage since {ots:%b %d}" if kind == "hot" else
                      f"New Lead · came in {ots:%b %d %H:%M}" if kind == "new_lead" else
                      f"{stage} · since {ots:%b %d}")
            n_new += upsert_card(col, kind, cid, origem, ots, brief, grupo=grupo,
                                 opportunity_id=o["id"], stage=stage, existing=existing)

    # (definições usadas pelas colunas 7 e 3 — Follow Up/Quote Sent + tasks por contato)
    fu_opps = {o["contactId"]: o for o in paged_opps(rules.STAGES["Follow Up"])
               if o.get("status") == "open"}
    qs_opps = {o["contactId"]: o for o in paged_opps(rules.STAGES["Quote Sent"])
               if o.get("status") == "open"}
    tasks_by_contact = {}

    # ---- col7: SÓ VERMELHOS — Follow Up e Quote Sent SEM task (atenção imediata) ----
    for fu_stage, notask_kind, stage_opps in (("Follow Up", "followup_notask", fu_opps),
                                              ("Quote Sent", "quote_notask", qs_opps)):
        for cid, o in stage_opps.items():
            if cid in appt_cids:
                continue  # regra Peter: appointment marcado → coluna 5 governa
            ots = parse_ts(o.get("lastStageChangeAt") or o.get("updatedAt")) or now
            if (now - ots).days > W["pipeline_days"]:
                continue  # envelhecido → warm-up cuida
            pend = tasks_by_contact.get(cid)
            if pend is None:
                tr = ghl.get(f"/contacts/{cid}/tasks")
                pend = [t for t in (tr.json().get("tasks", []) if tr.status_code == 200 else [])
                        if not t.get("completed") and t.get("dueDate")]
            if pend:
                continue  # tem task → vive na col 3 quando a data chegar
            brief = contact_brief(cid)
            if not ok_contact(cid, brief):
                continue
            n_new += upsert_card(
                7, notask_kind, cid,
                f"{fu_stage} since {ots:%b %d} — NO TASK · needs a decision",
                ots, brief, opportunity_id=o["id"], stage=fu_stage, existing=existing)

    # col1: inbound perdida sem retorno + SMS aguardando resposta (janela 3d)
    col1_win = now - dt.timedelta(days=W["col1_days"])
    for c in calls:
        if c["direction"] == "inbound" and not c.get("duration") and c["ts"] >= col1_win:
            returned = any(cc["direction"] == "outbound" and cc["contact_id"] == c["contact_id"]
                           and cc["ts"] > c["ts"] for cc in calls)
            if returned:
                continue
            if (c["contact_id"], "missed_inbound") not in existing \
                    and (c["contact_id"] in appt_cids or has_upcoming_appt(c["contact_id"])):
                continue  # report Rafael 08/jul: já tem appointment → coluna 5 governa
            if any(s["contact_id"] == c["contact_id"] and s["ts"] > c["ts"]
                   and no_action_reply(cfg, s.get("body")) for s in sms_in):
                continue  # regra Coleen: cliente já disse misdial/cortesia → sem card
            brief = contact_brief(c["contact_id"])
            if not ok_contact(c["contact_id"], brief):
                continue
            n_new += upsert_card(1, "missed_inbound", c["contact_id"],
                                 f"Missed inbound · called {c['ts'].astimezone(ET):%H:%M}, no answer",
                                 c["ts"], brief,
                                 grupo=("great_car" if is_great_car(None, brief) else None),
                                 existing=existing)
    for cid, last in conv_last.items():
        if last["type"] == "TYPE_SMS" and last["direction"] == "inbound" \
                and last["ts"] and last["ts"] >= col1_win:
            if no_action_reply(cfg, last.get("body")):
                continue  # cortesia/misdial → nenhuma ação (regra Greg/Coleen)
            if (cid, "sms_reply") not in existing \
                    and (cid in appt_cids or has_upcoming_appt(cid)):
                continue  # já tem appointment → vive na coluna 5
            brief = contact_brief(cid)
            if not ok_contact(cid, brief):
                continue
            n_new += upsert_card(1, "sms_reply", cid,
                                 f"SMS awaiting reply · last msg is theirs, {last['ts'].astimezone(ET):%H:%M}",
                                 last["ts"], brief,
                                 grupo=("great_car" if is_great_car(None, brief) else None),
                                 existing=existing)

    # ---- col3: tasks POR IMPORTÂNCIA (regra Rafael): verde=Quote Sent c/ task ·
    # azul=Follow Up c/ task · amarelo=task avulsa. + urable sem resposta. ----
    task_universe = set(opps.keys()) | {c["contact_id"] for c in oc} \
        | set(fu_opps) | set(qs_opps)
    for cid in list(task_universe)[:450]:
        brief = None
        r = ghl.get(f"/contacts/{cid}/tasks")
        if r.status_code != 200:
            continue
        pend = [t for t in r.json().get("tasks", [])
                if not t.get("completed") and t.get("dueDate")]
        pend.sort(key=lambda t: t.get("dueDate") or "")  # mais VENCIDA primeiro
        tasks_by_contact[cid] = pend
        for t in pend:
            due = parse_ts(t.get("dueDate"))
            days_over = (now - due).days
            if due.date() > dt.datetime.now(ET).date():
                continue  # futuras: invisíveis até o dia
            # VENCIDAS (report 09/jul): ficam SEMPRE no board, em vermelho, até o Eugene
            # resolver (mudar a data → recolore · ou fechar a task + mover p/ Lost → some).
            # Nada de sumir por idade — antes uma vencida antiga "desaparecia" do board.
            overdue = days_over > 0
            brief = brief or contact_brief(cid)
            if not ok_contact(cid, brief):
                break
            label = "due today" if days_over <= 0 else f"overdue {days_over}d"
            if cid in qs_opps:
                kind, pref = "quote_task", "QUOTE SENT"
            elif cid in fu_opps:
                kind, pref = "followup", "Follow Up"
            else:
                kind, pref = "task", "Task"
            n_new += upsert_card(3, kind, cid,
                                 f"{pref} · task \"{(t.get('title') or '')[:36]}\" · {label}",
                                 due, brief, task_id=t.get("id"),
                                 grupo=("overdue" if overdue else None),
                                 stage=("Quote Sent" if kind == "quote_task" else
                                        "Follow Up" if kind == "followup" else None),
                                 existing=existing)
            break  # 1 card por contato (a task mais próxima/vencida)
    # urable enviados (scan) sem resposta
    for s in sms_out:
        if URABLE.search(s["body"]) and s["ts"] >= now - dt.timedelta(days=W["urable_days"]):
            replied = any(si["contact_id"] == s["contact_id"] and si["ts"] > s["ts"]
                          for si in sms_in)
            if replied:
                continue
            if s["contact_id"] in appt_cids:
                continue  # regra Peter: appointment marcado → coluna 5 governa
            brief = contact_brief(s["contact_id"])
            if not ok_contact(s["contact_id"], brief):
                continue
            n_new += upsert_card(3, "urable", s["contact_id"],
                                 f"Urable sent {s['ts'].astimezone(ET):%b %d} · no reply since",
                                 s["ts"], brief, existing=existing)

    # ---- col5: appointments próximos 2 dias (+ cancelamentos futuros → reschedule) ----
    # Janela larga p/ pegar cancelamento de appointment futuro (report 09/jul NELSON).
    start = dt.datetime.now(ET).replace(hour=0, minute=0, second=0, microsecond=0)
    win_lo = start - dt.timedelta(days=1)
    win_hi = start + dt.timedelta(days=14)
    end = start + dt.timedelta(days=2)  # janela dos CARDS ativos (col5)
    appts = []
    for cal_name, cal_id in sb.CALENDARS.items():
        r = ghl.get("/calendars/events", {"locationId": ghl.LOCATION_ID, "calendarId": cal_id,
                                          "startTime": int(win_lo.timestamp() * 1000),
                                          "endTime": int(win_hi.timestamp() * 1000)})
        if r.status_code == 200:
            appts += r.json().get("events", [])
    # status atual por evento (p/ fechar cards obsoletos na resolução, mais abaixo)
    appt_status = {e.get("id"): e.get("appointmentStatus") for e in appts if e.get("id")}
    resched_done = set()
    for e in appts:
        cid = e.get("contactId")
        if not cid:
            continue
        status = e.get("appointmentStatus")
        stt = parse_ts(str(e.get("startTime")))
        # CANCELADO (report 09/jul NELSON): card de RESCHEDULE (assim como no-show).
        # Os cards de confirmação obsoletos fecham no loop de resolução via appt_status.
        # noshow/invalid: o pool do warm-up já cuida.
        if status == "cancelled":
            if cid in resched_done:
                continue
            resched_done.add(cid)
            # IGNORADO (report 09/jul): se o Eugene já dispensou o reschedule DESTE
            # cancelamento (cliente desistiu de vez), não recria o card do mesmo evento.
            eid = e.get("id")
            ign = sb._sb("GET", f"board_cards?contact_id=eq.{cid}&kind=eq.warmup"
                                f"&event_id=eq.{eid}&resolved_by=like.*ignored*"
                                "&select=id&limit=1") if eid else None
            if ign:
                continue
            brief = contact_brief(cid)
            if ok_contact(cid, brief):
                n_new += upsert_card(6, "warmup", cid,
                                     f"Cancelled {stt.astimezone(ET):%b %d} — RESCHEDULE (was booked)"
                                     if stt else "Cancelled appointment — RESCHEDULE (was booked)",
                                     stt or now, brief, grupo="reschedule",
                                     event_id=eid, existing=existing)
            continue
        # COMPARECEU (report 09/jul): estado terminal bom — nenhum card (nem "a
        # confirmar" nem reschedule). Os cards de appt abertos fecham na resolução.
        if status in ("invalid", "noshow", "showed"):
            continue
        # só vira card ativo se o appointment é nos próximos 2 dias
        if not stt or stt.astimezone(ET) < win_lo or stt.astimezone(ET) > end:
            continue
        brief = contact_brief(cid)
        if not ok_contact(cid, brief):
            continue
        if status == "confirmed":
            nr = ghl.get(f"/contacts/{cid}/notes")
            notes = nr.json().get("notes", []) if nr.status_code == 200 else []
            last_note = None
            if notes:
                ln = max(notes, key=lambda x: x.get("dateAdded") or "")
                body = re.sub(r"<[^>]+>", " ", ln.get("body") or "").strip()
                last_note = f"Last note ({parse_ts(ln.get('dateAdded')):%b %d}): \"{body[:220]}\""
            n_new += upsert_card(5, "appt_info", cid,
                                 f"Appointment {stt.astimezone(ET):%b %d, %H:%M} · confirmed",
                                 stt, brief, grupo="confirmed", event_id=e.get("id"),
                                 appt_start=stt, last_note=last_note, existing=existing)
        else:
            n_new += upsert_card(5, "appt_confirm", cid,
                                 f"Appointment {stt.astimezone(ET):%b %d, %H:%M} · not confirmed",
                                 stt, brief, grupo="to_confirm", event_id=e.get("id"),
                                 appt_start=stt, existing=existing)

    # ---- col6: warm up (ração + reabastecimento) ----
    open_now = open_cards()
    open_call_cards = [c for c in open_now if c["kind"] in CALL_KINDS]
    warm_open = [c for c in open_now if c["kind"] == "warmup"]
    valid_today = len(sb._sb("GET", f"board_attempts?day=eq.{today}&user_key=eq.eugene"
                                    "&valid=eq.true&select=call_id") or [])
    warm_created_today = len(sb._sb("GET", f"board_cards?kind=eq.warmup&day_created=eq.{today}"
                                           "&select=id") or [])
    need = max(cfg["ration"] - warm_created_today,
               (cfg["goal_calls"] - valid_today) - len(open_call_cards))
    # FILA POR IMPORTÂNCIA (regra Rafael 08/jul): o Warm up é a CASA de todo o passivo
    # recuperável. Pool = fila inteira, montado 1x/dia (e visível no board); a ração
    # libera os cards do dia do TOPO. tier 0 no-show (RESCHEDULE) · tier 1 melhor/mais
    # novo carro · tier 2 resto (recente 1º) · tier 3 faxina "no response" (fundo).
    excluded_cold = {r["contact_id"] for r in
                     (sb._sb("GET", "lead_flags?cold_excluded=eq.true&select=contact_id") or [])}
    faxina_rows = sb._sb("GET", "config?key=eq.faxina_cids&select=value") or []
    faxina_cids = set(((faxina_rows[0].get("value") if faxina_rows else None) or {})
                      .get("cids", []))
    pool_rows = sb._sb("GET", "config?key=eq.warmup_pool&select=value") or []
    pool_cfg = (pool_rows[0].get("value") if pool_rows else None) or {}
    if pool_cfg.get("day") != today:
        pool = []
        seen = set()
        known = {}   # nome/carro conhecidos via histórico de cards (barato)
        for row in sb._sb("GET", "board_cards?select=contact_id,veh,nome"
                                 "&order=created_at.desc&limit=1500") or []:
            if row["contact_id"] not in known:
                known[row["contact_id"]] = (row.get("nome"), row.get("veh"))
        # tier 0: no-shows dos últimos 90d — reagendar primeiro (mais recente 1º)
        ns_start = now_utc() - dt.timedelta(days=90)
        for cal_id in sb.CALENDARS.values():
            r = ghl.get("/calendars/events", {"locationId": ghl.LOCATION_ID,
                "calendarId": cal_id,
                "startTime": int(ns_start.timestamp() * 1000),
                "endTime": int(now_utc().timestamp() * 1000)})
            if r.status_code != 200:
                continue
            for e in r.json().get("events", []):
                cid = e.get("contactId")
                st = parse_ts(str(e.get("startTime")))
                if not cid or not st or e.get("appointmentStatus") != "noshow" \
                        or cid in seen or cid in appt_cids or cid in excluded_cold:
                    continue
                seen.add(cid)
                nm, vh = known.get(cid, (None, None))
                pool.append({"cid": cid, "tier": 0, "score": st.timestamp(),
                             "ots": iso(st), "nome": nm or e.get("title"), "veh": vh,
                             "origem": f"No-show {st:%b %d} — RESCHEDULE",
                             "opp": None})
        # tiers 1/2/3: cards envelhecidos + TODO o Lost recuperável
        cands = []
        for a in sb._sb("GET", "board_cards?status=eq.aged_out"
                               "&select=contact_id,veh,nome,origem,origem_ts"
                               "&order=origem_ts.desc&limit=200") or []:
            cands.append((a["contact_id"], a.get("nome"), a.get("veh"),
                          f"Aged: {(a.get('origem') or '')[:56]}",
                          a.get("origem_ts"), None, None))
        lost = paged_opps(rules.STAGES["Lost"])
        lost.sort(key=lambda o: o.get("updatedAt") or "", reverse=True)
        for o in lost[:900]:
            cands.append((o["contactId"], o.get("name"), None, None,
                          o.get("updatedAt"), o.get("createdAt"), o["id"]))
        fetches = 0
        for cid, nm, veh, origem, ots_s, created_s, opp_id in cands:
            if cid in seen or cid in appt_cids or cid in excluded_cold:
                continue
            seen.add(cid)
            k_nm, k_vh = known.get(cid, (None, None))
            nm = nm or k_nm
            veh = veh or k_vh
            if veh is None and cid not in faxina_cids and fetches < 250:
                b = contact_brief(cid)
                veh, nm = b.get("veh"), nm or b.get("nome")
                fetches += 1
            ots = parse_ts(ots_s) or now
            if cid in faxina_cids:
                # faxina de hoje mudou o updatedAt — usar a criação da opp como idade
                # real e mandar pro FUNDO da fila (tier 3): mora aqui, sem furar fila
                ct = parse_ts(created_s) or ots
                pool.append({"cid": cid, "tier": 3, "score": ct.timestamp(),
                             "ots": iso(ct), "nome": nm, "veh": veh,
                             "origem": f"Never responded · lead from {ct:%b %Y}",
                             "opp": opp_id})
                continue
            car_tier, yr = veh_rank(veh)
            base = origem or f"Lost (recoverable) · {ots:%b %d}"
            if car_tier > 0:
                pool.append({"cid": cid, "tier": 1,
                             "score": car_tier * 10000 + yr, "ots": iso(ots),
                             "nome": nm, "veh": veh, "origem": base, "opp": opp_id})
            else:
                pool.append({"cid": cid, "tier": 2, "score": ots.timestamp(),
                             "ots": iso(ots), "nome": nm, "veh": veh,
                             "origem": base, "opp": opp_id})
        pool.sort(key=lambda p: (p["tier"], -p["score"]))
        pool_cfg = {"day": today, "items": pool[:1000]}
        sb._sb("POST", "config?on_conflict=key",
               json={"key": "warmup_pool", "value": pool_cfg},
               headers_extra={"Prefer": "resolution=merge-duplicates"})
        log(f"warm-up pool do dia: {len(pool)} na fila "
            f"(no-show {sum(1 for p in pool if p['tier'] == 0)} · "
            f"carro {sum(1 for p in pool if p['tier'] == 1)} · "
            f"fundo {sum(1 for p in pool if p['tier'] == 3)}) · {fetches} fetches")
    if need > 0:
        released = 0
        open_cids = {c["contact_id"] for c in open_now}
        GRUPOS = {0: "reschedule", 1: "best_car", 2: "other", 3: "other"}
        for p in pool_cfg.get("items", []):
            if released >= need:
                break
            cid = p["cid"]
            # já tem QUALQUER card aberto → o board já cobra esse lead hoje
            if cid in open_cids or (cid, "warmup") in existing \
                    or cid in appt_cids or cid in excluded_cold:
                continue
            brief = contact_brief(cid)
            if not ok_contact(cid, brief):
                continue
            tags_low = {str(t).lower() for t in (brief.get("tags") or [])}
            if tags_low & set(cfg.get("warmup_excluded_tags", [])):
                continue
            made = upsert_card(6, "warmup", cid, p["origem"],
                               parse_ts(p.get("ots")) or now, brief,
                               grupo=GRUPOS[p["tier"]],
                               opportunity_id=p.get("opp"), existing=existing)
            if made:
                open_cids.add(cid)
            released += made
        log(f"warm-up liberados: {released} (need {need})")

    # ---- 5. RESOLUÇÃO ----
    oc = open_cards()
    resolutions = 0
    call_by_contact = {}
    for c in calls:
        if c["direction"] == "outbound":
            prev = call_by_contact.get(c["contact_id"])
            if not prev or c["ts"] > prev["ts"]:
                call_by_contact[c["contact_id"]] = c
    stage_now = {cid: {s for s, _ in lst} for cid, lst in opps.items()}
    for card in oc:
        cid = card["contact_id"]
        kind = card["kind"]
        created = parse_ts(card["created_at"])
        # DND AUTO-CLOSE (report 09/jul): atendente ativou DND depois que o card já
        # existia (ex.: percebeu que era spam) → o card SOME sozinho. Só p/ cards de
        # "contatar" (col1/warm-up, poucos) pra não estourar chamadas de contact_brief.
        if kind in ("missed_inbound", "sms_reply", "hot", "new_lead", "warmup", "urable") \
                and contact_brief(cid).get("dnd"):
            resolve_card(card, "DND activated — blocked/spam, no contact possible", "")
            resolutions += 1
            continue
        # REGRA PETER (report 08/jul): appointment futuro fecha qualquer card de
        # prioridade de contato — o lead já vive na coluna 5.
        if kind in APPT_WINS_KINDS and cid in appt_cids:
            resolve_card(card, "appointment booked — lives in Appointments column", "")
            resolutions += 1
            continue
        # ESPELHO PRIMEIRO (caso Jamile): card de stage cuja opp SAIU do stage fecha
        # SEMPRE — o card do stage novo assume. Vale com ou sem call no meio.
        # (Follow Up/Quote Sent: stage_now não os pagina — checar direto na opp.)
        if kind in STAGE_KINDS and card.get("stage"):
            if card["stage"] in ("Follow Up", "Quote Sent"):
                opr = ghl.get("/opportunities/search", {"location_id": ghl.LOCATION_ID,
                                                        "contact_id": cid, "limit": 5})
                cur = {rules.STAGE_BY_ID.get(o.get("pipelineStageId"))
                       for o in (opr.json().get("opportunities", []) if opr.status_code == 200 else [])
                       if o.get("status") == "open"}
                if card["stage"] not in cur:
                    resolve_card(card, "stage moved", "")
                    resolutions += 1
                    continue
            elif card["stage"] not in stage_now.get(cid, set()):
                resolve_card(card, "stage moved", "")
                resolutions += 1
                continue
        # vermelhos de task faltando: somem quando a task com data EXISTE
        if kind in ("followup_notask", "quote_notask"):
            tr = ghl.get(f"/contacts/{cid}/tasks")
            has_task = any(not t.get("completed") and t.get("dueDate")
                           for t in (tr.json().get("tasks", []) if tr.status_code == 200 else []))
            if has_task:
                resolve_card(card, "task created", "")
                resolutions += 1
            continue
        # follow-up/quote com task: fecha quando a task é CONCLUÍDA no GHL
        if kind in ("followup", "quote_task") and card.get("task_id"):
            tr = ghl.get(f"/contacts/{cid}/tasks")
            tlist = tr.json().get("tasks", []) if tr.status_code == 200 else []
            if any(t.get("id") == card["task_id"] and t.get("completed") for t in tlist):
                resolve_card(card, "task completed", "")
                resolutions += 1
                continue
        # CHAMADA PERDIDA (regra Rafael): retornar a ligação FECHA o card sozinho.
        # Se o retorno foi ATENDIDO e o lead ficou sem categoria → rastreador
        # "needs categorization" na faixa vermelha (coluna 0 = só na faixa).
        if kind == "missed_inbound":
            if has_upcoming_appt(cid):
                resolve_card(card, "has appointment — lives in Appointments column", "")
                resolutions += 1
                continue
            org = parse_ts(card.get("origem_ts")) or created
            # REGRA COLEEN (report 08/jul): o PRÓPRIO cliente respondeu cortesia/misdial
            # depois da perdida → mistério resolvido, retorno desnecessário
            if any(s["contact_id"] == cid and s["ts"] > org
                   and no_action_reply(cfg, s.get("body")) for s in sms_in):
                resolve_card(card, "client replied — misdial/courtesy, no action needed", "")
                resolutions += 1
                continue
            ret = next((c for c in calls if c["contact_id"] == cid
                        and c["direction"] == "outbound" and c["ts"] > org), None)
            if ret:
                # REGRA (report 09/jul): retornar chamada perdida FECHA o card. Só há
                # o que CATEGORIZAR se houve CONVERSA REAL (≥25s). "completed 0m0s" =
                # caixa postal / desligou = não atendeu → nada a categorizar, só fecha.
                # Se depois do retorno saiu SMS manual nosso (ex.: "returning your call,
                # call me back"), também está resolvido — sem categorização.
                real_talk = real_conversation(cfg, ret.get("duration"))
                sms_after = any(s["contact_id"] == cid and s["ts"] > ret["ts"]
                                and s.get("source") != "workflow" for s in sms_out)
                needs_cat = real_talk and not sms_after
                resolve_card(card, "returned the call" + (
                    "" if real_talk else " — no answer/voicemail"),
                             user_key(cfg, ret.get("user_id"), ret.get("source")))
                resolutions += 1
                if needs_cat:
                    sb._sb("POST", "board_cards", json={
                        "coluna": 0, "kind": "uncategorized", "contact_id": cid,
                        "nome": card.get("nome"), "veh": card.get("veh"),
                        "interest": card.get("interest"), "phone": card.get("phone"),
                        "origem": f"Returned call answered {ret['ts'].astimezone(ET):%H:%M} — needs categorization",
                        "origem_ts": iso(ret["ts"]),
                        "closes_when": "Needs categorization: book appointment · create task "
                                       "· send estimate · or mark Lost / move stage.",
                        "unres_call_ts": iso(ret["ts"]),
                        "unres_call_user": user_key(cfg, ret.get("user_id"), ret.get("source")),
                        "unres_call_answered": True,
                        "unres_call_dur": ret.get("duration") or 0})
                continue
        # SMS card: resposta enviada fecha · cortesia/appointment também (regra Greg/Coleen)
        if kind == "sms_reply":
            reply = next((s for s in sms_out if s["contact_id"] == cid
                          and s["ts"] > (parse_ts(card["origem_ts"]) or created)
                          and s.get("source") != "workflow"), None)
            if reply:
                resolve_card(card, "reply sent",
                             user_key(cfg, reply.get("user_id"), reply.get("source")))
                resolutions += 1
                continue
            last = conv_last.get(cid)
            if last and last.get("direction") == "inbound" \
                    and no_action_reply(cfg, last.get("body")):
                resolve_card(card, "courtesy reply — no action needed", "")
                resolutions += 1
                continue
            if has_upcoming_appt(cid):
                resolve_card(card, "has appointment — lives in Appointments column", "")
                resolutions += 1
            continue
        # confirmação de appointment
        # APPOINTMENTS (report 09/jul): o card "a confirmar" NÃO fecha só porque o SMS
        # de confirmação saiu (isso é automático no booking) — fecha só quando o status
        # vira "confirmed" (equipe marca à mão depois que o LEAD confirma) → aí o card
        # verde (appt_info) assume. Assim fica claro pra quem o assistente precisa ligar.
        if kind == "appt_confirm":
            st = appt_status.get(card.get("event_id"))
            if st == "confirmed":
                resolve_card(card, "confirmed", "")  # → appt_info (verde) assume
                resolutions += 1
            elif st == "showed":
                resolve_card(card, "showed — visit completed", "")
                resolutions += 1
            elif st in ("cancelled", "invalid", "noshow"):
                resolve_card(card, "appointment cancelled/gone", "")
                resolutions += 1
            elif card.get("appt_start") and parse_ts(card["appt_start"]) < now - dt.timedelta(hours=3):
                resolve_card(card, "visit time passed", "")
                resolutions += 1
            continue
        if kind == "appt_info":
            st = appt_status.get(card.get("event_id"))
            if st == "showed":
                resolve_card(card, "showed — visit completed", "")
                resolutions += 1
            elif st and st not in ("confirmed", None):
                # voltou a NÃO confirmado (equipe desmarcou) → o "a confirmar" assume
                resolve_card(card, "no longer confirmed — needs confirmation again", "")
                resolutions += 1
            elif card.get("appt_start") and parse_ts(card["appt_start"]) < now - dt.timedelta(hours=3):
                resolve_card(card, "visit time passed", "")
                resolutions += 1
            continue
        # colunas com ligação: call nova → relógio de resolução
        lc = call_by_contact.get(cid)
        if lc and (not card.get("unres_call_ts") or lc["ts"] > parse_ts(card["unres_call_ts"])):
            # p/ o relógio de resolução, "atendida" = CONVERSA REAL (≥25s); 0s = não
            # atendeu → pode auto-resolver por "stage avançou" (report 09/jul)
            answered = real_conversation(cfg, lc.get("duration"))
            sb._sb("PATCH", f"board_cards?id=eq.{card['id']}", json={
                "unres_call_ts": iso(lc["ts"]),
                "unres_call_user": user_key(cfg, lc.get("user_id"), lc.get("source")),
                "unres_call_answered": answered,
                "unres_call_dur": lc.get("duration") or 0})
            card["unres_call_ts"] = iso(lc["ts"])
            card["unres_call_answered"] = answered
        cts = parse_ts(card.get("unres_call_ts"))
        if not cts:
            continue  # sem call ainda: card espelho segue aberto
        # REGRA CARL (2026-07-08): cliente respondeu por SMS depois da call → a conversa
        # aconteceu — o vermelho some (se faltar responder, o card sms_reply da col 1 assume)
        replied = any(s["contact_id"] == cid and s["ts"] > cts for s in sms_in)
        if replied:
            sb._sb("PATCH", f"board_cards?id=eq.{card['id']}",
                   json={"unres": False, "unres_call_ts": None})
            card["unres"] = False
            continue
        # resoluções válidas após a call
        resolved = None
        res_user = ""
        # 1) appointment criado
        ar = ghl.get(f"/contacts/{cid}/appointments")
        if ar.status_code == 200:
            for e in ar.json().get("events", []):
                if parse_ts(e.get("dateAdded")) and parse_ts(e.get("dateAdded")) > cts:
                    resolved = "appointment booked"
                    res_user = user_key(cfg, (e.get("createdBy") or {}).get("userId"),
                                        (e.get("createdBy") or {}).get("source"))
                    break
        # 2) task criada com data
        if not resolved:
            tr = ghl.get(f"/contacts/{cid}/tasks")
            if tr.status_code == 200:
                for t in tr.json().get("tasks", []):
                    if parse_ts(t.get("dateAdded") or "") and parse_ts(t.get("dateAdded")) > cts \
                            and t.get("dueDate"):
                        resolved = "follow-up task created"
                        break
        # 3) estimate: link urable após a call
        if not resolved:
            ur = next((s for s in sms_out if s["contact_id"] == cid and s["ts"] > cts
                       and URABLE.search(s["body"])), None)
            if ur:
                resolved = "estimate sent (Urable)"
                res_user = user_key(cfg, ur.get("user_id"), ur.get("source"))
        # 4) Lost
        if not resolved:
            opr = ghl.get("/opportunities/search", {"location_id": ghl.LOCATION_ID,
                                                    "contact_id": cid, "limit": 5})
            for o in (opr.json().get("opportunities", []) if opr.status_code == 200 else []):
                if rules.STAGE_BY_ID.get(o.get("pipelineStageId")) == "Lost" \
                        and parse_ts(o.get("updatedAt")) and parse_ts(o.get("updatedAt")) > cts:
                    resolved = "marked Lost"
                    break
                # não atendida: stage avançou
                if not card.get("unres_call_answered") and card.get("stage") \
                        and rules.STAGE_BY_ID.get(o.get("pipelineStageId")) not in (card["stage"], None):
                    resolved = "stage advanced"
                    break
        # warm-up não atendida: SMS de reativação
        if not resolved and kind == "warmup" and not card.get("unres_call_answered"):
            re_sms = next((s for s in sms_out if s["contact_id"] == cid and s["ts"] > cts
                           and s.get("source") != "workflow"), None)
            if re_sms:
                resolved = "reactivation SMS sent"
                res_user = user_key(cfg, re_sms.get("user_id"), re_sms.get("source"))
        if resolved:
            resolve_card(card, resolved, res_user or card.get("unres_call_user") or "")
            resolutions += 1
        else:
            mins = (now - cts).total_seconds() / 60
            # VERMELHO "sem resolução" SÓ para CONVERSA REAL (report 09/jul): ligação
            # não atendida (0-25s) não vira vermelho — o desfecho dela é avançar stage
            # / tentar de novo, não "logar um resultado que não existe".
            if mins > cfg["resolution_min"] and not card.get("unres") \
                    and card.get("unres_call_answered"):
                sb._sb("PATCH", f"board_cards?id=eq.{card['id']}", json={"unres": True})

    # ---- 6. comissões (5 casos do Rafael) ----
    month0 = dt.datetime.now(ET).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_appts = []
    for cal_id in sb.CALENDARS.values():
        r = ghl.get("/calendars/events", {"locationId": ghl.LOCATION_ID, "calendarId": cal_id,
                                          "startTime": int(month0.timestamp() * 1000),
                                          "endTime": int((start + dt.timedelta(days=45)).timestamp() * 1000)})
        if r.status_code == 200:
            month_appts += r.json().get("events", [])
    for e in month_appts:
        cid = e.get("contactId")
        eid = e.get("id")
        if not cid or not eid or cid in test_ids:
            continue
        created_by = user_key(cfg, (e.get("createdBy") or {}).get("userId"),
                              (e.get("createdBy") or {}).get("source"))
        created_ts = parse_ts(e.get("dateAdded"))
        exists = sb._sb("GET", f"board_commissions?event_id=eq.{eid}&select=event_id,status") or []
        if not exists:
            eligible, reason = False, ""
            if created_by == "eugene":
                eligible = True
                reason = f"created by Eugene {created_ts:%b %d}" if created_ts else "created by Eugene"
            else:
                # confirmação ATIVA do Eugene ≤48h após criação (call atendida ou SMS manual)
                win_end = (created_ts or now) + dt.timedelta(hours=cfg["confirm_window_h"])
                active = next((c for c in calls if c["contact_id"] == cid
                               and user_key(cfg, c.get("user_id"), c.get("source")) == "eugene"
                               and c.get("duration") and created_ts and created_ts < c["ts"] <= win_end), None) \
                    or next((s for s in manual_sms if s["contact_id"] == cid
                             and user_key(cfg, s.get("user_id"), s.get("source")) == "eugene"
                             and created_ts and created_ts < s["ts"] <= win_end), None)
                if active:
                    eligible = True
                    reason = f"active confirmation by Eugene {active['ts']:%b %d}"
                else:
                    reason = f"created by {created_by}; no active confirmation by Eugene"
            status = "confirmed" if e.get("appointmentStatus") == "confirmed" else "booked"
            brief = contact_brief(cid)
            sb._sb("POST", "board_commissions?on_conflict=event_id",
                   headers_extra={"Prefer": "resolution=merge-duplicates"},
                   json={"event_id": eid, "contact_id": cid, "nome": brief["nome"],
                         "created_by_user": created_by,
                         "appt_start": str(e.get("startTime") or ""),
                         "eligible": eligible, "reason": reason, "status": status,
                         "day": today})
        else:
            if e.get("appointmentStatus") == "confirmed" and exists[0]["status"] == "booked":
                sb._sb("PATCH", f"board_commissions?event_id=eq.{eid}",
                       json={"status": "confirmed", "updated_at": iso(now)})
    # won: opps em Win do mês
    win_opps = paged_opps(rules.STAGES["Win"])
    win_contacts = {o["contactId"]: parse_ts(o.get("updatedAt")) for o in win_opps}
    for row in sb._sb("GET", "board_commissions?status=in.(booked,confirmed,done_waiting)"
                             "&select=event_id,contact_id,appt_start") or []:
        if row["contact_id"] in win_contacts:
            sb._sb("PATCH", f"board_commissions?event_id=eq.{row['event_id']}",
                   json={"status": "won", "won_at": iso(win_contacts[row["contact_id"]] or now),
                         "updated_at": iso(now)})
        else:
            ap = parse_ts(row.get("appt_start"))
            if ap and ap < now - dt.timedelta(days=7):
                sb._sb("PATCH", f"board_commissions?event_id=eq.{row['event_id']}",
                       json={"status": "expired", "updated_at": iso(now)})
            elif ap and ap < now:
                sb._sb("PATCH", f"board_commissions?event_id=eq.{row['event_id']}",
                       json={"status": "done_waiting", "updated_at": iso(now)})

    # ---- 7. contadores do dia ----
    att = sb._sb("GET", f"board_attempts?day=eq.{today}&user_key=eq.eugene&select=valid") or []
    unres_open = sb._sb("GET", "board_cards?status=eq.open&unres=eq.true"
                               "&unres_call_user=eq.eugene&select=id") or []
    sb._sb("POST", "board_days?on_conflict=day",
           headers_extra={"Prefer": "resolution=merge-duplicates"},
           json={"day": today, "dials": len(att),
                 "valid_attempts": sum(1 for a in att if a["valid"]),
                 "sms_manual": sum(1 for s in manual_sms
                                   if user_key(cfg, s.get("user_id"), s.get("source")) == "eugene"),
                 "resolutions": resolutions,
                 "unresolved_eod": len(unres_open),
                 "updated_at": iso(now)})
    # atividade por usuário (aba Owner)
    act = {}
    for uk in ("eugene", "rafael"):
        a_rows = sb._sb("GET", f"board_attempts?day=eq.{today}&user_key=eq.{uk}&select=valid") or []
        act[uk] = {"dials": len(a_rows), "valid": sum(1 for a in a_rows if a["valid"]),
                   "sms": sum(1 for s in manual_sms
                              if user_key(cfg, s.get("user_id"), s.get("source")) == uk)}
    act["automation"] = {"sms": sum(1 for s in sms_out if s.get("source") == "workflow")}
    sb._sb("POST", "config?on_conflict=key",
           headers_extra={"Prefer": "resolution=merge-duplicates"},
           json={"key": "board_activity", "value": {"date": today, "users": act,
                                                    "updated": iso(now)}})

    sb._sb("POST", "config?on_conflict=key",
           headers_extra={"Prefer": "resolution=merge-duplicates"},
           json={"key": "board_state", "value": {"last_scan": iso(now)}})
    log(f"ciclo ok: +{n_new} cards · {resolutions} resoluções · "
        f"válidas Eugene hoje: {sum(1 for a in att if a['valid'])}")


if __name__ == "__main__":
    cycle(full_task_pass="--full" in sys.argv)
