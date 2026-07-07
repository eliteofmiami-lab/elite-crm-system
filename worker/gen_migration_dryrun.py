"""GATE G1 — dry-run da migração ELITE ADS → New Pipeline. NÃO escreve nada.
Gera out/migration_dryrun.csv (opp → stage destino, motivo) + resumo."""
import json
import csv
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghl  # noqa: E402
import score  # noqa: E402

ADS = "gxSzYT8gC2sYY1QrXnDZ"
NEWP = "oUL5N3vxYqL13sBLrZUF"

# mapeamento de stages legado → New Pipeline (adendo A1: HOT LEADS → HOT LEADS)
MAP = {
    "GREAT CARS": "Great Cars",
    "NEW LEADS - CALL ASAP ": "New Lead",
    "HOT LEADS": "HOT LEADS",
    "FOLLOW UP - CHECK LEAD TASK": "Follow Up",
    "Day 1  - NO ANSWER 1": "Contact 1 (AM)",
    "Day 1 - SECOND CALL - AFTERNOON": "Contact 1 (PM)",
    "Day 2 - NO ANSWER2": "Contact 2 (AM)",
    "Day 2 - THIRD CALL-  AFTERNOON": "Contact 2 (PM)",
    "Day 3 - NO ANSWER3": "Contact 3 (AM)",
    "Day 3 - FOURTH CALL-  AFTERNOON": "Contact 3 (PM)",
    "APPOINTMENT BOOKED": "Appointment Booked",
}
AUTO_STAGES = set(MAP) - {"APPOINTMENT BOOKED"}  # migram por stage (se open)
NO_MIGRATE = {"NEVER ANSWERED - REMARKETING", "NOT INTERESTED "}

CUTOFF_90D = datetime(2026, 4, 8, tzinfo=timezone.utc)


def main():
    opps = json.load(open("out/opps_all.json"))
    pipes = json.load(open("out/pipelines.json"))["pipelines"]
    stage_name = {}
    for p in pipes:
        for s in p["stages"]:
            stage_name[s["id"]] = s["name"]

    ads = [o for o in opps if o["pipelineId"] == ADS]
    newp = [o for o in opps if o["pipelineId"] == NEWP]
    newp_phones = {o["phone"] for o in newp if o.get("phone")}

    rows = []
    need_appt = []
    for o in ads:
        st = stage_name.get(o["pipelineStageId"], "?")
        phone = o.get("phone")
        car, car_r = score.car_score(name=o.get("name"))
        dup = phone in newp_phones if phone else False

        if dup:
            decision, dest, why = "TAG dup-elite-ads (não move)", "", "telefone já existe no New Pipeline"
        elif o.get("status") != "open":
            decision, dest, why = "não migra", "", f"status={o.get('status')} (fechada no legado)"
        elif st in NO_MIGRATE:
            decision, dest, why = "não migra", "", f"stage {st.strip()} → base de cold calls (M5)"
        elif st in AUTO_STAGES:
            decision, dest, why = "MIGRA", MAP[st], f"stage ativo no legado ({st.strip()})"
        elif st == "APPOINTMENT BOOKED":
            if car == 35:
                decision, dest, why = "MIGRA", "Appointment Booked", f"carro alvo ({car_r})"
            else:
                decision, dest, why = "verificar-appt", "Appointment Booked", "depende de appointment ≤90d"
                need_appt.append(o)
        else:
            decision, dest, why = "não migra", "", f"stage desconhecido: {st}"
        rows.append({"opp": o, "stage_legado": st.strip(), "decision": decision,
                     "dest": dest, "why": why, "car": car})

    # checar appointments dos APPOINTMENT BOOKED indecisos (somente leitura)
    print(f"checando appointments de {len(need_appt)} contatos (APPOINTMENT BOOKED)...")
    appt_ok = {}
    for i, o in enumerate(need_appt, 1):
        r = ghl.get(f"/contacts/{o['contactId']}/appointments")
        ok = False
        if r.status_code == 200:
            for e in r.json().get("events", []):
                try:
                    t = datetime.strptime(e.get("startTime", "")[:19], "%Y-%m-%d %H:%M:%S")
                    if t.replace(tzinfo=timezone.utc) >= CUTOFF_90D:
                        ok = True
                        break
                except Exception:
                    continue
        appt_ok[o["id"]] = ok
        if i % 50 == 0:
            print(f"  ...{i}/{len(need_appt)}")
    for row in rows:
        if row["decision"] == "verificar-appt":
            if appt_ok.get(row["opp"]["id"]):
                row["decision"], row["why"] = "MIGRA", "appointment nos últimos 90 dias"
            else:
                row["decision"], row["dest"], row["why"] = ("não migra", "",
                    "appointment antigo (>90d) → base de cold calls (M5)")

    with open("out/migration_dryrun.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nome", "telefone", "stage_legado", "decisão", "stage_destino",
                    "motivo", "criado_em", "opportunityId", "contactId"])
        for r_ in sorted(rows, key=lambda x: (x["decision"], x["stage_legado"])):
            o = r_["opp"]
            w.writerow([o.get("contact_name") or o.get("name"), o.get("phone"),
                        r_["stage_legado"], r_["decision"], r_["dest"], r_["why"],
                        (o.get("createdAt") or "")[:10], o["id"], o["contactId"]])

    from collections import Counter
    c = Counter(r_["decision"] for r_ in rows)
    print("\n=== RESUMO DO DRY-RUN (nada foi movido) ===")
    for k, v in c.most_common():
        print(f"  {v:>5}  {k}")
    d = Counter((r_["stage_legado"], r_["dest"]) for r_ in rows if r_["decision"] == "MIGRA")
    print("\n=== PARA ONDE VAI (stage legado → destino) ===")
    for (a, b), v in sorted(d.items(), key=lambda kv: -kv[1]):
        print(f"  {v:>4}  {a} → {b}")


if __name__ == "__main__":
    main()
