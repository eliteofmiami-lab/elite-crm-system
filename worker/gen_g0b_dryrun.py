"""GATE G0-B: dry-run do write-back de score. NÃO escreve nada — só mostra o que SERIA gravado.
Gera out/writeback_dryrun_G0B.csv com 20 exemplos (lead -> campo -> valor -> endpoint)."""
import json, csv


def touchpoints(msgs):
    return sum(1 for m in msgs if m.get("direction") == "outbound"
              and m.get("messageType") in ("TYPE_SMS", "TYPE_CALL", "TYPE_EMAIL"))


def next_action(x, s):
    st = (x["stage"] or "").lower()
    if x["urable_link_sent"] and "win" not in st:
        return "Follow-up da quote enviada"
    if s["eng"] == 25:
        return "Ligar (pediu ligação / ligou inbound)"
    if s["car"] == 35:
        return "Ligar — carro alvo"
    if x["no_show"]:
        return "Reagendar (no-show)"
    return "Avançar contato"


def main():
    rows = json.load(open("out/leads_v2.json"))
    cache = json.load(open("out/messages_40d.json"))
    EP = "PUT /opportunities/{opportunityId}  (customFields)"
    out = []
    for x in rows[:20]:
        s = x["v2"]
        tp = touchpoints(cache.get(x["contactId"], []))
        writes = {
            "elite_score": f'{s["known"]}/{s["max_possible"]}',
            "elite_score_breakdown": s["breakdown"],
            "elite_quote_sent": "true" if x["urable_link_sent"] else "false",
            "elite_quote_link": "(link go.urable.com se houver)" if x["urable_link_sent"] else "",
            "elite_touchpoints": tp,
            "elite_next_action": next_action(x, s),
            "elite_sentimento": "(vazio — vem da análise de chamada, M2)",
        }
        for field, val in writes.items():
            out.append({
                "lead": x["name"], "opportunityId": x["opportunityId"],
                "campo": field, "valor_a_gravar": val, "endpoint": EP,
                "link_ghl": x["link"],
            })
    with open("out/writeback_dryrun_G0B.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lead", "opportunityId", "campo", "valor_a_gravar", "endpoint", "link_ghl"])
        w.writeheader(); w.writerows(out)
    print(f"dry-run G0-B: {len(out)} linhas ({len(out)//7} leads × 7 campos) -> out/writeback_dryrun_G0B.csv")
    print("Exemplo (1 lead):")
    for r in out[:7]:
        print(f'  {r["campo"]:24} = {r["valor_a_gravar"]}')


if __name__ == "__main__":
    main()
