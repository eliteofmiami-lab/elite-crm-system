"""A3 — Auditoria de SMS por template/stage (SOMENTE LEITURA, não altera nada).
Agrupa SMS outbound por template normalizado, associa ao stage atual da opp (proxy),
e calcula volume, taxa de resposta (inbound do lead em ≤48h) e opt-out."""
import json, re
from datetime import datetime, timedelta
from collections import defaultdict, Counter

OPTOUT = re.compile(r"\bstop\b|unsubscribe|remove me|don'?t text|no thanks|not interested|"
                    r"pare|remover|não tenho interesse", re.I)


def parse(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def normalize(body, first_name, opp_name):
    t = body or ""
    t = re.sub(r"https?://\S+", "«link»", t)
    t = re.sub(r"go\.urable\.com/\S+", "«link»", t)
    # remove nome e tokens do veículo
    for tok in ([first_name] if first_name else []) + re.split(r"\s+", (opp_name or "")):
        if tok and len(tok) >= 3:
            t = re.sub(re.escape(tok), "«x»", t, flags=re.I)
    t = re.sub(r"\d{1,4}([:/.-]\d{1,4})*", "«n»", t)      # datas/horas/números
    t = re.sub(r"[A-Z][a-z]+ \d", "«dt»", t)               # "July 8"
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t[:90]


def main():
    enriched = json.load(open("out/leads_enriched.json"))
    cache = json.load(open("out/messages_40d.json"))
    meta = {}
    for x in enriched:
        meta.setdefault(x["contactId"], x)  # 1ª opp por contato

    tpl = defaultdict(lambda: {"vol": 0, "resp": 0, "optout": 0,
                               "stages": Counter(), "pipes": Counter(), "sample": ""})
    for cid, msgs in cache.items():
        info = meta.get(cid, {})
        fn = (info.get("name") or "").split(" ")[0]
        opp = info.get("opp_name")
        stage = info.get("stage"); pipe = info.get("pipeline")
        ms = sorted([m for m in msgs if m.get("dateAdded")], key=lambda m: m["dateAdded"])
        for i, m in enumerate(ms):
            if m.get("messageType") != "TYPE_SMS" or m.get("direction") != "outbound":
                continue
            body = m.get("body") or ""
            if not body.strip():
                continue
            key = normalize(body, fn, opp)
            rec = tpl[key]
            rec["vol"] += 1
            if not rec["sample"]:
                rec["sample"] = re.sub(r"\s+", " ", body).strip()[:160]
            rec["stages"][stage] += 1
            rec["pipes"][pipe] += 1
            # resposta do lead em ≤48h?
            t0 = parse(m["dateAdded"])
            if t0:
                for n in ms[i + 1:]:
                    tn = parse(n["dateAdded"])
                    if not tn or tn - t0 > timedelta(hours=48):
                        break
                    if n.get("direction") == "inbound" and n.get("messageType") in ("TYPE_SMS", "TYPE_CALL"):
                        rec["resp"] += 1
                        if n.get("messageType") == "TYPE_SMS" and OPTOUT.search(n.get("body") or ""):
                            rec["optout"] += 1
                        break

    items = sorted(tpl.items(), key=lambda kv: -kv[1]["vol"])
    lines = ["# SMS_CADENCE_AUDIT — cadência real de SMS (últimos 40 dias, somente leitura)",
             "",
             "> Reconstruído a partir das mensagens **efetivamente enviadas**. Templates normalizados "
             "(nome/veículo/links/números removidos p/ agrupar quase-idênticos).",
             "> **Stage = stage ATUAL da opp** (proxy) — o histórico exato de stage no momento do envio não "
             "é exposto pela API, então a associação é aproximada. Resposta = inbound do lead em ≤48h.",
             "> ⚠️ Nenhuma mensagem foi alterada. Revisão de copy é decisão do Rafael.",
             "",
             f"Total de templates distintos: **{len(items)}**. Mostrando os de maior volume.",
             ""]
    for key, r in items[:25]:
        rate = (100 * r["resp"] / r["vol"]) if r["vol"] else 0
        top_pipe = r["pipes"].most_common(1)[0][0] if r["pipes"] else "?"
        top_stages = ", ".join(f"{s}({n})" for s, n in r["stages"].most_common(3))
        lines += [
            f"### «{r['vol']} envios · {rate:.0f}% resposta{' · '+str(r['optout'])+' opt-out' if r['optout'] else ''}»",
            f"- **Pipeline predominante:** {top_pipe}",
            f"- **Stages (atuais) onde aparece:** {top_stages}",
            f"- **Amostra:** {r['sample']}",
            "",
        ]
    # ranking
    ranked = [ (k,v) for k,v in items if v["vol"] >= 5 ]
    best = sorted(ranked, key=lambda kv: -(kv[1]["resp"]/kv[1]["vol"]))[:5]
    worst = sorted(ranked, key=lambda kv: (kv[1]["resp"]/kv[1]["vol"]))[:5]
    lines += ["---", "", "## Ranking de performance (templates com ≥5 envios)", "",
              "**Melhores taxas de resposta:**"]
    for k, v in best:
        lines.append(f"- {100*v['resp']/v['vol']:.0f}% ({v['vol']} envios) — {v['sample'][:80]}")
    lines += ["", "**Piores taxas de resposta (candidatos a reescrever):**"]
    for k, v in worst:
        lines.append(f"- {100*v['resp']/v['vol']:.0f}% ({v['vol']} envios) — {v['sample'][:80]}")
    lines += ["", "## Recomendações",
              "- Manter os templates de topo (abertura + confirmação de appointment tendem a puxar resposta).",
              "- Reescrever os de baixa resposta com muito volume (desperdício de alcance).",
              "- Para associação exata SMS↔stage, o worker (M2) vai carimbar o stage no momento do envio "
              "em `elite_touchpoints`/nota — aí o próximo audit fica preciso.",
              ""]
    open("docs/SMS_CADENCE_AUDIT.md", "w").write("\n".join(lines))
    print(f"OK: {len(items)} templates -> docs/SMS_CADENCE_AUDIT.md")
    print("Top 5 por volume:")
    for k, v in items[:5]:
        print(f'  {v["vol"]:>4} envios · {100*v["resp"]/v["vol"]:.0f}% resp · {v["sample"][:70]}')


if __name__ == "__main__":
    main()
