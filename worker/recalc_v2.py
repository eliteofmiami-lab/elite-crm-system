"""Recalcula o score v2 dos leads dos 40 dias usando score.py + cache de mensagens.
Gera out/leads_score_v2.csv e out/leads_v2.json (para o dry-run de write-back)."""
import json, csv, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import score


def main():
    enriched = json.load(open("out/leads_enriched.json"))
    msgs_cache = json.load(open("out/messages_40d.json"))
    rows = []
    for x in enriched:
        msgs = msgs_cache.get(x["contactId"], [])
        s = score.compute(make=x["vehicle_make"], model=x["vehicle_model"],
                          year=x["vehicle_year"], opp_name=x["opp_name"],
                          how_soon=x["how_soon"], msgs=msgs)
        rows.append({**x, "v2": s})
    # ordenar por conhecido desc, depois carro
    rows.sort(key=lambda r: (-r["v2"]["known"], -r["v2"]["car"]))

    def veh(x):
        if x["vehicle_make"] or x["vehicle_model"] or x["vehicle_year"]:
            return " ".join(str(v) for v in (x["vehicle_year"], x["vehicle_make"], x["vehicle_model"]) if v)
        return x["opp_name"] or ""

    cols = ["nome", "telefone", "data_entrada", "veiculo", "pipeline", "stage",
            "carro", "momento", "engajamento", "intencao", "score_conhecido", "score_max",
            "breakdown", "how_soon", "tem_appointment", "no_show", "urable_link_enviado",
            "n_calls", "source", "ultima_atividade", "link_ghl"]
    with open("out/leads_score_v2.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for x in rows:
            s = x["v2"]
            w.writerow([
                x["name"], x["phone"], (x["createdAt"] or "")[:10], veh(x),
                x["pipeline"], x["stage"],
                f'{s["car"]} ({s["car_reason"]})',
                s["momento"] if isinstance(s["momento"], int) else "?",
                f'{s["eng"]} ({s["eng_reason"]})',
                f'{s["int"]} ({s["int_reason"]})' if isinstance(s["int"], int) else f'? ({s["int_reason"]})',
                s["known"], s["max_possible"], s["breakdown"],
                x["how_soon"] or "", "sim" if x["has_appt"] else "", "SIM" if x["no_show"] else "",
                "sim" if x["urable_link_sent"] else "", x["n_calls"], x["source"] or "",
                (x["last_activity"] or "")[:10], x["link"],
            ])
    json.dump(rows, open("out/leads_v2.json", "w"), ensure_ascii=False, indent=2)

    # resumo
    from collections import Counter
    print(f"leads: {len(rows)}")
    print("mudança de engajamento (v1→v2 inbound=25):",
          Counter(r["v2"]["eng_reason"] for r in rows))
    print("intenção (proxy):", Counter(
        (r["v2"]["int_reason"].split(":")[0] if isinstance(r["v2"]["int"], int) else "?")
        for r in rows))
    print("top 5 score conhecido:")
    for r in rows[:5]:
        print(f'  {r["v2"]["known"]}/{r["v2"]["max_possible"]}  {r["name"]}  [{r["v2"]["breakdown"]}]  {r["stage"]}')


if __name__ == "__main__":
    main()
