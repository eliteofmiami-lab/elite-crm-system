"""
FAXINA DE DIA ZERO (PLANO_GERAL §B) — inventário do passivo, por categoria, com
contagens e listas prontas para BULK ACTION MANUAL do Rafael no GHL.
Somente leitura; o painel não escreve nada.
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
import ghl  # noqa: E402
from brain import rules  # noqa: E402
from board_sync import paged_opps, parse_ts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GHL_LINK = "https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/"
now = dt.datetime.now(dt.timezone.utc)


def bucket_opps():
    cats = {"new_leads_7d": [], "stalled_30d": [], "stalled_90d": []}
    stages_ativos = ["New Lead", "HOT LEADS", "Contact 1 (AM)", "Contact 1 (PM)",
                     "Contact 2 (AM)", "Contact 2 (PM)", "Contact 3 (AM)",
                     "Contact 3 (PM)", "Follow Up"]
    for stage in stages_ativos:
        for o in paged_opps(rules.STAGES[stage]):
            ts = parse_ts(o.get("lastStageChangeAt") or o.get("updatedAt") or o.get("createdAt"))
            if not ts:
                continue
            days = (now - ts).days
            item = (o.get("name") or "—", stage, days, o["contactId"])
            if stage == "New Lead" and days > 7:
                cats["new_leads_7d"].append(item)
            if days > 90:
                cats["stalled_90d"].append(item)
            elif days > 30:
                cats["stalled_30d"].append(item)
    return cats


def main():
    cats = bucket_opps()
    lost = paged_opps(rules.STAGES["Lost"])
    lost_old = [(o.get("name") or "—", "Lost", (now - (parse_ts(o.get("updatedAt")) or now)).days,
                 o["contactId"]) for o in lost
                if (now - (parse_ts(o.get("updatedAt")) or now)).days > 90]

    m = [f"# FAXINA_DIA_ZERO — inventário do passivo · {now:%Y-%m-%d}",
         "",
         "Listas prontas para **bulk action manual no GHL** (Contacts → filtro → seleção em",
         "massa). O painel NÃO escreve — quem move é você/Eugene, em minutos.",
         "",
         "## Resumo",
         f"| Categoria | Contagem | Proposta |",
         f"|---|---|---|",
         f"| New Leads parados >7 dias | {len(cats['new_leads_7d'])} | viram ração do Warm up (automático — já no painel) |",
         f"| Stages ativos parados 31–90 dias | {len(cats['stalled_30d'])} | ração do Warm up (automático) |",
         f"| Stages ativos parados >90 dias | {len(cats['stalled_90d'])} | **bulk → Lost 'no response'** (proposta) |",
         f"| Lost sem atividade >90 dias | {len(lost_old)} | manter Lost; fora do Warm up ativo |",
         ""]
    for title, rows in (("Stages ativos parados >90 dias (candidatos ao bulk → Lost)",
                         sorted(cats["stalled_90d"], key=lambda x: -x[2])),
                        ("New Leads parados >7 dias", sorted(cats["new_leads_7d"], key=lambda x: -x[2])),
                        ("Stages ativos parados 31–90 dias", sorted(cats["stalled_30d"], key=lambda x: -x[2]))):
        m.append(f"## {title} · {len(rows)}")
        m.append("")
        for nome, stage, days, cid in rows[:200]:
            m.append(f"- {nome} · {stage} · parado {days}d · [abrir]({GHL_LINK}{cid})")
        if len(rows) > 200:
            m.append(f"- … +{len(rows) - 200} (lista completa sob pedido)")
        m.append("")
    m += ["## Decisões que faltam de você (PLANO_GERAL §E)",
          "1. Corte do bulk: >90 dias sem resposta → Lost 'no response' — confirma?",
          "2. Janelas: 3d / 7d / 14d / 30d / ração 20 — ajusta algo?",
          "3. Horário comercial seg–sáb 9–17 ET — confirma?",
          "4. Textos dos 3 SMS fora de horário (GUIA_WORKFLOWS_FORA_DE_HORARIO.md) — ajusta?"]
    (ROOT / "FAXINA_DIA_ZERO.md").write_text("\n".join(m))
    print(f"FAXINA_DIA_ZERO.md: >90d={len(cats['stalled_90d'])} · NL>7d={len(cats['new_leads_7d'])}"
          f" · 31-90d={len(cats['stalled_30d'])} · Lost>90d={len(lost_old)}")


if __name__ == "__main__":
    main()
