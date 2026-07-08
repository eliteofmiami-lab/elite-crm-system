"""
Score v2 — Elite CRM.  Módulo puro (sem I/O de rede) usado pelo backfill e pelo worker.

Componentes (0-100):
  Carro       0-35  — sempre calculável a partir de make/model/year/nome.
  Momento     0-25  — só via transcrição de chamada ou nota. '?' até lá.
  Engajamento 0-25  — do histórico de conversas.
  Intenção    0-15  — via transcrição; enquanto não houver, PROXY por how_soon.

Score é sempre reportado como (conhecido, maximo_possivel, breakdown).
'?' significa "sem dado", NÃO zero.
"""
import re

# ----------------- Carro (0-35) -----------------
EXOTIC = ["porsche", "mclaren", "mc laren", "lamborghini", "rolls-royce", "rolls royce",
          "bentley", "ferrari", "aston martin", "maserati", "lotus", "bugatti",
          "koenigsegg", "pagani"]
PREMIUM_MODELS = ["amg", "corvette", "plaid", "g63", "g 63", "g-wagon", "g wagon",
                  "gt63", "gt 63", "rsq8", "rs q8", "type r", "type s"]


def car_score(make=None, model=None, year=None, name=None):
    blob = " ".join(str(x or "").lower() for x in (make, model, name))
    yr = None
    m = re.search(r"20\d{2}", f"{year or ''} {name or ''}")
    if m:
        yr = int(m.group())
    if any(e in blob for e in EXOTIC):
        return 35, "exótico"
    if any(pm in blob for pm in PREMIUM_MODELS):
        return 35, "premium"
    if re.search(r"\bbmw\b.*\bm[0-9]\b|\bm[0-9]\b.*\bbmw\b|\baudi\b.*\brs\b|\brs[0-9]\b", blob):
        return 35, "premium (M/RS)"
    if yr in (2025, 2026):
        return 25, f"ano {yr}"
    return 10, "comum"


# ----------------- Engajamento (0-25) -----------------
CALL_ME = re.compile(r"call me|give me a call|you can call|please call|prefer.*call|call back|"
                     r"reach me by phone|ligar|me liga|llame|llamar", re.I)


def engagement_from_messages(msgs):
    """v2: chamada INBOUND do lead = 25 (mesmo peso de 'pediu ligação')."""
    inbound_sms = [m for m in msgs if m.get("messageType") == "TYPE_SMS" and m.get("direction") == "inbound"]
    inbound_call = any(m.get("messageType") == "TYPE_CALL" and m.get("direction") == "inbound" for m in msgs)
    answered_call = any(m.get("messageType") == "TYPE_CALL"
                        and ((m.get("meta") or {}).get("call") or {}).get("duration")
                        for m in msgs)
    asked_call = any(CALL_ME.search(m.get("body") or "") for m in inbound_sms)
    if asked_call:
        return 25, "pediu ligação"
    if inbound_call:
        return 25, "ligou (inbound)"
    if inbound_sms:
        return 15, "respondeu SMS"
    if answered_call:
        return 10, "atendeu chamada"
    return 0, "sem resposta"


# ----------------- Intenção (0-15) -----------------
HOW_SOON_INTENT = {
    "as soon as possible": (15, "ASAP"),
    "within the next 2 weeks": (12, "≤2 semanas"),
    "within the next month": (8, "≤1 mês"),
    "not sure / just exploring": (3, "só explorando"),
}


def intent_from_how_soon(how_soon):
    """Proxy enquanto não há transcrição. Retorna (valor|'?', motivo)."""
    if not how_soon:
        return "?", "sem how_soon"
    key = how_soon.strip().lower()
    if key in HOW_SOON_INTENT:
        v, why = HOW_SOON_INTENT[key]
        return v, f"how_soon: {why}"
    return "?", f"how_soon não mapeado ({how_soon!r})"


# valores de intenção derivados de transcrição (SOBRESCREVEM o proxy)
INTENT_FROM_CALL = {"pediu_quote": 15, "sem_recuar": 15, "indeciso": 10, "so_pesquisando": 5}
# faixas de Momento derivadas de transcrição/nota
MOMENTO_FAIXA = {"recem_entregue": 25, "chegando": 25, "menos_3m": 20,
                 "mais_3m": 15, "mais_6m": 10, "mais_1a": 5}
# formulário Log call details (rótulos EN do painel) → faixa
MOMENTO_FORM = {"Just delivered / brand new": "recem_entregue", "Arriving soon": "chegando",
                "Bought under 3 months ago": "menos_3m", "3–6 months": "mais_3m",
                "6–12 months": "mais_6m", "Over a year": "mais_1a"}


def compute(*, make=None, model=None, year=None, opp_name=None, how_soon=None,
            msgs=None, call_analysis=None, momento_manual=None,
            visited_store=False, visit_reason=None,
            quote_sent=False, quote_reason=None):
    """
    Retorna dict com componentes, conhecido, maximo_possivel, breakdown e selo (A12-b).
    Precedência:
      Momento  — manual (Log call VENCE) > transcrição > '?'
      Intenção — visita à loja (prova, A12-c) > transcrição > quote enviada > proxy how_soon
    Cada componente carrega `_src` (origem) p/ exibição honesta e auditoria.
    """
    cs, cs_r = car_score(make, model, year, opp_name)
    eng, eng_r = engagement_from_messages(msgs or [])

    # Momento — manual vence; senão transcrição; senão '?'
    momento, momento_r, momento_src = "?", "sem transcrição/nota", None
    faixa_manual = MOMENTO_FORM.get(momento_manual or "", momento_manual)
    if faixa_manual in MOMENTO_FAIXA:
        momento = MOMENTO_FAIXA[faixa_manual]
        momento_r = f"informado pelo Eugene ({momento_manual})"
        momento_src = "manual"
    elif call_analysis and call_analysis.get("momento", {}).get("faixa") in MOMENTO_FAIXA:
        momento = MOMENTO_FAIXA[call_analysis["momento"]["faixa"]]
        momento_r = call_analysis["momento"].get("evidencia", "transcrição")
        momento_src = "call"

    # Intenção — visita à loja é o sinal mais forte do funil (A12-c)
    if visited_store:
        intenc, intenc_r, intenc_src = 15, visit_reason or "visitou a loja", "visita"
    elif call_analysis and call_analysis.get("intencao", {}).get("nivel") in INTENT_FROM_CALL:
        intenc = INTENT_FROM_CALL[call_analysis["intencao"]["nivel"]]
        intenc_r = call_analysis["intencao"].get("evidencia", "transcrição")
        intenc_src = "call"
    elif quote_sent:
        intenc, intenc_r, intenc_src = 15, quote_reason or "quote enviada", "quote"
    else:
        intenc, intenc_r = intent_from_how_soon(how_soon)
        intenc_src = "how_soon" if isinstance(intenc, int) else None

    known = cs + eng + sum(v for v in (momento, intenc) if isinstance(v, int))
    # máximo apurável = teto só dos componentes COM dado — honestidade sobre o que falta
    max_possible = 35 + 25 + (25 if isinstance(momento, int) else 0) + (15 if isinstance(intenc, int) else 0)

    # selo (A12-b): call-verified quando Momento OU Intenção vêm de evidência real
    # (transcrição, visita provada, quote detectada, entrada manual do Eugene)
    verified = momento_src in ("call", "manual") or intenc_src in ("call", "visita", "quote")
    badge = "call-verified" if verified else "partial"

    def fmt(v):
        return str(v) if isinstance(v, int) else "?"
    breakdown = f"car:{cs} mom:{fmt(momento)} eng:{eng} int:{fmt(intenc)}"
    return {
        "car": cs, "car_reason": cs_r,
        "momento": momento, "momento_reason": momento_r, "momento_src": momento_src,
        "eng": eng, "eng_reason": eng_r,
        "int": intenc, "int_reason": intenc_r, "int_src": intenc_src,
        "known": known, "max_possible": max_possible,
        "badge": badge, "breakdown": breakdown,
        "visited_store": bool(visited_store),
    }
