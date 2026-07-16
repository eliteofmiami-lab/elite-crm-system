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

import os  # noqa: E402

# ---- CACHE TTL EM DISCO (Lote 1, otimização de rate limit GHL) ----
# O bridge relança o processo a cada ciclo, então cache de processo não persiste.
# Perfil e tasks quase não mudam em minutos → cache em arquivo, com TTL. Corta ~80%
# das chamadas (varredura por-contato). Falha de API usa cache velho (nunca fecha
# card por engano). O arquivo vive na máquina do bridge (out/ghl_cache.json).
_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "out", "ghl_cache.json")
# TTLs LONGOS + DELTA (Lote 2): o cache serve de rede de segurança; a atualização
# imediata vem do DELTA — contato que MUDOU (call/sms/stage novo, ou tem card de task
# aberto) é re-buscado na hora (_changed_contacts). Contato sem mudança usa cache até
# o TTL longo. Perfil quase nunca muda (4h); tasks: 45min só p/ pegar due-date que
# chega sem atividade (o delta já pega abertura/fechamento de quem tem card).
BRIEF_TTL_MIN = 240
TASKS_TTL_MIN = 45
_cache_obj = None
_tasks_mem = {}  # dedup DENTRO do ciclo (evita re-busca task_universe + resolução)
_changed_contacts = set()  # DELTA: contatos com mudança neste ciclo → força re-busca


def _cache_load():
    global _cache_obj
    if _cache_obj is None:
        try:
            with open(_CACHE_PATH) as f:
                _cache_obj = json.load(f)
        except Exception:
            _cache_obj = {}
        _cache_obj.setdefault("brief", {})
        _cache_obj.setdefault("tasks", {})
    return _cache_obj


def _cache_fresh(entry, ttl_min):
    if not entry or "at" not in entry:
        return False
    try:
        return (now_utc() - parse_ts(entry["at"])).total_seconds() < ttl_min * 60
    except Exception:
        return False


def _cache_save():
    if _cache_obj is None:
        return
    try:
        cut = now_utc() - dt.timedelta(hours=2)  # poda entradas velhas
        for kind in ("brief", "tasks"):
            for cid in list(_cache_obj.get(kind, {}).keys()):
                a = _cache_obj[kind][cid].get("at")
                if not a or parse_ts(a) < cut:
                    del _cache_obj[kind][cid]
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w") as f:
            json.dump(_cache_obj, f)
    except Exception:
        pass


def contact_tasks(contact_id):
    """Tasks do contato com cache TTL + dedup no ciclo. Retorna lista (sucesso ou
    cache fresco/velho) ou None se a API falhou e não há cache — nesse caso o caller
    NÃO deve agir (não cria nem fecha card)."""
    if contact_id in _tasks_mem:
        return _tasks_mem[contact_id]
    fc = _cache_load()["tasks"].get(contact_id)
    # DELTA: contato que mudou (ou tem card de task aberto) NÃO usa cache — re-busca
    if contact_id not in _changed_contacts and _cache_fresh(fc, TASKS_TTL_MIN):
        _tasks_mem[contact_id] = fc["data"]
        return fc["data"]
    r = ghl.get(f"/contacts/{contact_id}/tasks")
    if r.status_code == 200:
        tasks = r.json().get("tasks", [])
        _cache_load()["tasks"][contact_id] = {"data": tasks, "at": iso(now_utc())}
        _tasks_mem[contact_id] = tasks
        return tasks
    if fc:  # API falhou → usa cache velho (nunca fecha card por engano)
        _tasks_mem[contact_id] = fc["data"]
        return fc["data"]
    _tasks_mem[contact_id] = None
    return None


_open_tasks_mem = {"val": "unset"}  # memo por processo (1 processo = 1 ciclo)


def location_open_tasks():
    """ESPELHO DO PAINEL DE TASKS (regra Rafael 10/jul): a lista de tasks PENDENTES
    do GHL é a fonte da verdade da coluna 3 — independente do stage da oportunidade
    (lead em Lost com task aberta = warm up, a task continua valendo). Usa o POST
    /tasks/search (o único endpoint com flag completed CONFIÁVEL — o GET com
    isLocation=true devolve flags velhas). Retorna a lista completa paginada, ou
    None se a API falhou — nesse caso o caller NÃO cria nem fecha nada no ciclo."""
    if _open_tasks_mem["val"] != "unset":
        return _open_tasks_mem["val"]
    out, after = [], None
    for _ in range(50):
        body = {"completed": False, "limit": 100}
        if after:
            body["searchAfter"] = after
        try:
            r = ghl.post(f"/locations/{ghl.LOCATION_ID}/tasks/search", body)
        except Exception:
            _open_tasks_mem["val"] = None
            return None
        if r.status_code not in (200, 201):
            _open_tasks_mem["val"] = None
            return None
        tks = r.json().get("tasks", [])
        out.extend(tks)
        if len(tks) < 100:
            break
        after = tks[-1].get("searchAfter")
        if not after:
            break
    _open_tasks_mem["val"] = out
    return out

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
                "task_upcoming_days": 7,  # espelho col3: próximas N dias visíveis
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
# followup/quote_task FORA daqui (10/jul): são cards do ESPELHO de tasks — só a
# task fechada/reagendada os fecha, nunca a mudança de stage (Lost = warm up).
STAGE_KINDS = {"hot", "new_lead", "pipeline",
               "followup_notask", "quote_notask"}

CF_VEH = {"make": "CiRd678lAFn854igklGR", "model": "LHwTnTb8TPz5BbJ0I2XV",
          "year": "C01IzbXlbESCLfhoHkrZ"}
# FONTE DO INTERESSE (09/jul): o lead responde "What Services are you interested in?"
# no formulário (CF_SERVICES). O antigo CF_INTEREST ("Elite Interesse Atual") é campo
# MANUAL quase sempre vazio → era a causa de "interest not set". Lê o form primeiro.
CF_SERVICES = "308nNEqn6D0lZruuJ10m"   # "What Services are you interested in?" (form)
CF_INTEREST = "D5TgphY9HlZMoS8wcWj1"   # "Elite Interesse Atual" (manual, fallback)


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
    """nome, veh, interest, phone, tags (cache no ciclo + cache TTL em disco)."""
    if contact_id in cache:
        return cache[contact_id]
    fc = _cache_load()["brief"].get(contact_id)
    # DELTA: força re-busca se o contato mudou neste ciclo; senão usa cache (TTL longo)
    if contact_id not in _changed_contacts and _cache_fresh(fc, BRIEF_TTL_MIN):
        cache[contact_id] = fc["data"]
        return fc["data"]
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
        b["interest"] = cfs.get(CF_SERVICES) or cfs.get(CF_INTEREST) or next(
            (str(v) for k, v in cfs.items() if isinstance(v, str)
             and any(w in str(v).lower() for w in ("ppf", "coating", "wrap", "tint"))), None)
        _cache_load()["brief"][contact_id] = {"data": b, "at": iso(now_utc())}  # grava só em sucesso
    elif fc:
        b = fc["data"]  # API falhou → usa cache velho (melhor que vazio)
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
                    rec["from_num"] = msg.get("from")
                    rec["to_num"] = msg.get("to")
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
                appt_start=None, last_note=None, existing=None, assignee=None,
                dedup_task=False):
    """1 card aberto por (contact, kind) — ou por TASK (dedup_task=True, espelho da
    col 3: um contato pode ter várias tasks, cada uma vira um card). Retorna True se criou."""
    if dedup_task and task_id:
        dup = sb._sb("GET", f"board_cards?status=eq.open&task_id=eq.{task_id}"
                            "&select=id&limit=1")
        if dup:
            return False
        # ⚑ reportado/fechado na mão: mesma checagem comum abaixo, só que por task
        rep = sb._sb("GET", f"board_cards?task_id=eq.{task_id}"
                            "&or=(resolved_by.like.*reported*,resolved_by.like.*closed%20manually*)"
                            "&select=origem_ts&order=resolved_at.desc&limit=1")
    else:
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
        "last_note": last_note, "assignee": assignee,
    })
    return True


def resolve_card(card, how, user="", extra=None):
    sb._sb("PATCH", f"board_cards?id=eq.{card['id']}", json={
        "status": "resolved", "resolved_by": how, "resolved_user": user or None,
        "resolved_at": iso(now_utc()), "unres": False})


def age_out(card, dest_note):
    sb._sb("PATCH", f"board_cards?id=eq.{card['id']}", json={
        "status": "aged_out", "resolved_by": dest_note, "resolved_at": iso(now_utc())})


def called_contact_ids():
    """Contatos que JÁ receberam alguma tentativa de call (16/jul): calls outbound +
    board_attempts + disposições. Retorna None se a leitura parecer falha (proteção:
    nunca reclassificar o board inteiro por causa de uma resposta vazia do Supabase)."""
    cids = set()
    total = 0
    for table, filt in (("calls", "direction=eq.outbound"),
                        ("board_attempts", None),
                        ("ghl_events", "type=eq.disposition")):
        offset = 0
        while True:
            q = f"{table}?select=contact_id" + (f"&{filt}" if filt else "") \
                + f"&limit=1000&offset={offset}"
            rows = sb._sb("GET", q) or []
            total += len(rows)
            cids.update(r["contact_id"] for r in rows if r.get("contact_id"))
            if len(rows) < 1000:
                break
            offset += 1000
    # a base tem centenas de calls históricas — 0 linhas = leitura quebrada, não realidade
    return cids if total > 0 else None


# -------------------- ciclo --------------------
def cycle(full_task_pass=False):
    # TRAVA DE HORÁRIO (Lote 1): a varredura completa só roda em horário comercial
    # (seg-sáb, 9h-17h ET). Fora disso o webhook mantém o board vivo em tempo real —
    # varrer ~400 contatos de madrugada/domingo só queima a cota diária do GHL.
    et_now = dt.datetime.now(ET)
    if et_now.weekday() == 6 or not (9 <= et_now.hour < 17):
        log(f"fora do horário comercial ({et_now:%a %H:%M} ET) — ciclo pulado (webhook mantém o board)")
        return
    cfg = load_cfg()
    W = cfg["windows"]
    test_ids, silent = excluded_sets()
    st_rows = sb._sb("GET", "config?key=eq.board_state&select=value") or []
    state = st_rows[0]["value"] if st_rows else {}
    since = parse_ts(state.get("last_scan")) or (now_utc() - dt.timedelta(hours=6))
    lookback = min(since, now_utc() - dt.timedelta(minutes=30))
    today = f"{dt.datetime.now(ET):%Y-%m-%d}"

    # BOARD DESLIGADO (ordem do Rafael 16/07 à tarde: "não serviu, tá mais atrapalhando
    # que ajudando" — só volta depois de muitos testes, SE voltar). O ciclo roda em modo
    # MÍNIMO: nenhum card criado/movido/envelhecido — ficam só as automações de SMS que
    # ele pediu hoje (confirmações D-2, resgate de no-show, vigia do rodízio).
    bm_rows = sb._sb("GET", "config?key=eq.board_mode&select=value") or []
    if not bool(((bm_rows[0]["value"] if bm_rows else None) or {}).get("enabled", True)):
        calls, sms_out, sms_in, comments, conv_last = scan_conversations(lookback)
        for nome, fn in (("digest D-2", confirm_digest_d2),
                         ("resgate no-show", noshow_rescue),
                         ("vigia rodízio", lambda: rotation_watch(calls))):
            try:
                fn()
            except Exception as e:
                log(f"[warn] {nome} falhou: {e}")
        sb._sb("POST", "config?on_conflict=key",
               headers_extra={"Prefer": "resolution=merge-duplicates"},
               json={"key": "board_state", "value": {"last_scan": iso(now_utc())}})
        log("board OFF — ciclo mínimo (só automações de SMS)")
        _cache_save()
        return

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

    # SALVA-VIDAS (report 09/jul — apagão da API do GHL às 14h): se a busca de
    # oportunidades voltou VAZIA, é falha/instabilidade da API do GHL, NÃO "todo mundo
    # saiu do stage". Aborta o ciclo AGORA — antes de envelhecer/resolver — pra NUNCA
    # apagar o board inteiro por causa de resposta vazia. Quando a API volta, o próximo
    # ciclo sincroniza normal.
    stage_col_cards = [c for c in open_cards() if c["kind"] in ("hot", "new_lead", "pipeline")]
    if not by_opp and stage_col_cards:
        log(f"ABORTA CICLO: GHL devolveu 0 oportunidades, mas há {len(stage_col_cards)} "
            f"cards de stage abertos → instabilidade da API. Board preservado, nada apagado.")
        try:
            sb._sb("POST", "config?on_conflict=key",
                   headers_extra={"Prefer": "resolution=merge-duplicates"},
                   json={"key": "board_live_error",
                         "value": {"at": iso(now_utc()),
                                   "error": "GHL API returned 0 opportunities — cycle skipped to protect the board"}})
        except Exception:
            pass
        _cache_save()
        return

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
    # DELTA (Lote 2): monta o conjunto de contatos que MUDARAM neste ciclo → esses
    # forçam re-busca de brief/tasks (os demais usam cache com TTL longo). Sinais:
    # call/sms/comentário novos (scan), mudança de stage recente, e quem tem card de
    # task aberto (p/ fechar rápido quando a task é concluída/reagendada).
    _changed_contacts.clear()
    _changed_contacts.update(c["contact_id"] for c in calls)
    _changed_contacts.update(s["contact_id"] for s in sms_out)
    _changed_contacts.update(s["contact_id"] for s in sms_in)
    _changed_contacts.update(ev["contact_id"] for ev in comments)
    for _stage, _o in by_opp.values():
        _lsc = parse_ts(_o.get("lastStageChangeAt"))
        if _lsc and _lsc > since:  # mudou de stage desde o último scan
            _changed_contacts.add(_o["contactId"])
    _changed_contacts.update(c["contact_id"] for c in oc
                             if c["kind"] in ("task", "followup", "quote_task"))

    # envelhecimento (PLANO §A): card aberto que saiu da janela viva → aged_out (vira
    # ração do warm-up); nada é deletado nem esquecido — só muda de coluna.
    # TASKS NÃO ENVELHECEM (report 09/jul): uma task vencida FICA no board em vermelho
    # até resolver (concluir · reagendar). Antes "task/followup/quote_task" envelheciam
    # em 7d e a vencida sumia pra ração — o oposto do pedido. O ciclo de vida delas é a
    # própria task no painel do GHL (10/jul: nem Lost fecha — warm up).
    AGE_WIN = {"missed_inbound": W["col1_days"], "sms_reply": W["col1_days"],
               "hot": W["col1_days"], "new_lead": W["col2_days"],
               "urable": W["urable_days"], "pipeline": W["pipeline_days"],
               "followup_notask": W["pipeline_days"], "quote_notask": W["pipeline_days"]}
    # 16/jul: quem nunca recebeu call seria tratado diferente (reclassificação col 2 +
    # topo do reaquecimento). DESLIGADO 16/07 à tarde (config board_reclassify): as
    # fontes locais (calls/attempts/disposições) estão INCOMPLETAS vs o GHL real —
    # leads com 3-4 calls apareciam como NEVER CALLED (report Rafael). Religar SÓ
    # depois do backfill completo de conversas provar cobertura.
    _rc = sb._sb("GET", "config?key=eq.board_reclassify&select=value") or []
    _rc_on = bool(((_rc[0]["value"] if _rc else None) or {}).get("enabled"))
    called_cids = called_contact_ids() if _rc_on else None
    aged_n = 0
    for c in list(oc):
        win_d = AGE_WIN.get(c["kind"])
        ots = parse_ts(c.get("origem_ts"))
        if win_d and ots and (now_utc() - ots).days > win_d and not c.get("unres"):
            nc = (called_cids is not None and c["kind"] in ("new_lead", "pipeline")
                  and c["contact_id"] not in called_cids)
            age_out(c, "NEVER CALLED — aged out → top of warm-up" if nc
                    else f"aged out of window ({win_d}d) → warm-up ration")
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
            # 16/jul: lead SEM nenhuma call outbound não é "cadência" — é NEW LEAD.
            # A automação move lead novo direto pra Contact 1/2/3 e ele se disfarçava
            # de pipeline (col 4, "2 moves/dia = completo"). Ninguém ligava.
            reclassified = (called_cids is not None and kind == "pipeline"
                            and cid not in called_cids)
            if reclassified:
                col, kind = 2, "new_lead"
                # (>7d cai na janela da col 2 e não cria card novo — o card de pipeline
                # antigo segue vivo na col 4 até envelhecer pro topo do warm-up; por
                # isso o supersede do card antigo acontece SÓ na criação, lá embaixo.)
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
                      f"NEVER CALLED · {stage} since {ots:%b %d}" if reclassified else
                      f"New Lead · came in {ots:%b %d %H:%M}" if kind == "new_lead" else
                      f"{stage} · since {ots:%b %d}")
            if reclassified and (cid, "pipeline") in existing:
                # a col 2 assume — o card de cadência do mesmo lead sai de cena
                sb._sb("PATCH", f"board_cards?status=eq.open&contact_id=eq.{cid}"
                                "&kind=eq.pipeline",
                       json={"status": "resolved", "resolved_at": iso(now_utc()),
                             "resolved_by": "reclassified — never called → NEW LEAD (col 2)"})
                existing.discard((cid, "pipeline"))
            n_new += upsert_card(col, kind, cid, origem, ots, brief, grupo=grupo,
                                 opportunity_id=o["id"], stage=stage, existing=existing)

    # (definições usadas pelas colunas 7 e 3 — Follow Up/Quote Sent + tasks por contato)
    fu_opps = {o["contactId"]: o for o in paged_opps(rules.STAGES["Follow Up"])
               if o.get("status") == "open"}
    qs_opps = {o["contactId"]: o for o in paged_opps(rules.STAGES["Quote Sent"])
               if o.get("status") == "open"}

    # ---- fonte da verdade das tasks (regra Rafael 10/jul): painel de tasks do GHL.
    # 1 busca paginada substitui ~450 GETs por contato. None = API falhou → nenhum
    # card de task é criado NEM fechado neste ciclo (segurança contra fechamento falso).
    open_tasks = location_open_tasks()
    open_tasks_by_contact = {}
    open_task_by_id = {}
    if open_tasks is not None:
        for t in open_tasks:
            tid = t.get("_id") or t.get("id")
            if tid:
                open_task_by_id[tid] = t
            if t.get("contactId") and t.get("dueDate"):
                open_tasks_by_contact.setdefault(t["contactId"], []).append(t)
    # tag de responsável: nomes conhecidos do config + o resto da API de users
    assignee_names = {cfg["eugene_user_id"]: "Eugene", cfg["rafael_user_id"]: "Rafael"}
    for alias in cfg.get("rafael_aliases", []):
        assignee_names[alias] = "Rafael"
    try:
        ru = ghl.get("/users/", {"locationId": ghl.LOCATION_ID})
        if ru.status_code == 200:
            for u in ru.json().get("users", []):
                nm = ((u.get("firstName") or u.get("name") or "").strip().split() or ["—"])[0]
                assignee_names.setdefault(u.get("id"), nm)
    except Exception:
        pass
    upcoming_days = W.get("task_upcoming_days", 7)

    # ---- col7: SÓ VERMELHOS — Follow Up e Quote Sent SEM task (atenção imediata) ----
    for fu_stage, notask_kind, stage_opps in (("Follow Up", "followup_notask", fu_opps),
                                              ("Quote Sent", "quote_notask", qs_opps)):
        for cid, o in stage_opps.items():
            if cid in appt_cids:
                continue  # regra Peter: appointment marcado → coluna 5 governa
            ots = parse_ts(o.get("lastStageChangeAt") or o.get("updatedAt")) or now
            if (now - ots).days > W["pipeline_days"]:
                continue  # envelhecido → warm-up cuida
            if open_tasks is not None:
                pend = open_tasks_by_contact.get(cid, [])
            else:  # busca global falhou → fonte por contato (confiável, só mais cara)
                pend = [t for t in (contact_tasks(cid) or [])
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

    # ---- col3: ESPELHO DO PAINEL DE TASKS (regra Rafael 10/jul). TODA task pendente
    # do GHL vira card — vencida (vermelho) · do dia · próxima (janela de N dias) —
    # de TODOS os usuários (tag de responsável no card: um cobre o outro), e
    # INDEPENDENTE do stage: lead em Lost com task aberta é warm up, continua aqui.
    # Cores por contexto: verde=Quote Sent · azul=Follow Up · amarelo=task avulsa. ----
    if open_tasks is not None:
        today_et = dt.datetime.now(ET).date()
        upcoming_lim = today_et + dt.timedelta(days=upcoming_days)
        for t in open_tasks:
            tid = t.get("_id") or t.get("id")
            cid = t.get("contactId")
            due = parse_ts(t.get("dueDate")) if t.get("dueDate") else None
            if not (tid and cid and due):
                continue
            d = due.astimezone(ET).date()
            if d > upcoming_lim:
                continue  # longe demais: entra sozinha quando a janela alcançar
            days_over = (today_et - d).days
            if d < today_et:
                want_grupo, label = "overdue", f"overdue {days_over}d"
            elif d == today_et:
                want_grupo, label = None, "due today"
            else:
                want_grupo, label = "upcoming", f"upcoming {d:%b %d}"
            if cid in qs_opps:
                kind, pref = "quote_task", "QUOTE SENT"
            elif cid in fu_opps:
                kind, pref = "followup", "Follow Up"
            else:
                kind, pref = "task", "Task"
            who = assignee_names.get(t.get("assignedTo") or "", "Unassigned")
            origem_txt = f"{pref} · task \"{(t.get('title') or '').strip()[:36]}\" · {label}"
            # 1 card por TASK, sempre refletindo o estado ATUAL (recolor vencida→vermelho,
            # do dia→normal, reagendada→upcoming). Duplicatas da era "1 card por contato"
            # são fechadas pelo loop de resolução (task_id que sumiu da lista pendente).
            exlist = sb._sb("GET", f"board_cards?status=eq.open&task_id=eq.{tid}"
                                   "&select=id,grupo,origem,kind,assignee"
                                   "&order=created_at.asc") or []
            if exlist:
                keep = exlist[0]
                patch = {}
                if keep.get("grupo") != want_grupo:
                    patch["grupo"] = want_grupo
                if keep.get("origem") != origem_txt:
                    patch["origem"] = origem_txt
                if keep.get("kind") != kind:
                    patch["kind"] = kind
                if keep.get("assignee") != who:
                    patch["assignee"] = who
                if patch:
                    patch["origem_ts"] = iso(due)
                    sb._sb("PATCH", f"board_cards?id=eq.{keep['id']}", json=patch)
                for extra in exlist[1:]:
                    resolve_card(extra, "dedup — one card per task", "")
            else:
                brief = contact_brief(cid)
                if not ok_contact(cid, brief):
                    continue
                n_new += upsert_card(3, kind, cid, origem_txt, due, brief,
                                     task_id=tid, grupo=want_grupo,
                                     assignee=who, dedup_task=True)
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
            # 16/jul: nunca-ligado NÃO mora no fundo — topo do reaquecimento, logo
            # depois dos reschedules. (faxina "never responded" = respondido por SMS
            # é outra coisa; nunca-LIGADO é lead que a loja nunca tentou por voz.)
            if called_cids is not None and cid not in called_cids:
                pool.append({"cid": cid, "tier": 1,
                             "score": 10**9 + ots.timestamp(), "ots": iso(ots),
                             "nome": nm, "veh": veh, "grupo": "never_called",
                             "origem": f"NEVER CALLED · lead from {ots:%b %d}",
                             "opp": opp_id})
                continue
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
                               grupo=p.get("grupo") or GRUPOS[p["tier"]],
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
                if opr.status_code == 200:  # API OK: só então decide fechar
                    cur = {rules.STAGE_BY_ID.get(o.get("pipelineStageId"))
                           for o in opr.json().get("opportunities", [])
                           if o.get("status") == "open"}
                    if card["stage"] not in cur:
                        resolve_card(card, "stage moved", "")
                        resolutions += 1
                        continue
                # API falhou (timeout/429) → NÃO fecha por engano; tenta no próximo ciclo
            elif card["stage"] not in stage_now.get(cid, set()):
                resolve_card(card, "stage moved", "")
                resolutions += 1
                continue
        # vermelhos de task faltando: somem quando a task com data EXISTE
        if kind in ("followup_notask", "quote_notask"):
            if open_tasks is not None:
                has_task = bool(open_tasks_by_contact.get(cid))
            else:  # busca global falhou → fonte por contato
                has_task = any(not t.get("completed") and t.get("dueDate")
                               for t in (contact_tasks(cid) or []))
            if has_task:
                resolve_card(card, "task created", "")
                resolutions += 1
            continue
        # cards de TASK (espelho, 10/jul): fecham SÓ quando a task sai da lista de
        # pendentes do GHL (concluída/apagada) ou é reagendada além da janela de
        # próximas (volta sozinha quando a data se aproximar). Stage NÃO fecha:
        # lead em Lost com task aberta = warm up, o card fica (regra Rafael 10/jul,
        # revoga a regra Lost/Won de 09/jul). Recolor é feito no loop de criação.
        if kind in ("task", "followup", "quote_task") and card.get("task_id"):
            if open_tasks is None:
                continue  # busca global falhou → NÃO fecha por engano; tenta depois
            tk = open_task_by_id.get(card["task_id"])
            if tk is None:
                resolve_card(card, "task completed", "")
                resolutions += 1
                continue
            due2 = parse_ts(tk.get("dueDate")) if tk.get("dueDate") else None
            if due2 and due2.astimezone(ET).date() > \
                    dt.datetime.now(ET).date() + dt.timedelta(days=upcoming_days):
                resolve_card(card, "task rescheduled — returns when its date is close", "")
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
            for t in (contact_tasks(cid) or []):
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
        # 4) Lost · ou avanço de stage (a disposição da call moveu o lead na cadência)
        stage_moved = False
        if not resolved:
            opr = ghl.get("/opportunities/search", {"location_id": ghl.LOCATION_ID,
                                                    "contact_id": cid, "limit": 5})
            for o in (opr.json().get("opportunities", []) if opr.status_code == 200 else []):
                if rules.STAGE_BY_ID.get(o.get("pipelineStageId")) == "Lost" \
                        and parse_ts(o.get("updatedAt")) and parse_ts(o.get("updatedAt")) > cts:
                    resolved = "marked Lost"
                    break
                # STAGE AVANÇOU DEPOIS DA CALL (report 09/jul Shandor): a disposição
                # "No Answer" (workflow ladder) moveu o lead pra frente. ISSO é a
                # resolução "moved to next stage" — vale mesmo p/ call lida como
                # 'atendida', porque um voicemail de 56s é logado como completed/56s e
                # engana a duração. Sinal confiável: lastStageChangeAt do opp > a call.
                lsc = parse_ts(o.get("lastStageChangeAt"))
                if lsc and lsc > cts:
                    stage_moved = True
                    break
        # 5) DISPOSIÇÃO registrada depois da call (webhook type=disposition, 10/jul):
        # o clique do atendente no fim da chamada é a FONTE DA VERDADE do outcome
        # (a API não expõe — chega via workflow Disposition:* → ghl_events).
        # no_answer/voicemail = NÃO houve conversa → mesmo efeito do stage_moved
        # (limpa o vermelho e corrige a call p/ não-atendida); os demais = resolução.
        if not resolved and not stage_moved:
            evs = sb._sb("GET", f"ghl_events?type=eq.disposition&contact_id=eq.{cid}"
                                f"&created_at=gte.{iso(cts)}"
                                "&select=payload&order=created_at.desc&limit=1") or []
            if evs:
                d = ((evs[0].get("payload") or {}).get("_disposition") or "").lower()
                if d in ("no_answer", "voicemail"):
                    stage_moved = True
                elif d:
                    resolved = f"disposition: {d.replace('_', ' ')}"
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
        elif stage_moved:
            # a call foi um NO ANSWER (moveu o lead na cadência). NÃO fecha o card do
            # stage ATUAL — o Eugene ainda liga no slot novo. Só apaga o vermelho e
            # corrige a call p/ não-atendida, pra não voltar a cobrar categorização.
            if card.get("unres") or card.get("unres_call_answered"):
                sb._sb("PATCH", f"board_cards?id=eq.{card['id']}",
                       json={"unres": False, "unres_call_answered": False})
                card["unres"] = False
                card["unres_call_answered"] = False
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

    # ---- 8. CONFIRMAÇÕES D-2 (regra Rafael 16/07): booking sem confirmação humana
    # vira no-show — o Rafael assumiu as confirmações PESSOALMENTE. Todo dia, no 1º
    # ciclo depois das 8h ET, ele recebe por SMS a lista dos appointments de DAQUI A
    # 2 DIAS (nome, fone, carro, horário) pra ligar confirmando.
    try:
        confirm_digest_d2()
    except Exception as e:
        log(f"[warn] digest de confirmações D-2 falhou (não derruba o ciclo): {e}")

    # ---- 9. RESGATE DE NO-SHOW (regra Rafael 16/07): no-show novo recebe a mensagem
    # padrão do Rafael ANTES de virar reschedule — pessoal, com saída honrosa e
    # pergunta concreta de agenda. 1 SMS por evento, nunca re-dispara.
    try:
        noshow_rescue()
    except Exception as e:
        log(f"[warn] resgate de no-show falhou (não derruba o ciclo): {e}")

    # ---- 10. RODÍZIO DE NÚMEROS (regra Rafael 16/07): número ativo do Eugene bateu
    # 45 outbound no dia → SMS pros dois + banner no topo do board dizendo PRA QUAL
    # número trocar. Banner some sozinho quando a troca acontece (ou no dia seguinte).
    try:
        rotation_watch(calls)
    except Exception as e:
        log(f"[warn] vigia do rodízio falhou (não derruba o ciclo): {e}")

    sb._sb("POST", "config?on_conflict=key",
           headers_extra={"Prefer": "resolution=merge-duplicates"},
           json={"key": "board_state", "value": {"last_scan": iso(now)}})
    log(f"ciclo ok: +{n_new} cards · {resolutions} resoluções · "
        f"válidas Eugene hoje: {sum(1 for a in att if a['valid'])}")
    _cache_save()  # persiste o cache TTL (perfil/tasks) p/ o próximo ciclo


def _staff_contact_id(phone, name):
    """Contato de staff no GHL (upsert por telefone — não duplica)."""
    r = ghl.post("/contacts/upsert",
                 {"locationId": ghl.LOCATION_ID, "phone": phone,
                  "firstName": name, "tags": ["staff"]})
    if r.status_code not in (200, 201):
        return None
    return ((r.json() or {}).get("contact") or {}).get("id")


def rotation_watch(calls):
    """Conta outbound por número (dedupe por msg id) e avisa a troca aos 45 no ativo."""
    import os
    day = f"{dt.datetime.now(ET):%Y-%m-%d}"
    pool_rows = sb._sb("GET", "config?key=eq.rotation_pool&select=value") or []
    pool = (pool_rows[0]["value"] if pool_rows else None) or \
        ["+19543145029", "+19543352725", "+17543317204", "+19547383458"]
    # teto por número (config rotation_caps): número novo aquece com teto menor
    caps_rows = sb._sb("GET", "config?key=eq.rotation_caps&select=value") or []
    caps = (caps_rows[0]["value"] if caps_rows else None) or {}
    st_rows = sb._sb("GET", "config?key=eq.rotation_counts&select=value") or []
    st = (st_rows[0]["value"] if st_rows else None) or {}
    if st.get("day") != day:
        st = {"day": day, "counts": {}, "seen": [], "notified": []}
    seen = set(st.get("seen") or [])
    counts = st.get("counts") or {}
    for c in calls:
        if c.get("direction") != "outbound" or not c.get("id") or c["id"] in seen:
            continue
        frm = c.get("from_num")
        if not frm:
            continue
        seen.add(c["id"])
        counts[frm] = counts.get(frm, 0) + 1
    st["seen"] = sorted(seen)[-4000:]
    st["counts"] = counts

    active = None  # número de saída ATUAL do Eugene (lcPhone — leitura via API)
    try:
        r = ghl.get(f"/users/?locationId={ghl.LOCATION_ID}")
        for u in (r.json().get("users") or []):
            nome = f"{u.get('name') or ''} {u.get('firstName') or ''}".lower()
            if "eugene" in nome:
                active = (u.get("lcPhone") or {}).get(ghl.LOCATION_ID)
    except Exception:
        pass

    notice_rows = sb._sb("GET", "config?key=eq.board_notice&select=value") or []
    notice = notice_rows[0]["value"] if notice_rows else None
    # banner se limpa sozinho: dia virou OU Eugene já está no número recomendado
    if notice and (notice.get("day") != day or (active and active == notice.get("next"))):
        sb._sb("POST", "config?on_conflict=key",
               headers_extra={"Prefer": "resolution=merge-duplicates"},
               json={"key": "board_notice", "value": {}})
        log("rodízio: troca detectada/dia novo — banner limpo")

    cap_active = caps.get(active, 45) if active else 45
    if active and counts.get(active, 0) >= cap_active and active not in (st.get("notified") or []):
        # próximo: número do pool ainda ABAIXO do próprio teto, com menor uso hoje
        cands = [p for p in pool if p != active and counts.get(p, 0) < caps.get(p, 45)]
        nxt = min(cands, key=lambda p: counts.get(p, 0)) if cands else None
        if nxt:
            st.setdefault("notified", []).append(active)
            sb._sb("POST", "config?on_conflict=key",
                   headers_extra={"Prefer": "resolution=merge-duplicates"},
                   json={"key": "board_notice",
                         "value": {"kind": "rotate_number", "day": day, "active": active,
                                   "next": nxt, "count": counts.get(active, 0),
                                   "created": iso(now_utc())}})
            aviso = (f"ELITE: o numero de saida {active} bateu {counts.get(active, 0)} "
                     f"calls hoje. TROCA AGORA para {nxt} — Settings > My Staff > "
                     "Eugene > Phone.")
            for phone, who in ((os.environ.get("EUGENE_PHONE"), "Eugene"),
                               (os.environ.get("RAFAEL_PHONE"), "Rafael")):
                if phone:
                    cid = _staff_contact_id(phone, who)
                    if cid:
                        ghl.post("/conversations/messages",
                                 {"type": "SMS", "contactId": cid, "message": aviso})
            log(f"rodízio: {active} bateu {counts.get(active, 0)} — trocar pra {nxt}, avisos enviados")

    sb._sb("POST", "config?on_conflict=key",
           headers_extra={"Prefer": "resolution=merge-duplicates"},
           json={"key": "rotation_counts", "value": st})


def confirm_digest_d2():
    """SMS diário pro Rafael com os appointments de D+2 (confirmação pessoal)."""
    import os
    rafael = (os.environ.get("RAFAEL_PHONE") or "").strip()
    if not rafael:
        return
    now_et = dt.datetime.now(ET)
    day_key = f"{now_et:%Y-%m-%d}"
    st_rows = sb._sb("GET", "config?key=eq.confirm_digest_d2&select=value") or []
    if now_et.hour < 8 or (st_rows and st_rows[0]["value"].get("day") == day_key):
        return
    alvo = (now_et + dt.timedelta(days=2)).date()
    ini = dt.datetime(alvo.year, alvo.month, alvo.day, tzinfo=ET)
    fim = ini + dt.timedelta(days=1)
    linhas = []
    for cal_id in sb.CALENDARS.values():
        r = ghl.get("/calendars/events", {"locationId": ghl.LOCATION_ID,
                                          "calendarId": cal_id,
                                          "startTime": int(ini.timestamp() * 1000),
                                          "endTime": int(fim.timestamp() * 1000)})
        if r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            if e.get("appointmentStatus") in ("cancelled", "invalid", "noshow", "showed") \
                    or not e.get("contactId"):
                continue
            st = parse_ts(str(e.get("startTime")))
            b = contact_brief(e["contactId"])
            nome = b.get("nome") or e.get("title") or "?"
            fone = b.get("phone") or "sem fone"
            veh = b.get("veh") or ""
            status = e.get("appointmentStatus") or "new"
            hora = f"{st.astimezone(ET):%I:%M%p}".lstrip("0").lower() if st else "?"
            linhas.append(f"• {hora} {nome} {fone}" + (f" — {veh}" if veh else "")
                          + (" [NAO CONFIRMADO]" if status != "confirmed" else ""))
    # marca o dia ANTES de enviar — reenvio manual é melhor que SMS duplicado em loop
    sb._sb("POST", "config?on_conflict=key",
           headers_extra={"Prefer": "resolution=merge-duplicates"},
           json={"key": "confirm_digest_d2",
                 "value": {"day": day_key, "count": len(linhas), "sent_at": iso(now_utc())}})
    if not linhas:
        log(f"digest D-2: sem appointments em {alvo:%d/%m} — nada a enviar")
        return
    cid = _staff_contact_id(rafael, "Rafael")
    if not cid:
        log("digest D-2: upsert do contato do Rafael falhou")
        return
    msg = (f"ELITE — CONFIRMACOES {alvo:%a %d/%m} (D-2):\n" + "\n".join(linhas[:12])
           + (f"\n(+{len(linhas)-12} mais no board)" if len(linhas) > 12 else "")
           + "\nLigar e confirmar cada um. No-show custa job.")
    r = ghl.post("/conversations/messages",
                 {"type": "SMS", "contactId": cid, "message": msg})
    log(f"digest D-2 enviado ({len(linhas)} appointments, status {r.status_code})")


def noshow_rescue():
    """SMS padrão do Rafael pra cada no-show NOVO (1x por evento, direto ao lead)."""
    st_rows = sb._sb("GET", "config?key=eq.noshow_rescue_state&select=value") or []
    state = st_rows[0]["value"] if st_rows else None
    seen = set((state or {}).get("seen") or [])
    first_run = state is None
    ini = now_utc() - dt.timedelta(days=5)
    novos = []
    for cal_id in sb.CALENDARS.values():
        r = ghl.get("/calendars/events", {"locationId": ghl.LOCATION_ID,
                                          "calendarId": cal_id,
                                          "startTime": int(ini.timestamp() * 1000),
                                          "endTime": int(now_utc().timestamp() * 1000)})
        if r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            eid = e.get("id")
            if not eid or e.get("appointmentStatus") != "noshow" or eid in seen \
                    or not e.get("contactId"):
                continue
            seen.add(eid)
            novos.append(e)
    enviados = 0
    if not first_run:  # 1ª rodada só marca o passado — nunca metralhar no-show antigo
        for e in novos:
            cid = e["contactId"]
            b = contact_brief(cid)
            if (b.get("dnd")) or not b.get("phone"):
                continue
            first = (b.get("nome") or "").split(" ")[0] or "there"
            carro = b.get("veh") or b.get("interest") or "your car"
            msg = (f"Hey {first}. This is Rafael from Elite Premium Detailing. "
                   f"We had you down for the {carro} and I blocked shop time for it — "
                   "I'd hate for you to lose the slot. If the timing changed, no problem: "
                   "what day works better this week? I'll handle your car personally. "
                   "Feel free to call or text me back. Thank you!")
            r = ghl.post("/conversations/messages",
                         {"type": "SMS", "contactId": cid, "message": msg})
            if r.status_code in (200, 201):
                enviados += 1
                sb._sb("PATCH", f"board_cards?status=eq.open&contact_id=eq.{cid}",
                       json={"last_note": "No-show rescue SMS sent (Rafael) — aguardando resposta"})
    sb._sb("POST", "config?on_conflict=key",
           headers_extra={"Prefer": "resolution=merge-duplicates"},
           json={"key": "noshow_rescue_state",
                 "value": {"seen": sorted(seen)[-500:], "updated": iso(now_utc())}})
    if novos:
        log(f"resgate no-show: {len(novos)} novos, {enviados} SMS enviados"
            + (" (1ª rodada: só semeou o estado)" if first_run else ""))


if __name__ == "__main__":
    cycle(full_task_pass="--full" in sys.argv)
