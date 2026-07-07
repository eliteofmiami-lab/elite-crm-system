"""
Regras pós-chamada (spec 2.3 + adendo A1/A2) — decide AÇÕES; quem executa é writer.py.
Cada função retorna uma lista de ações [(func_writer, kwargs, motivo)] para o runner aplicar.
Nada aqui toca a rede.
"""
import re

# --- IDs reais (recon Fase 0) ---
NEW_PIPELINE_ID = "oUL5N3vxYqL13sBLrZUF"
STAGES = {  # ordem da cadência no New Pipeline
    "Great Cars": "22b4c971-42cb-4665-89dd-72966fe3a1cc",
    "New Lead": "5750c231-d5d4-4959-9112-0e2c78b1d2c2",
    "Contact 1 (AM)": "f1c50583-3e96-40ed-980c-de0e2b47a84c",
    "Contact 1 (PM)": "f6ad51ef-1973-4089-a119-e8dee6d065a6",
    "Contact 2 (AM)": "8e199abc-afb4-468e-8d0b-41922714e3ca",
    "Contact 2 (PM)": "9c10347f-188b-4c9b-abf2-ebbff8c49201",
    "Contact 3 (AM)": "f0480213-6014-4f7e-8b1f-0bf18255163e",
    "Contact 3 (PM)": "f4132e16-72fe-4fd7-af4d-046e80596e56",
    "Follow Up": "41e90499-e2f5-4a80-a772-9dc08dc86475",
    "Quote Sent": "708575b3-2b8e-4bd8-91cb-a2fb4774484a",
    "Appointment Booked": "77313fe9-fba1-4955-a62e-9094f1140fce",
    "Win": "8ecb943b-01d3-4d95-b3c2-7ece780dc512",
    "Lost": "125cfc10-4578-4275-86ae-5344aeea0676",
}
STAGE_BY_ID = {v: k for k, v in STAGES.items()}
# HOT LEADS criado via API em 2026-07-07 (autorizado pelo Rafael no chat), posição 1.
HOT_LEADS_STAGE_ID = "361f01f1-fd89-4e2f-8e74-eaf3a17b6cad"
STAGES["HOT LEADS"] = HOT_LEADS_STAGE_ID
STAGE_BY_ID[HOT_LEADS_STAGE_ID] = "HOT LEADS"

# Cadência no-answer: nunca retroceder; parar em Follow Up.
CADENCE = ["New Lead", "Contact 1 (AM)", "Contact 1 (PM)", "Contact 2 (AM)",
           "Contact 2 (PM)", "Contact 3 (AM)", "Contact 3 (PM)", "Follow Up"]
# Anti-regressão (A1): nunca mover se a opp está num destes
PROTECTED_STAGES = {"Quote Sent", "Appointment Booked", "Win"}

URABLE_LINK = re.compile(r"https?://(?:go\.|app\.)?urable\.com/\S+", re.I)
# A2: número de tracking Google Ads — CONFIRMADO pelo Rafael (2026-07-07, "Google Leads" no sistema)
GOOGLE_ADS_NUMBER = "+17544650696"


def next_cadence_stage(current_stage_name):
    """Próximo stage da cadência no-answer. None se não avança (fim ou stage fora da cadência)."""
    if current_stage_name not in CADENCE:
        return None
    i = CADENCE.index(current_stage_name)
    if i + 1 >= len(CADENCE):
        return None
    return CADENCE[i + 1]


def on_no_answer(opp):
    """Call não atendida → avançar cadência (dispara SMS automáticos). Nunca retroceder."""
    cur = STAGE_BY_ID.get(opp["pipelineStageId"])
    if cur in PROTECTED_STAGES:
        return []
    nxt = next_cadence_stage(cur)
    if not nxt:
        return []
    return [("update_opportunity",
             {"opp_id": opp["id"], "fields": {"pipelineStageId": STAGES[nxt]}},
             f"no-answer: cadência {cur} → {nxt}")]


def on_inbound_call(opp):
    """A1: call inbound → mover para HOT LEADS (exceto stages protegidos)."""
    if HOT_LEADS_STAGE_ID is None:
        return []  # stage ainda não existe; runner registra pendência
    cur = STAGE_BY_ID.get(opp["pipelineStageId"])
    if cur in PROTECTED_STAGES or cur == "HOT LEADS":
        return []
    return [("update_opportunity",
             {"opp_id": opp["id"], "fields": {"pipelineStageId": HOT_LEADS_STAGE_ID}},
             f"inbound call: {cur} → HOT LEADS")]


def on_great_car(opp, contact_id, score):
    """Lead novo com carro alvo → tag great-car + stage Great Cars (dispara CAPI)."""
    cur = STAGE_BY_ID.get(opp["pipelineStageId"])
    if score["car"] != 35 and score["car"] != 25:
        return []
    if cur in PROTECTED_STAGES or cur == "Great Cars":
        return []
    # tag "great cars" (com espaço) = a que o workflow 2.1 do GHL escuta (print do Rafael 2026-07-07)
    acts = [("add_tag", {"contact_id": contact_id, "tags": ["great cars"]}, "carro alvo")]
    if score["car"] == 35:
        acts.append(("update_opportunity",
                     {"opp_id": opp["id"], "fields": {"pipelineStageId": STAGES["Great Cars"]}},
                     "carro exótico/premium → Great Cars (CAPI)"))
    return acts


def on_quote_detected(opp, contact_id, link):
    """SMS outbound com link Urable → marcar quote enviada + mover p/ Quote Sent."""
    cur = STAGE_BY_ID.get(opp["pipelineStageId"])
    acts = [("update_opportunity",
             {"opp_id": opp["id"], "fields": {"customFields": [
                 {"key": "elite_quote_sent", "field_value": "true"},
                 {"key": "elite_quote_link", "field_value": link},
             ]}}, "quote Urable detectada nos SMS")]
    if cur not in ("Quote Sent", "Appointment Booked", "Win"):
        acts.append(("update_opportunity",
                     {"opp_id": opp["id"], "fields": {"pipelineStageId": STAGES["Quote Sent"]}},
                     f"quote enviada: {cur} → Quote Sent"))
    return acts


EUGENE_USER_ID = "EbVhbGHnGfuvbQurQoga"  # recon Fase 0


def on_missed_inbound(opp, contact_id, lead_name, called_number=None,
                      lead_phone=None, eugene_phone=None, rafael_phone=None):
    """Regra do Rafael (2026-07-07): inbound NÃO atendida → retorno o mais rápido possível.
    ALERTA DUPLO (Eugene + Rafael ao mesmo tempo) — quem pegar primeiro resolve.
    Task fica no Eugene (fila); SMS urgente vai pros dois celulares; card camada 1 no painel."""
    import datetime as dt
    due = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10)).isoformat()
    origem = " (Google Ads)" if called_number == GOOGLE_ADS_NUMBER else ""
    alerta = (f"🚨 MISSED CALL{origem}: {lead_name}"
              + (f" {lead_phone}" if lead_phone else "")
              + " — call back ASAP. First one to call handles it.")
    acts = [("create_task",
             {"contact_id": contact_id,
              "title": f"📞 URGENTE: retornar ligação perdida — {lead_name}{origem}",
              "body": "Lead ligou e não foi atendido. Regra: retornar o mais rápido possível. "
                      "Alerta enviado para Eugene E Rafael — quem fizer primeiro resolve.",
              "due_iso": due, "assigned_to": EUGENE_USER_ID},
             "inbound perdida → callback urgente")]
    for phone, who in ((eugene_phone, "Eugene"), (rafael_phone, "Rafael")):
        if phone:
            acts.append(("alert_staff",
                         {"phone": phone, "name": who, "message": alerta},
                         f"alerta urgente p/ {who} (inbound perdida)"))
    return acts


def on_reheat(opp, contact_id, touchpoints, score_known, had_any_response):
    """Reaquecimento: ≥5 toques sem NENHUMA resposta (≥8 se score ≥80) → Lost + tag."""
    if had_any_response:
        return []
    threshold = 8 if score_known >= 80 else 5
    if touchpoints < threshold:
        return []
    cur = STAGE_BY_ID.get(opp["pipelineStageId"])
    if cur in PROTECTED_STAGES or cur == "Lost":
        return []
    return [
        ("add_tag", {"contact_id": contact_id, "tags": ["reaquecimento"]}, "sem resposta após toques"),
        ("update_opportunity",
         {"opp_id": opp["id"], "fields": {"pipelineStageId": STAGES["Lost"]}},
         f"reaquecimento: {touchpoints} toques sem resposta → Lost (drip semanal)"),
    ]
