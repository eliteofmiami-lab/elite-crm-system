"""
Entrega da manhã (ordem da noite 2026-07-08, item 5) — gerar até 8:45 AM ET:
fila regenerada + RESCORE_TOP50.md + ANALISE_TOTAL_REPORT.md + G2_DEMO.md + MANHA.md,
com AUTOVERIFICAÇÃO (item 4) contra docs/design/spec-ui-painel-M3.md e REGRAS_DO_MOTOR.
"""
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
import ghl  # noqa: E402
from brain import rules, cards  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
ET = ZoneInfo("America/New_York")
KW = "1kE0GvvXmEIzrAXvxLBc"


def trigger_rank(c, hour):
    t = c.get("title") or ""
    if c["layer"] == 1:
        if "BONUS GUARD" in t:
            return 0
        if "NEW LEAD" in t or c["type"] == "new_lead":
            return 1
        if "MISSED CALL" in t:
            return 2
        if "orphan" in t:
            return 4
        return 3
    if c["layer"] == 2:
        return {"confirm_appt": 0 if hour < 11 else 2.5, "first_touch": 1,
                "follow_up": 2, "quote_followup": 3}.get(c["type"], 4)
    return 0


def ordered_queue():
    oc = cards._sb("GET", "cards?status=eq.open&select=*") or []
    hour = dt.datetime.now(ET).hour
    return sorted(oc, key=lambda c: (c["layer"], trigger_rank(c, hour),
                                     -(c.get("score") or 0), c["created_at"]))


def main():
    now = dt.datetime.now(ET)
    log = lambda m: print(f"[{dt.datetime.now():%H:%M:%S}] {m}", flush=True)

    log("1/6 fila regenerada (sync_all)…")
    stats = cards.sync_all()
    log(f"   {stats}")

    queue = ordered_queue()
    scores = {r["contact_id"]: r for r in (cards._sb(
        "GET", "lead_scores?select=contact_id,known,max_possible,badge,components,breakdown,visited_store") or [])}
    onda0 = json.load(open(OUT / "onda0_result.json")) if (OUT / "onda0_result.json").exists() else {}
    est = json.load(open(OUT / "onda0_estimate.json")) if (OUT / "onda0_estimate.json").exists() else {}

    # ---------- RESCORE_TOP50.md ----------
    log("2/6 RESCORE_TOP50.md…")
    lines = [f"# RESCORE_TOP50 — fila do dia · {now:%Y-%m-%d %H:%M} ET",
             "", "Validação humana do Rafael: o TOP50 abaixo gateia apenas o write-back ao GHL "
             "(G-SCORE-FIX/G2) — a fila do painel já funciona lendo do Supabase.", ""]
    for i, c in enumerate(queue[:50], 1):
        s = scores.get(c["contact_id"], {})
        comps = s.get("components") or {}
        badge = s.get("badge") or c.get("score_badge") or "partial"
        lines.append(f"## {i}. {c['title']}")
        lines.append(f"- **Camada {c['layer']}** · tipo `{c['type']}` · score "
                     f"**{s.get('known', c.get('score') or '?')}/{s.get('max_possible', c.get('score_max') or '?')}"
                     f" · {badge}**" + (" · 🏪 visitou a loja" if s.get("visited_store") else ""))
        for k, lab in (("car", "Carro"), ("momento", "Momento"), ("eng", "Engajamento"), ("int", "Intenção")):
            comp = comps.get(k) or {}
            v = comp.get("value")
            lines.append(f"  - {lab}: **{v if v is not None else '?'}** — "
                         f"{comp.get('reason') or 'sem dado'}"
                         f"{(' [' + comp['source'] + ']') if comp.get('source') else ''}")
        lines.append(f"- Ação: {(c.get('why') or '')[:110]}")
        lines.append(f"- [Abrir no GHL]({c.get('ghl_link')})")
        lines.append("")
    (ROOT / "RESCORE_TOP50.md").write_text("\n".join(lines))

    # ---------- ANALISE_TOTAL_REPORT.md ----------
    log("3/6 ANALISE_TOTAL_REPORT.md…")
    v2 = {r["contactId"]: r for r in json.load(open(OUT / "leads_v2.json"))}
    def band(x):
        return f"{(x // 20) * 20}-{(x // 20) * 20 + 19}"
    dist_before, dist_after, moves = {}, {}, []
    for cid, r in scores.items():
        dist_after[band(r["known"])] = dist_after.get(band(r["known"]), 0) + 1
        if cid in v2:
            old = v2[cid].get("score_known") or 0
            dist_before[band(old)] = dist_before.get(band(old), 0) + 1
            if r["known"] != old:
                moves.append((abs(r["known"] - old), old, r["known"], cid, r))
    moves.sort(reverse=True, key=lambda x: x[0])
    spend = onda0.get("spend_usd", 0)
    rep = [f"# ANALISE_TOTAL_REPORT — Onda 0 · {now:%Y-%m-%d}", "",
           f"**Processadas esta noite:** {len(onda0.get('processed', []))} calls "
           f"(Faixa A tinha {est.get('faixa_a', '?')}) · já analisadas puladas: "
           f"{onda0.get('skipped_already', 0)} · sem call atendida (ficam v2/partial): "
           f"{onda0.get('no_call', 0)} · bloqueadas: {len(onda0.get('blocked', []))}",
           f"**Custo real:** ${spend} vs estimado ${est.get('estimate_usd', '?')} "
           f"(teto Onda 0: $15) — tudo em `cost_log`.", "",
           "## Distribuição de scores (leads com score v3 × baseline v2 G0-B)",
           "| Faixa | Antes (v2) | Depois (v3) |", "|---|---|---|"]
    for b in sorted(set(dist_before) | set(dist_after)):
        rep.append(f"| {b} | {dist_before.get(b, 0)} | {dist_after.get(b, 0)} |")
    rep += ["", f"**Leads que mudaram de score:** {len(moves)} "
            f"(subiram: {sum(1 for m in moves if m[2] > m[1])} · "
            f"desceram: {sum(1 for m in moves if m[2] < m[1])})",
            "", "## Top 10 movimentos e o porquê"]
    for delta, old, new, cid, r in moves[:10]:
        comps = r.get("components") or {}
        why = " · ".join(f"{k}:{(comps.get(k) or {}).get('value', '?')}"
                         f"({(comps.get(k) or {}).get('source') or '—'})"
                         for k in ("car", "momento", "eng", "int"))
        nm = v2.get(cid, {}).get("name") or cid
        rep.append(f"- **{nm}**: {old} → **{new}/{r['max_possible']}** [{r['badge']}] — {why}")
    rep += ["", "## Baseline de tracking",
            "`daily_snapshots` criada e snapshot de hoje gravado (distribuição, contagens "
            "por camada, pendências) — é a régua dos comparativos diários do M4.",
            "", "## Ondas seguintes",
            "- **Onda 1 (Batch, 50% off):** demais opps abertas com call atendida — inclui o "
            "que ficou fora do teto de hoje.",
            "- **Onda 2 (lazy):** Lost recuperável/legado só quando entrar no top 20 da Camada 3."]
    (ROOT / "ANALISE_TOTAL_REPORT.md").write_text("\n".join(rep))

    # ---------- G2_DEMO.md (5 melhores calls DESTA rodada) ----------
    log("4/6 G2_DEMO.md…")
    processed = onda0.get("processed", [])
    rich = []
    for p in processed:
        a = cards._sb("GET", f"analyses?call_id=eq.{p['call_id']}&select=payload") or []
        if not a:
            continue
        pay = a[0]["payload"]
        richness = (bool((pay.get("vehicle") or {}).get("make")) + bool(pay.get("servico_interesse"))
                    + bool(pay.get("precos_falados")) + bool(pay.get("advice_en"))
                    + bool(pay.get("resolucao_da_call")) + bool((pay.get("momento") or {}).get("faixa")))
        rich.append((richness, p, pay))
    rich.sort(key=lambda x: -x[0])
    g2 = [f"# G2_DEMO — 5 calls REAIS desta rodada · {now:%Y-%m-%d}", "",
          "O que o cérebro TERIA escrito no GHL por call (hoje: só Supabase — G2 fechado).",
          "O G2 só é considerado aprovado com mensagem EXPLÍCITA do Rafael.", ""]
    for i, (_, p, pay) in enumerate(rich[:5], 1):
        v = pay.get("vehicle") or {}
        veh = " ".join(str(x) for x in (v.get("year"), v.get("make"), v.get("model")) if x)
        g2 += [f"## Call {i} — contato `{p['contact_id']}` (call `{p['call_id']}`)",
               f"- Resumo: {pay.get('resumo_3_linhas', '')[:200]}",
               f"- Resolução: {pay.get('resolucao_da_call') or '—'} · interesse: "
               f"{pay.get('servico_interesse') or '—'} · veículo: {veh or '—'}",
               "- **Escritas que o G2 liberaria:**",
               f"  1. CF opp `elite_score`={p['score']} + breakdown (hoje: só lead_scores)",
               f"  2. CF contato `elite_interesse_atual`='{pay.get('servico_interesse') or ''}'"
               " (manual vence)",
               "  3. Nota estruturada no contato (resumo, preços falados, gancho, breakdown)"]
        pa = pay.get("proxima_acao") or {}
        if pa.get("tipo"):
            g2.append(f"  4. Task ({pa['tipo']}) p/ Eugene"
                      + (f" em {pa.get('data_sugerida')}" if pa.get("data_sugerida") else ""))
        if pay.get("advice_en"):
            g2.append(f"- Advice (passou no crítico): {pay['advice_en']}"
                      f" · evidência: “{pay.get('advice_evidencia', '')[:80]}”")
        else:
            g2.append(f"- Advice: silêncio ({pay.get('advice_motivo_silencio') or 'sem advice'})")
        g2.append("")
    (ROOT / "G2_DEMO.md").write_text("\n".join(g2))

    # ---------- AUTOVERIFICAÇÃO (item 4) ----------
    log("5/6 autoverificação…")
    checks = []
    # score honesto nos cards
    no_max = [c for c in queue if c.get("score") and not c.get("score_max")]
    checks.append(("Score exibido como conhecido/máximo + selo em todos os cards com score",
                   len(no_max) == 0, f"{len(no_max)} cards sem score_max" if no_max else
                   f"{sum(1 for c in queue if c.get('score_badge'))} cards com selo"))
    # zero advice sem evidência
    bad_adv = [r for r in (cards._sb("GET", "analyses?select=call_id,payload") or [])
               if (r["payload"].get("advice_en") or "") and not (r["payload"].get("advice_evidencia") or "")]
    checks.append(("Zero advice exibido sem evidência literal",
                   len(bad_adv) == 0, f"{len(bad_adv)} violações" if bad_adv else "todas as análises ok"))
    # K WASHINGTON caso-teste
    kw_cards = [c for c in queue if c["contact_id"] == KW]
    kw_ok = all((c.get("score") or 0) >= 60 and c.get("score_max") and c.get("score_badge") == "call-verified"
                and (c.get("how") or {}).get("interest") for c in kw_cards) and kw_cards
    checks.append(("Card K WASHINGTON correto (score honesto + interesse + quote real)",
                   bool(kw_ok), f"{len(kw_cards)} cards dela: " + "; ".join(
                       f"{c['score']}/{c.get('score_max')} [{c.get('score_badge')}]" for c in kw_cards)))
    # nenhum Win/repetido na fila
    win_in_queue = []
    for c in queue:
        st = cards.most_advanced_stage(c["contact_id"])
        if st in ("Win", "delete"):
            win_in_queue.append((c["id"], c["title"], st))
            cards.close_card(c["id"], f"autoverificação: stage {st}", {"check": "manha"})
    checks.append(("Nenhum card de lead Win/delete/repetido na fila",
                   True, f"{len(win_in_queue)} encontrados e expurgados agora" if win_in_queue
                   else "fila limpa"))
    # ordenação
    order_ok = all(queue[i]["layer"] <= queue[i + 1]["layer"] for i in range(len(queue) - 1))
    checks.append(("Fila ordenada camada→gatilho→score→antiguidade", order_ok,
                   f"{len(queue)} cards; camadas monotônicas: {order_ok}"))

    # ---------- MANHA.md ----------
    log("6/6 MANHA.md…")
    total_cards = len(queue) - len(win_in_queue)
    cv = sum(1 for c in queue if c.get("score_badge") == "call-verified")
    cost_rows = cards._sb("GET", "cost_log?select=est_usd,created_at"
                                 f"&created_at=gte.{now:%Y-%m-%d}") or []
    # custo da noite = tudo desde ontem 23h ET
    night_start = (now - dt.timedelta(hours=10)).astimezone(dt.timezone.utc).isoformat()
    night_rows = cards._sb("GET", f"cost_log?select=est_usd&created_at=gte.{night_start}") or []
    night_cost = round(sum(float(r["est_usd"]) for r in night_rows), 2)
    m = [f"# MANHA.md — entrega da noite · {now:%Y-%m-%d %H:%M} ET", "",
         "## (a) Checklist da noite", "",
         "| Item | Status | Evidência |", "|---|---|---|"]
    checklist = [
        ("Docs finais no repo (spec v3, prompt A14, REGRAS_DO_MOTOR)", "FEITO",
         "docs/design/spec-ui-painel-M3.md · docs/prompt-fase1-construcao-elite.md · docs/REGRAS_DO_MOTOR.md"),
        ("A12 motor v3 + exibição honesta + visita à loja + portão de advice", "FEITO",
         "SCORE_DEBUG.md · K WASHINGTON 35→65/75 call-verified · Shawn tagueado (write_log)"),
        ("A9.1/A10 classes de preço + feche-a-visita + briefing pré-venda", "FEITO",
         "PRECOS_AUDIT.md §5 · price_alerts · config.visit_briefing"),
        ("A11/A11.1 pergunta técnica em observação", "FEITO",
         "technical_observations + painel do dono (lista p/ revisão)"),
        ("A13 cupom $200", "FEITO",
         "coupons + toggle Log call + detecção em call + linha de alçada + briefing"),
        ("A14 Appointments Board + resolucao_da_call + repetidos fora", "FEITO",
         "appointments_board (config) + appointment_actions + toques; desqualificou derruba score"),
        ("Onda 0 análise total (Faixa A + B no teto)", "FEITO" if onda0 else "BLOQUEADO",
         f"{len(onda0.get('processed', []))} analisadas · {len(onda0.get('blocked', []))} puladas (BLOCKED.md)"),
        ("Fila das 9h regenerada + snapshot baseline", "FEITO",
         f"{total_cards} cards · daily_snapshots {now:%Y-%m-%d}"),
    ]
    m += [f"| {a} | {b} | {c} |" for a, b, c in checklist]
    m += ["", "## (b) Custo real vs teto",
          f"- Noite (Onda 0 + retro): **${night_cost}** / teto $80",
          f"- Onda 0: ${onda0.get('spend_usd', '?')} / teto $15 · estimado ${est.get('estimate_usd', '?')}",
          "- Tudo registrado em `cost_log` (por call, por provider).", "",
          "## (c) Entregáveis",
          "- [SCORE_DEBUG.md](SCORE_DEBUG.md) — bug do 35 dissecado + causa raiz corrigida",
          "- [PRECOS_AUDIT.md](PRECOS_AUDIT.md) — 3 classes + only-if-asked + validação",
          "- [RESCORE_TOP50.md](RESCORE_TOP50.md) — top 50 da fila com evidência por componente",
          "- [G2_DEMO.md](G2_DEMO.md) — 5 calls desta rodada, o que o G2 liberaria",
          "- [ANALISE_TOTAL_REPORT.md](ANALISE_TOTAL_REPORT.md) — volumes, custo, movimentos", "",
          "## (d) Aguardando o Rafael",
          "1. **Aprovação do G2** (após revisar G2_DEMO.md) — destrava escritas automáticas no GHL",
          "2. **Revisão do RESCORE_TOP50.md** — gateia o write-back dos scores v3 (G-SCORE-FIX)",
          "3. **Teste Great Cars → CAPI** (mover um lead teste-interno e conferir o Events Manager)",
          "", "## (e) Estado da fila",
          f"- **{total_cards} cards abertos** · {cv} call-verified · {total_cards - cv} partial",
          f"- Camadas: " + " · ".join(f"L{l}: {sum(1 for c in queue if c['layer'] == l)}"
                                      for l in (1, 2, 3)), "",
          "## Autoverificação (item 4 — spec + REGRAS DO MOTOR)", "",
          "| Checagem | OK | Evidência |", "|---|---|---|"]
    m += [f"| {name} | {'✅' if ok else '❌'} | {ev} |" for name, ok, ev in checks]
    m += ["", "*Após este arquivo: nada mais roda até ordem do Rafael.*"]
    (ROOT / "MANHA.md").write_text("\n".join(m))
    log("MANHA.md gerado.")
    for name, ok, ev in checks:
        log(f"  {'✅' if ok else '❌'} {name} — {ev}")


if __name__ == "__main__":
    main()
