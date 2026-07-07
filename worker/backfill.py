"""
Backfill de score dos últimos 40 dias — SOMENTE LEITURA.
Puxa contato + appointments + conversas de cada oportunidade da janela e calcula o score parcial.
Gera out/leads_enriched.json (dados brutos p/ os entregáveis).
"""
import json, re, time
import ghl

LOC = ghl.LOCATION_ID
pipes = {p["id"]: p["name"] for p in json.load(open("out/pipelines.json"))["pipelines"]}
stages = {}
for p in json.load(open("out/pipelines.json"))["pipelines"]:
    for s in p["stages"]:
        stages[s["id"]] = s["name"]

CF = {f["id"]: f for f in json.load(open("out/cf_contact.json"))["customFields"]}
CF_BY_KEY = {f["fieldKey"].replace("contact.", ""): f["id"] for f in CF.values()}

# ---------- classificador de veículo ----------
EXOTIC = ["porsche","mclaren","mc laren","lamborghini","rolls-royce","rolls royce","bentley",
          "ferrari","aston martin","maserati","lotus","bugatti","koenigsegg","pagani"]
PREMIUM_MODELS = ["amg","corvette","plaid","g63","g 63","g-wagon","g wagon","gt63","gt 63"]

def car_score(make, model, year, name):
    blob = " ".join(str(x or "").lower() for x in (make, model, name))
    yr = None
    m = re.search(r"20\d{2}", f"{year} {name}")
    if m: yr = int(m.group())
    # exótico
    if any(e in blob for e in EXOTIC):
        return 35, "exótico"
    # premium por modelo (AMG/Corvette/Plaid/G63)
    if any(pm in blob for pm in PREMIUM_MODELS):
        return 35, "premium"
    # BMW M / Audi RS / Mercedes AMG
    if re.search(r"\bbmw\b.*\bm[0-9]\b|\bm[0-9]\b.*\bbmw\b|\baudi\b.*\brs\b|\brs[0-9]\b", blob):
        return 35, "premium (M/RS)"
    if yr in (2025, 2026):
        return 25, f"ano {yr}"
    return 10, "comum"

CALL_ME = re.compile(r"call me|give me a call|you can call|please call|prefer.*call|call back|llame|"
                     r"reach me by phone|ligar|me liga", re.I)

def engagement(msgs):
    """Retorna (score, motivo) do maior sinal encontrado."""
    inbound_sms = [m for m in msgs if m.get("messageType") == "TYPE_SMS" and m.get("direction") == "inbound"]
    answered_call = any(m.get("messageType") == "TYPE_CALL" and (m.get("meta", {}).get("call", {}) or {}).get("duration")
                        for m in msgs)
    asked_call = any(CALL_ME.search(m.get("body") or "") for m in inbound_sms)
    if asked_call:
        return 25, "pediu ligação"
    if inbound_sms:
        return 15, "respondeu SMS"
    if answered_call:
        return 10, "atendeu chamada"
    return 0, "sem resposta"

URABLE_LINK = re.compile(r"(go\.urable\.com/\S+|app\.urable\.com/\S+|urable\.com/\S+)", re.I)


def get_msgs(contact_id):
    r = ghl.get("/conversations/search", {"locationId": LOC, "contactId": contact_id})
    if r.status_code != 200:
        return []
    convs = r.json().get("conversations", [])
    all_msgs = []
    for cv in convs:
        m = ghl.get(f"/conversations/{cv['id']}/messages")
        if m.status_code == 200:
            all_msgs += m.json().get("messages", {}).get("messages", [])
    return all_msgs


def main():
    opps = json.load(open("out/opps_40d.json"))
    out = []
    for i, o in enumerate(opps, 1):
        cid = o["contactId"]
        # contato
        cr = ghl.get(f"/contacts/{cid}")
        contact = cr.json().get("contact", {}) if cr.status_code == 200 else {}
        cfvals = {c["id"]: c.get("value") for c in contact.get("customFields", [])}
        make = cfvals.get(CF_BY_KEY.get("vehicle_make"))
        model = cfvals.get(CF_BY_KEY.get("vehicle_model"))
        year = cfvals.get(CF_BY_KEY.get("vehicle_year"))
        how_soon = cfvals.get(CF_BY_KEY.get("how_soon_are_you_looking_to_get_this_done"))
        services = cfvals.get(CF_BY_KEY.get("what_services_are_you_interested_in"))
        # appointments
        ar = ghl.get(f"/contacts/{cid}/appointments")
        appts = ar.json().get("events", []) if ar.status_code == 200 else []
        appt_statuses = [a.get("appointmentStatus") for a in appts]
        no_show = any(s == "noshow" for s in appt_statuses)
        has_appt = len(appts) > 0
        # mensagens / engajamento
        msgs = get_msgs(cid)
        eng, eng_reason = engagement(msgs)
        last_ts = max([m.get("dateAdded", "") for m in msgs] + [o.get("updatedAt", "")])
        urable_sent = any(URABLE_LINK.search(m.get("body") or "") for m in msgs)
        n_calls = sum(1 for m in msgs if m.get("messageType") == "TYPE_CALL")

        cs, cs_reason = car_score(make, model, year, o.get("name"))
        known = cs + eng          # Momento e Intenção = ? (sem transcrição)
        max_possible = 35 + 25    # Carro + Engajamento disponíveis sem transcrição

        out.append({
            "contactId": cid, "opportunityId": o["id"],
            "name": f"{contact.get('firstName','')} {contact.get('lastName','')}".strip() or contact.get("contactName") or o.get("name"),
            "phone": contact.get("phone"),
            "dateAdded": contact.get("dateAdded"), "createdAt": o.get("createdAt"),
            "source": o.get("source") or contact.get("source"),
            "pipeline": pipes.get(o["pipelineId"]), "stage": stages.get(o["pipelineStageId"]),
            "vehicle_make": make, "vehicle_model": model, "vehicle_year": year,
            "opp_name": o.get("name"), "how_soon": how_soon, "services": services,
            "car_score": cs, "car_reason": cs_reason,
            "momento": "?", "engagement": eng, "engagement_reason": eng_reason, "intencao": "?",
            "score_known": known, "score_max": max_possible,
            "has_appt": has_appt, "appt_statuses": appt_statuses, "no_show": no_show,
            "n_calls": n_calls, "urable_link_sent": urable_sent,
            "last_activity": last_ts,
            "tags": contact.get("tags", []),
            "link": f"https://app.gohighlevel.com/v2/location/{LOC}/contacts/detail/{cid}",
        })
        if i % 25 == 0:
            print(f"  ...{i}/{len(opps)}")
            json.dump(out, open("out/leads_enriched.json", "w"), ensure_ascii=False, indent=2)
    json.dump(out, open("out/leads_enriched.json", "w"), ensure_ascii=False, indent=2)
    print(f"OK: {len(out)} leads enriquecidos -> out/leads_enriched.json")


if __name__ == "__main__":
    main()
