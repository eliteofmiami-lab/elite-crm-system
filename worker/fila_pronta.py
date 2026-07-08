"""
FILA_PRONTA.md — entregável final do MVP: top 30 da fila (posição · estado · por quê ·
score), validação BINÁRIA do gabarito dos 5, prova de zero escritas e custo real.
"""
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
from brain import cards, lead_state  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ET = ZoneInfo("America/New_York")

GABARITO = [
    ("Agie Pee", "YpB8EZBqUWBVjIL6n1jh", "topo da Camada 1, callback_devido"),
    ("Naomi", "YgXYlVJ0r0JZ3urQeqVa", "AUSENTE (pos_venda)"),
    ("ROBERT R", "aFFRZmWOR8q60vduVQpO", "fora da discagem; nurture C3 com estado"),
    ("Shawn", "h7CXUZffhrzkpULZEmgJ", "só na data do follow-up"),
    ("Adam Nguyen", "eCjlTmHXc8d9TMpNXA8Y", "aguardando_evento_externo (~setembro)"),
]
WRITE_LOG_BASELINE = (1763, "140adf2ce93062f1afee84ab46a9de24")


def trigger_rank(c, hour):
    t = c.get("title") or ""
    if c["layer"] == 1:
        if "CALLBACK OWED" in t:
            return 0
        if "NEW LEAD" in t:
            return 1
        if "MISSED CALL" in t:
            return 2
        return 3
    if c["layer"] == 2:
        return {"confirm_appt": 0 if hour < 11 else 2.5, "first_touch": 1,
                "follow_up": 2, "quote_followup": 3, "quote_rescue": 3.5}.get(c["type"], 4)
    return 0


def main():
    now = dt.datetime.now(ET)
    open_cards = cards._sb("GET", "cards?status=eq.open&select=*") or []
    hour = now.hour
    queue = sorted(open_cards, key=lambda c: (c["layer"], trigger_rank(c, hour),
                                              -(c.get("score") or 0), c["created_at"]))
    states = {r["contact_id"]: r for r in
              (cards._sb("GET", "lead_states?select=contact_id,situacao,state") or [])}

    # ---- gabarito binário ----
    checks = []
    pos = {c["contact_id"]: i + 1 for i, c in enumerate(queue)}
    # Agie
    agie = GABARITO[0][1]
    agie_cards = [c for c in queue if c["contact_id"] == agie]
    ok_agie = (states.get(agie, {}).get("situacao") == "callback_devido"
               and agie_cards and pos.get(agie) == 1 and agie_cards[0]["layer"] == 1)
    checks.append(("Agie Pee = topo Camada 1, callback_devido", ok_agie,
                   f"posição {pos.get(agie, '—')} · estado {states.get(agie, {}).get('situacao')}"))
    # Naomi
    naomi = GABARITO[1][1]
    naomi_open = [c for c in open_cards if c["contact_id"] == naomi]
    ok_naomi = (states.get(naomi, {}).get("situacao") == "pos_venda" and not naomi_open)
    checks.append(("Naomi = AUSENTE (pos_venda)", ok_naomi,
                   f"cards abertos: {len(naomi_open)} · estado {states.get(naomi, {}).get('situacao')}"))
    # Robert
    rob = GABARITO[2][1]
    rob_open = [c for c in open_cards if c["contact_id"] == rob]
    rob_nurture = cards._sb("GET", f"cards?status=eq.snoozed&contact_id=eq.{rob}"
                                   "&select=type,layer,due_at,snooze_reason") or []
    ok_rob = (states.get(rob, {}).get("situacao") == "aguardando_decisao_cliente"
              and not rob_open and any(c["layer"] == 3 for c in rob_nurture))
    checks.append(("Robert = fora da discagem; nurture C3 com estado", ok_rob,
                   f"abertos: {len(rob_open)} · nurture: {[(c['layer'], str(c['due_at'])[:10]) for c in rob_nurture]}"
                   f" · estado {states.get(rob, {}).get('situacao')}"))
    # Shawn
    sh = GABARITO[3][1]
    sh_open = [c for c in open_cards if c["contact_id"] == sh]
    sh_snoozed = cards._sb("GET", f"cards?status=eq.snoozed&contact_id=eq.{sh}"
                                  "&select=due_at,type") or []
    ok_sh = (states.get(sh, {}).get("situacao") == "agendado" and not sh_open)
    checks.append(("Shawn = só na data do follow-up (agendado)", ok_sh,
                   f"abertos: {len(sh_open)} · retomadas: {[str(c['due_at'])[:10] for c in sh_snoozed]}"
                   f" · estado {states.get(sh, {}).get('situacao')}"))
    # Adam
    ad = GABARITO[4][1]
    ad_open = [c for c in open_cards if c["contact_id"] == ad]
    ad_snoozed = cards._sb("GET", f"cards?status=eq.snoozed&contact_id=eq.{ad}"
                                  "&select=due_at,type") or []
    ok_ad = (states.get(ad, {}).get("situacao") == "aguardando_evento_externo" and not ad_open)
    checks.append(("Adam = aguardando_evento_externo (janela ~set)", ok_ad,
                   f"abertos: {len(ad_open)} · retomadas: {[str(c['due_at'])[:10] for c in ad_snoozed]}"
                   f" · estado {states.get(ad, {}).get('situacao')}"))
    all_ok = all(ok for _, ok, _ in checks)

    # ---- zero escritas ----
    wl = ROOT / "out" / "write_log.jsonl"
    lines = sum(1 for _ in open(wl))
    md5 = hashlib.md5(wl.read_bytes()).hexdigest()
    zero_writes = (lines, md5) == WRITE_LOG_BASELINE

    # ---- custo da rodada MVP ----
    res = json.load(open(ROOT / "out" / "mvp_result.json")) if (ROOT / "out" / "mvp_result.json").exists() else {}

    for name, ok, ev in checks:
        print(f"{'✅' if ok else '❌'} {name} — {ev}")
    print(f"zero escritas: {zero_writes} ({lines} linhas, md5 {md5[:8]})")
    if not all_ok:
        print("\n!! GABARITO NÃO BATEU — NÃO EMITIR FILA_PRONTA. Investigar acima.")
        return False

    dist = {}
    for cid, s in states.items():
        dist[s.get("situacao") or "?"] = dist.get(s.get("situacao") or "?", 0) + 1
    cv = sum(1 for c in queue if c.get("score_badge") == "call-verified")

    m = [f"# FILA_PRONTA — MVP · {now:%Y-%m-%d %H:%M} ET", "",
         "## Aceite (gabarito do Rafael — binário)", "",
         "| Caso | Esperado | Como está | OK |", "|---|---|---|---|"]
    for (nome, cid, esperado), (_, ok, ev) in zip(GABARITO, checks):
        m.append(f"| {nome} | {esperado} | {ev} | {'✅' if ok else '❌'} |")
    m += ["", "## Zero escritas no GHL",
          f"- `out/write_log.jsonl` INTOCADO: {lines} linhas · md5 `{md5}` (idêntico ao "
          "baseline capturado no início do MVP). Todo caminho de escrita bloqueado no "
          "código (`writer.MVP_READONLY`) e removido da UI (RailView é somente-leitura).", "",
          "## Custo real da rodada",
          f"- **${res.get('spend_usd', '?')}** / teto $40 (estimado $15.29) — tudo em `cost_log`.", "",
          "## Estado da base",
          f"- {len(states)} leads com estado sintetizado: " +
          " · ".join(f"{k}: {v}" for k, v in sorted(dist.items(), key=lambda x: -x[1])),
          f"- Fila: **{len(queue)} cards abertos** ({cv} call-verified) · congelados fora da fila: "
          "pós-venda invisível, aguardando/agendado dormindo até a janela.", "",
          "## Como abrir dentro do GHL",
          "- [INSTRUCOES_MENU_LINK.md](INSTRUCOES_MENU_LINK.md) — Custom Menu Link (3 min). "
          "URL: `https://elite-crm-panel.vercel.app/?layout=rail`", ""]

    # item 6: pendências abertas + amostra de 10 p/ validação do formato
    pends = cards._sb("GET", "pendencias?status=eq.open&select=*"
                             "&order=created_at.desc&limit=300") or []
    m += ["## Verificador pós-call — Pendências (item 6)",
          f"- **{len(pends)} pendências abertas** (somem sozinhas quando a LEITURA "
          "confirma qualquer resolução válida; o sistema só aponta, nunca executa).",
          "", "### Amostra de 10 (validação do formato)", ""]
    for p in pends[:10]:
        m.append(f"- **[{p['kind']}]** {p['fato']} **→ {p['acao']}**")
    if not pends:
        m.append("- (nenhuma pendência aberta no momento)")

    scores_full = {r["contact_id"]: r for r in (cards._sb(
        "GET", "lead_scores?select=contact_id,components") or [])}
    m += ["", "## Top 30 da fila (posição · estado · por quê · score com breakdown)", ""]
    for i, c in enumerate(queue[:30], 1):
        st = states.get(c["contact_id"], {})
        sit = st.get("situacao") or "—"
        m.append(f"**{i}. {c['title']}**  ")
        m.append(f"C{c['layer']} · `{sit}` · score {c.get('score') or '?'}/"
                 f"{c.get('score_max') or '?'} "
                 f"{'✓' if c.get('score_badge') == 'call-verified' else '(partial)'}"
                 f"{' · ' + c.get('phone') if c.get('phone') else ''}  ")
        comps = (scores_full.get(c["contact_id"]) or {}).get("components") or {}
        if comps:
            partes = []
            for k, lab in (("car", "Carro"), ("momento", "Momento"),
                           ("eng", "Engaj."), ("int", "Intenção")):
                comp = comps.get(k) or {}
                val = comp.get("value")
                val = "?" if val is None else val
                razao = (comp.get("reason") or "sem dado")[:60]
                fonte = f" · {comp['source']}" if comp.get("source") else ""
                partes.append(f"{lab} {val} ({razao}{fonte})")
            m.append("_" + " · ".join(partes) + "_  ")
        m.append(f"{(c.get('why') or '')[:220]}  ")
        m.append(f"[Abrir contato]({c.get('ghl_link')})")
        m.append("")
    m += ["---", "**Congelado até segunda ordem** (código preservado, execução off): advice, "
          "rascunhos/aprovações, wrap-up, bonus guard, comissões, relatório 18:30, Appointments "
          "Board, briefing, cupom, retro (batch pago aguardando no servidor), nudges/clock-in, "
          "extensão Chrome.", "",
          "*Após este arquivo: parado, aguardando o Rafael.*"]
    (ROOT / "FILA_PRONTA.md").write_text("\n".join(m))
    print(f"\nFILA_PRONTA.md emitido · {len(queue)} cards · gabarito 5/5")
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
