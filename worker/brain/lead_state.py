"""
A16 — REGRA ZERO: a unidade de análise é o LEAD, não a call.
Linha do tempo cronológica (calls analisadas + SMS in/out + eventos) → síntese
(Sonnet, system cacheado) → estado_do_lead → SÓ o estado escreve score/ação/card.

Regras da cronologia (REGRAS_DO_MOTOR §0):
- evidência mais nova SOBRESCREVE a antiga (componentes carregam data)
- "cliente pediu espaço" → aguardando_decisao_cliente: fora da discagem ativa, nurture leve
- evento futuro conhecido → follow-up NA janela certa, não retry genérico
- retorno do cliente não atendido → callback_devido, urgência máxima
- pós-venda/garantia (A16.1) → o sistema NÃO gera NADA; grava pos_venda e silencia
- o card conta a HISTÓRIA, não a foto de uma call antiga
"""
import datetime as dt
import json

import anthropic

import ghl
from brain import analyze, cards, rules

S = {"type": "string"}
B = {"type": "boolean"}
STATE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["situacao", "situacao_evidencia", "situacao_data", "evento_externo",
                 "followup_em", "momento_atual", "intencao_atual", "tipo_ultima_call",
                 "vehicle", "proxima_acao", "narrativa_do_card", "rascunho_followup",
                 "urgente"],
    "properties": {
        # ativo_venda|aguardando_decisao_cliente|aguardando_evento_externo|agendado|
        # callback_devido|pos_venda|esfriou
        "situacao": S,
        "situacao_evidencia": S,      # trecho/evento literal que prova a situação
        "situacao_data": S,           # data (YYYY-MM-DD) da evidência da situação
        "evento_externo": S,          # qual evento/janela (se aguardando_evento_externo)
        "followup_em": S,             # YYYY-MM-DD sugerido p/ retomar ("" se n/a)
        "momento_atual": {"type": "object", "additionalProperties": False,
                          "required": ["faixa", "data", "evidencia"],
                          "properties": {"faixa": S, "data": S, "evidencia": S}},
        "intencao_atual": {"type": "object", "additionalProperties": False,
                           "required": ["nivel", "data", "evidencia"],
                           "properties": {"nivel": S, "data": S, "evidencia": S}},
        "tipo_ultima_call": S,        # venda|pos_venda_garantia|suporte|engano|""
        "vehicle": {"type": "object", "additionalProperties": False,
                    "required": ["make", "model", "year"],
                    "properties": {"make": S, "model": S, "year": S}},
        "proxima_acao": {"type": "object", "additionalProperties": False,
                         "required": ["tipo", "quando", "motivo"],
                         "properties": {"tipo": S, "quando": S, "motivo": S}},
        "narrativa_do_card": S,       # a HISTÓRIA em até 3 linhas (inglês, p/ Eugene)
        "rascunho_followup": S,       # SMS em 1ª pessoa NATURAL (Eugene) — "" se nada
        "urgente": B,
    },
}

SYSTEM = """Você sintetiza o ESTADO ATUAL de um lead da Elite Premium Detailing (PPF,
ceramic coating, wraps — Davie/FL) a partir da LINHA DO TEMPO completa: calls analisadas,
SMS enviados/respondidos e eventos (quotes, appointments, inbound perdidas), em ordem.
A unidade é o LEAD, não uma call isolada. Regras:
1. EVIDÊNCIA MAIS NOVA SOBRESCREVE A ANTIGA. Cada componente (momento, intenção) sai do
   evento mais recente que o prova, com a DATA. Pediu quote em maio e recuou em junho →
   vale junho.
2. situacao (escolha UMA):
   - ativo_venda: conversa de venda viva, próximo passo é nosso.
   - aguardando_decisao_cliente: o cliente PEDIU espaço ("I'll call you when I decide",
     "not right now") → respeitar; fora da discagem ativa; nurture leve.
   - aguardando_evento_externo: espera evento fora do nosso controle (carro novo chega,
     modelo lança) → followup_em = a JANELA CERTA do evento, nunca retry genérico.
   - agendado: appointment futuro marcado → só follow-up/confirmação na data certa.
   - callback_devido: o CLIENTE tentou falar conosco e não foi atendido (inbound perdida
     sem retorno nosso depois) → URGENTE, topo da fila. urgente=true.
     JANELA DE VALIDADE (regra do Rafael): só vale se a perdida foi nos últimos 4 dias
     (hoje, ontem, ou atravessando o fim de semana). Perdida mais antiga NÃO é
     callback_devido — o erro não pode mais ser corrigido; classifique o lead pelo
     restante da história (esfriou / ativo_venda / aguardando_*).
   - pos_venda: cliente JÁ COMPROU; call de garantia/pós-venda/suporte → o sistema fica
     INERTE (nada é criado). Reentrada só com conversa de venda NOVA.
   - spam_nao_lead: NÃO É CLIENTE — vendedor/solicitador ligando PARA a loja
     ("can I speak to the owner", oferta de serviços/marketing/seguro, robocall,
     screener automático sem interesse em serviço automotivo). Sem veículo, sem
     serviço buscado, nunca. O sistema silencia: fora de TODAS as filas, para sempre.
     Callback perdida de spam NÃO é callback_devido.
   - esfriou: sem resposta a múltiplas tentativas, sem pedido de espaço → fila fria.
3. tipo_ultima_call: venda | pos_venda_garantia | suporte | engano | "".
3b. Vocabulário fixo: momento_atual.faixa ∈ recem_entregue|chegando|menos_3m|mais_3m|
   mais_6m|mais_1a|"" · intencao_atual.nivel ∈ pediu_quote|sem_recuar|indeciso|
   so_pesquisando|"" — sempre com a DATA da evidência mais recente que o prova.
4. vehicle com INFERÊNCIA DE ANO: "just bought/brand new/just picked up" sem ano explícito
   → ano provável = ano atual (2026), marcar year assim ("2026 (inferido)").
5. proxima_acao deriva DO ESTADO (não da call mais antiga): quando = data concreta se
   houver janela; motivo = 1 frase.
6. narrativa_do_card: a HISTÓRIA em ≤3 linhas, inglês (p/ o operador), com datas —
   ex.: "2 calls; on Jun 9 he said he'll call us when he decides. Don't chase."
7. rascunho_followup: SÓ se a próxima ação for mensagem — em 1ª PESSOA, tom NATURAL de
   humano (o Eugene), curto, sem cara de template; senão "".
Datas: hoje é {HOJE}. Campos sem evidência: "" (nunca invente)."""


def _client():
    return analyze.get_client()


def build_timeline(contact_id, max_events=70):
    """Linha do tempo compacta: calls (+análise), SMS in/out, appointments, quote."""
    events = []
    r = ghl.get("/conversations/search", {"locationId": ghl.LOCATION_ID,
                                          "contactId": contact_id})
    convs = r.json().get("conversations", []) if r.status_code == 200 else []
    ana_by_call = {}
    rows = cards._sb("GET", ("analyses?select=call_id,payload,calls!inner(contact_id)"
                             f"&calls.contact_id=eq.{contact_id}")) or []
    for a in rows:
        ana_by_call[a["call_id"]] = a["payload"]
    for cv in convs[:3]:
        m = ghl.get(f"/conversations/{cv['id']}/messages")
        if m.status_code != 200:
            continue
        for msg in m.json().get("messages", {}).get("messages", []):
            ts = msg.get("dateAdded") or ""
            mt = msg.get("messageType")
            if mt == "TYPE_CALL":
                meta = (msg.get("meta") or {}).get("call") or {}
                dur = meta.get("duration") or 0
                ev = {"ts": ts, "tipo": "call", "direction": msg.get("direction"),
                      "atendida": bool(dur and dur > 20), "duracao_s": dur}
                pay = ana_by_call.get(msg["id"])
                if pay:
                    ev["analise"] = {
                        "resumo": pay.get("resumo_3_linhas", "")[:220],
                        "momento": (pay.get("momento") or {}).get("faixa"),
                        "intencao": (pay.get("intencao") or {}).get("nivel"),
                        "servico": pay.get("servico_interesse"),
                        "resolucao": pay.get("resolucao_da_call"),
                        "veiculo": pay.get("vehicle")}
                events.append(ev)
            elif mt == "TYPE_SMS":
                body = (msg.get("body") or "").strip()
                ev = {"ts": ts, "tipo": "sms", "direction": msg.get("direction"),
                      "texto": body[:180]}
                if rules.URABLE_LINK.search(body):
                    ev["quote_link"] = True
                events.append(ev)
    ar = ghl.get(f"/contacts/{contact_id}/appointments")
    if ar.status_code == 200:
        for e in ar.json().get("events", []):
            events.append({"ts": str(e.get("startTime") or ""), "tipo": "appointment",
                           "status": e.get("appointmentStatus"),
                           "titulo": str(e.get("title") or "")[:60]})
    events.sort(key=lambda e: e["ts"])
    # compactar mantendo início e fim da história
    if len(events) > max_events:
        events = events[:15] + [{"tipo": "corte", "n_omitidos": len(events) - 55}] + events[-55:]
    # contexto da opp
    opr = ghl.get("/opportunities/search", {"location_id": ghl.LOCATION_ID,
                                            "contact_id": contact_id, "limit": 5})
    opps = opr.json().get("opportunities", []) if opr.status_code == 200 else []
    ctx = [{"stage": rules.STAGE_BY_ID.get(o.get("pipelineStageId"), "?"),
            "status": o.get("status"), "name": o.get("name")} for o in opps]
    return {"opps": ctx, "eventos": events}


def synthesize(contact_id, timeline=None, client=None, log_cost=True):
    """Síntese do estado do lead. Retorna (state, custo_usd)."""
    client = client or _client()
    timeline = timeline or build_timeline(contact_id)
    hoje = f"{dt.datetime.now():%Y-%m-%d}"
    r = client.messages.create(
        model=analyze.MODEL, max_tokens=6000,
        system=[{"type": "text", "text": SYSTEM.replace("{HOJE}", hoje),
                 "cache_control": {"type": "ephemeral"}}],
        output_config={"format": {"type": "json_schema", "schema": STATE_SCHEMA}},
        messages=[{"role": "user", "content":
                   f"LINHA DO TEMPO DO LEAD:\n{json.dumps(timeline, ensure_ascii=False)}"}])
    state = json.loads(next(b.text for b in r.content if b.type == "text"))
    usd = round(r.usage.input_tokens / 1e6 * 3.0 + r.usage.output_tokens / 1e6 * 15.0, 5)
    if log_cost:
        cards._sb("POST", "cost_log", json={"call_id": f"state-{contact_id}",
                                            "provider": "anthropic",
                                            "model": f"{analyze.MODEL} (lead-state)",
                                            "units": r.usage.input_tokens + r.usage.output_tokens,
                                            "est_usd": usd})
    state["_computed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    cards._sb("POST", "lead_states?on_conflict=contact_id",
              headers_extra={"Prefer": "resolution=merge-duplicates"},
              json={"contact_id": contact_id, "state": state,
                    "situacao": state.get("situacao"),
                    "computed_at": state["_computed_at"].replace("+00:00", "Z")})
    return state, usd


def state_for(contact_id):
    rows = cards._sb("GET", f"lead_states?contact_id=eq.{contact_id}&select=state") or []
    return rows[0]["state"] if rows else None


# situações que tiram o lead da DISCAGEM ATIVA (cards de venda não nascem)
BLOCK_DIAL = {"aguardando_decisao_cliente", "aguardando_evento_externo",
              "agendado", "pos_venda", "spam_nao_lead"}


def apply_state(contact_id, state):
    """Efeitos do estado na fila (Supabase apenas — G2 fechado)."""
    sit = state.get("situacao")
    n = {"closed": 0, "created": 0}
    if sit in ("pos_venda", "spam_nao_lead"):
        # A16.1 (pós-venda) e spam de vendedor (Rafael 2026-07-08): NADA nasce;
        # cards abertos morrem em silêncio; fora do cold para sempre.
        motivo = ("pos_venda — fora do sistema (A16.1)" if sit == "pos_venda"
                  else "spam/vendedor — não é lead (fora de todas as filas)")
        for c in cards._sb("GET", f"cards?status=in.(open,snoozed,wrapup)&contact_id=eq.{contact_id}&select=id") or []:
            cards.close_card(c["id"], motivo, {"state": sit})
            n["closed"] += 1
        cards._sb("POST", "lead_flags?on_conflict=contact_id",
                  headers_extra={"Prefer": "resolution=merge-duplicates"},
                  json={"contact_id": contact_id, "cold_excluded": True,
                        "set_by": motivo})
        return n
    if sit == "callback_devido":
        # trava de validade (defesa em profundidade): perdida >4 dias não fura a fila
        data = state.get("situacao_data") or ""
        limite = f"{(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=4)):%Y-%m-%d}"
        if data and data < limite:
            print(f"  [callback expirado] {contact_id}: perdida em {data} — vira esfriou (C3)")
            state["situacao"] = "esfriou"
            cards._sb("PATCH", f"lead_states?contact_id=eq.{contact_id}",
                      json={"situacao": "esfriou",
                            "state": {**state, "situacao": "esfriou"}})
            return n
        made = cards.create_card(
            "callback", 1, contact_id,
            "📞 CALLBACK OWED — customer called US and nobody answered",
            state.get("narrativa_do_card") or "They tried to reach us. Call back NOW.",
            {"passos": ["Call back immediately — apologize for missing them",
                        "They reached out — the deal is warm, close the visit"],
             "state": sit})
        n["created"] += bool(made)
        return n
    if sit in ("aguardando_decisao_cliente", "aguardando_evento_externo", "agendado"):
        # fora da discagem ativa: fecha cards de discagem; agenda retomada na janela
        for c in cards._sb("GET", f"cards?status=eq.open&contact_id=eq.{contact_id}"
                                  "&type=in.(first_touch,warm_call,quote_followup,callback)"
                                  "&select=id,type") or []:
            cards.close_card(c["id"], f"{sit} — fora da discagem ativa (Regra Zero)",
                             {"state": sit, "evidencia": state.get("situacao_evidencia", "")[:120]})
            n["closed"] += 1
        due = state.get("followup_em") or ""
        if not due:
            base = dt.datetime.now(dt.timezone.utc)
            due = f"{(base + dt.timedelta(days=30)):%Y-%m-%d}"
        if sit != "agendado":  # agendado: confirm_appt cuida da data
            existing = cards._sb("GET", f"cards?status=eq.snoozed&contact_id=eq.{contact_id}"
                                        "&type=eq.follow_up&select=id&limit=1")
            if not existing:
                # nurture leve mora na CAMADA 3 (gabarito: fora da discagem ativa,
                # visível só como nurture com o estado explícito)
                cards._sb("POST", "cards", json={
                    "type": "follow_up", "layer": 3, "contact_id": contact_id,
                    "title": f"Follow-up ({'client asked for space' if sit == 'aguardando_decisao_cliente' else state.get('evento_externo') or 'external event'})",
                    "why": state.get("narrativa_do_card"),
                    "how": {"passos": [state.get("proxima_acao", {}).get("motivo") or "Re-open gently"],
                            "state": sit},
                    "status": "snoozed", "snooze_reason": f"{sit} — janela {due}",
                    "due_at": f"{due}T13:00:00Z",
                    "ghl_link": cards.GHL_LINK.format(loc=cards.LOC, cid=contact_id)})
                n["created"] += 1
    return n
