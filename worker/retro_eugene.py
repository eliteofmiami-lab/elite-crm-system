"""
MISSÃO retro (docs/missoes/prompt-retro-eugene.md): por que perdemos leads.
Win vs Lost, 120 dias, call atendida >60s, cap 250 calls, Batch API (50% off).
Roda SOMENTE após a Onda 0. Leitura no GHL; resultados no Supabase + arquivos.
Teto: $50 (ordem da noite). Fases: --collect (amostra+custo) · --submit (batch) ·
--harvest (resultados+síntese).
"""
import datetime as dt
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
import ghl  # noqa: E402
from brain import rules, cards, transcribe, analyze  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
CAP_CALLS = 250
CAP_USD = 50.0
S = {"type": "string"}
B = {"type": "boolean"}

# Schema DEDICADO e enxuto — o schema completo da análise + campos retro estourou o
# limite de gramática do structured output no Batch ("compiled grammar is too large").
_RETRO_PROPS = {
    "resumo_3_linhas": S,
    "servico_interesse": S,
    "precos_falados": {"type": "array",
                       "items": {"type": "object", "additionalProperties": False,
                                 "required": ["servico", "valor"],
                                 "properties": {"servico": S, "valor": S}}},
    "sentimento_geral": S,
    "reacao_preco": S,             # achou_caro|ok|achou_barato|nao_discutido
    "script_coverage": {"type": "object", "additionalProperties": False,
                        "required": ["perguntou_carro_novo", "perguntou_garagem",
                                     "perguntou_keep_or_trade", "perguntou_outros_orcamentos",
                                     "apresentou_ballpark"],
                        "properties": {k: B for k in
                                       ["perguntou_carro_novo", "perguntou_garagem",
                                        "perguntou_keep_or_trade", "perguntou_outros_orcamentos",
                                        "apresentou_ballpark"]}},
    "extras_empurrados": B,
    "ponto_de_morte": S,           # preco_sem_defesa|sem_proximo_passo|visita_nao_proposta|followup_nao_feito|objecao_nao_tratada|esfriou_sem_causa|""
    "visita_proposta_houve": B,
    "visita_proposta_como": S,
    "preco_antes_da_motivacao": B,
    "proximo_passo_definido_houve": B,
    "proximo_passo_definido_qual": S,
    "talk_ratio_operador": {"type": "number"},   # 0-1 fração de fala do operador
    "classificacao_da_perda": S,   # controlavel|incontrolavel|"" (win)
    "justificativa_classificacao": S,
    "nota_da_call": {"type": "integer"},         # 0-10
    "perguntas_do_cliente": {"type": "array", "items": S},
    "resposta_tecnica_improvisada": B,
}
RETRO_SCHEMA = {"type": "object", "additionalProperties": False,
                "required": list(_RETRO_PROPS), "properties": _RETRO_PROPS}

RETRO_SYSTEM = """Você analisa retrospectivamente calls de vendas da Elite Premium Detailing
(detailing automotivo premium em Davie/FL: PPF, ceramic coating, wrap). O atendente é o
Eugene (assistente) ou o Rafael (dono); o outro falante é o cliente. Transcrição diarizada
(S0/S1...), em inglês/espanhol/português. Extraia APENAS o que está na transcrição;
campos de texto sem evidência ficam "".

MODO RETROSPECTIVO: o desfecho REAL deste lead (win/lost + grupo) vem nos metadados.
Analise a call À LUZ do desfecho:
- ponto_de_morte (só lost): onde a conversa/lead morreu — preco_sem_defesa |
  sem_proximo_passo | visita_nao_proposta | followup_nao_feito | objecao_nao_tratada |
  esfriou_sem_causa. "" para win.
- visita_proposta: o operador propôs a VISITA à loja? como?
- preco_antes_da_motivacao: falou preço antes de entender a motivação do cliente?
- proximo_passo_definido: a call terminou com passo concreto (data/ação)?
- talk_ratio_operador: fração aproximada de fala do operador (0-1) pela diarização.
- classificacao_da_perda: controlavel (a condução podia mudar o desfecho) vs
  incontrolavel (price shopper declarado, spam, mudou de cidade, comprou antes).
  Com justificativa. "" para win.
- nota_da_call: 0-10 (abertura, descoberta, apresentação de preço, fechamento de visita,
  próximo passo definido).
- perguntas_do_cliente: TODAS as perguntas que o cliente fez, literais e curtas.
"""


def log(m):
    print(f"[{dt.datetime.now():%H:%M:%S}] {m}", flush=True)


def paged_opps(stage_id, extra=None):
    out, page = [], 1
    while True:
        p = {"location_id": ghl.LOCATION_ID, "pipeline_id": rules.NEW_PIPELINE_ID,
             "pipeline_stage_id": stage_id, "limit": 100, "page": page}
        r = ghl.get("/opportunities/search", p)
        if r.status_code != 200:
            break
        ops = r.json().get("opportunities", [])
        out += ops
        if len(ops) < 100:
            break
        page += 1
    return out


def answered_calls(contact_id, min_dur=60):
    """Calls atendidas >min_dur do contato, mais recente primeiro."""
    calls = []
    r = ghl.get("/conversations/search", {"locationId": ghl.LOCATION_ID,
                                          "contactId": contact_id})
    if r.status_code != 200:
        return []
    for cv in r.json().get("conversations", [])[:3]:
        m = ghl.get(f"/conversations/{cv['id']}/messages")
        if m.status_code != 200:
            continue
        for msg in m.json().get("messages", {}).get("messages", []):
            if msg.get("messageType") != "TYPE_CALL":
                continue
            dur = ((msg.get("meta") or {}).get("call") or {}).get("duration") or 0
            if dur > min_dur:
                calls.append({"id": msg["id"], "ts": msg.get("dateAdded"), "dur": dur,
                              "direction": msg.get("direction")})
    calls.sort(key=lambda c: c["ts"] or "", reverse=True)
    return calls


def collect():
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=120)).isoformat()
    sample = []
    # -------- grupo WIN --------
    wins = [o for o in paged_opps(rules.STAGES["Win"])
            if (o.get("updatedAt") or "") >= cutoff or (o.get("createdAt") or "") >= cutoff]
    log(f"wins no período: {len(wins)}")
    for o in wins:
        cs = answered_calls(o["contactId"])
        if not cs:
            continue
        best = max(cs, key=lambda c: c["dur"]) if len(cs) > 1 else cs[0]
        # "call decisiva": a última antes do fim; fallback mais longa — usamos a mais longa
        sample.append({"contact_id": o["contactId"], "opp_id": o["id"],
                       "name": o.get("name"), "grupo": "win", "call": best})
    n_win = len(sample)
    log(f"grupo WIN com call: {n_win}")

    # -------- grupo LOST (estratificado, na ordem, até o cap) --------
    losts = [o for o in paged_opps(rules.STAGES["Lost"])
             if (o.get("updatedAt") or "") >= cutoff or (o.get("createdAt") or "") >= cutoff]
    log(f"losts no período: {len(losts)}")
    import score as sc
    seen = {s["contact_id"] for s in sample}

    def car_pts(o):
        return sc.car_score(name=o.get("name"))[0]

    groups = []
    # 1. alto valor morto (carro 35/25)
    groups.append(("alto_valor", [o for o in losts if car_pts(o) >= 25]))
    # 2. quote enviada e morreu (CF quote_sent/link nas opps)
    def has_quote(o):
        return any((cf.get("fieldValue") or "") not in ("", None, False)
                   for cf in o.get("customFields", [])
                   if cf.get("id") in ("b0", ) or "quote" in str(cf.get("id", "")).lower())
    groups.append(("quote_morta", [o for o in losts if any(
        str(cf.get("fieldValue") or "").startswith("http") for cf in o.get("customFields", []))]))
    # 3. no-show nunca recuperado (via calendários, 90d máx da API)
    noshows = set()
    now = dt.datetime.now(dt.timezone.utc)
    for cal_id in cards.CALENDARS.values():
        r = ghl.get("/calendars/events", {"locationId": ghl.LOCATION_ID, "calendarId": cal_id,
                                          "startTime": int((now - dt.timedelta(days=90)).timestamp() * 1000),
                                          "endTime": int(now.timestamp() * 1000)})
        if r.status_code == 200:
            for e in r.json().get("events", []):
                if e.get("appointmentStatus") == "noshow" and e.get("contactId"):
                    noshows.add(e["contactId"])
    groups.append(("noshow", [o for o in losts if o["contactId"] in noshows]))
    # 4./5. demais losts por recência (ghosted/price ficam aqui — GHL não expõe motivo via API)
    groups.append(("lost_geral", sorted(losts, key=lambda o: o.get("updatedAt") or "",
                                        reverse=True)))

    for gname, ops in groups:
        for o in ops:
            if len(sample) >= CAP_CALLS:
                break
            cid = o["contactId"]
            if cid in seen:
                continue
            cs = answered_calls(cid)
            if not cs:
                continue
            seen.add(cid)
            sample.append({"contact_id": cid, "opp_id": o["id"], "name": o.get("name"),
                           "grupo": gname, "call": max(cs, key=lambda c: c["dur"])})
        log(f"  +{gname}: amostra agora {len(sample)}")
        if len(sample) >= CAP_CALLS:
            break

    minutes = sum(s["call"]["dur"] for s in sample) / 60
    est = minutes * 0.0043 + len(sample) * 0.013  # deepgram + sonnet batch (50% off)
    log(f"== AMOSTRA: {len(sample)} calls ({n_win} win) · {minutes:.0f} min · ~${est:.2f} "
        f"(teto ${CAP_USD}) ==")
    json.dump({"sample": sample, "estimate_usd": round(est, 2)},
              open(OUT / "retro_sample.json", "w"), indent=2, ensure_ascii=False)
    if est > CAP_USD:
        log("!! acima do teto — cortar amostra antes do submit")
    return sample


def submit():
    """Transcreve (Deepgram, sync) e submete o Batch Anthropic."""
    data = json.load(open(OUT / "retro_sample.json"))
    sample = data["sample"]
    client = analyze.get_client()
    reqs, done, spend = [], 0, 0.0
    transcripts = {}
    for s in sample:
        call = s["call"]
        # já transcrita? (Onda 0 pode ter processado)
        tr = cards._sb("GET", f"transcripts?call_id=eq.{call['id']}&select=full_text,diarized") or []
        if tr:
            text = transcribe.diarized_as_text(tr[0].get("diarized") or []) or tr[0]["full_text"]
        else:
            # FK: transcripts referencia calls — garantir a linha da call ANTES
            cards._sb("POST", "calls", headers_extra={"Prefer": "resolution=merge-duplicates"},
                      json={"id": call["id"], "contact_id": s["contact_id"],
                            "direction": call["direction"], "duration_sec": call["dur"],
                            "called_at": call["ts"], "recording_downloaded": True})
            audio = None
            for attempt in range(3):
                try:
                    audio = transcribe.download_recording(call["id"])
                    if audio:
                        break
                except Exception:
                    pass
                time.sleep(2 ** attempt)
            if not audio:
                continue
            try:
                t = transcribe.transcribe(audio)
            except Exception:
                continue
            usd = round(call["dur"] / 60 * 0.0043, 5)
            spend += usd
            cards._sb("POST", "cost_log", json={"call_id": call["id"], "provider": "deepgram",
                                                "model": "nova-2 (retro)",
                                                "units": round(call["dur"] / 60, 2), "est_usd": usd})
            cards._sb("POST", "transcripts", headers_extra={"Prefer": "resolution=merge-duplicates"},
                      json={"call_id": call["id"], "provider": "deepgram",
                            "language": t.get("language"), "diarized": t["diarized"],
                            "full_text": t["full_text"]})
            text = transcribe.diarized_as_text(t["diarized"]) or t["full_text"]
        if not (text or "").strip():
            continue
        transcripts[call["id"]] = True
        meta = {"desfecho_conhecido": s["grupo"], "lead": s["name"],
                "direction": call["direction"], "duration_sec": call["dur"]}
        reqs.append({"custom_id": call["id"],
                     "params": {"model": analyze.MODEL, "max_tokens": 8000,
                                "system": [{"type": "text", "text": RETRO_SYSTEM,
                                            "cache_control": {"type": "ephemeral"}}],
                                "output_config": {"format": {"type": "json_schema",
                                                             "schema": RETRO_SCHEMA}},
                                "messages": [{"role": "user", "content":
                                              f"Metadados: {json.dumps(meta, ensure_ascii=False)}\n\n"
                                              f"Transcrição diarizada:\n{text}"}]}})
        done += 1
        if done % 25 == 0:
            log(f"  transcritas {done}/{len(sample)} · deepgram ${spend:.2f}")
    log(f"submetendo batch com {len(reqs)} análises (deepgram gasto: ${spend:.2f})")
    batch = client.messages.batches.create(requests=reqs)
    json.dump({"batch_id": batch.id, "n": len(reqs),
               "submitted": dt.datetime.now(dt.timezone.utc).isoformat()},
              open(OUT / "retro_batch.json", "w"), indent=2)
    log(f"batch {batch.id} submetido ({len(reqs)} reqs)")


def harvest():
    """Colhe o batch, grava análises retro e roda a síntese."""
    info = json.load(open(OUT / "retro_batch.json"))
    sample = {s["call"]["id"]: s for s in json.load(open(OUT / "retro_sample.json"))["sample"]}
    client = analyze.get_client()
    while True:
        b = client.messages.batches.retrieve(info["batch_id"])
        log(f"batch: {b.processing_status} · {b.request_counts}")
        if b.processing_status == "ended":
            break
        time.sleep(60)
    results, in_tok, out_tok, errored = [], 0, 0, 0
    for entry in client.messages.batches.results(info["batch_id"]):
        if entry.result.type != "succeeded":
            errored += 1
            continue
        msg = entry.result.message
        in_tok += msg.usage.input_tokens
        out_tok += msg.usage.output_tokens
        payload = json.loads(next(bl.text for bl in msg.content if bl.type == "text"))
        s = sample.get(entry.custom_id, {})
        payload["_retro"] = {"grupo": s.get("grupo"), "lead": s.get("name"),
                             "contact_id": s.get("contact_id")}
        results.append(payload)
        cards._sb("POST", "analyses", headers_extra={"Prefer": "resolution=merge-duplicates"},
                  json={"call_id": entry.custom_id, "model": f"{analyze.MODEL} (batch retro)",
                        "payload": payload})
    usd = round((in_tok / 1e6 * 3.0 + out_tok / 1e6 * 15.0) * 0.5, 2)  # 50% batch
    cards._sb("POST", "cost_log", json={"call_id": "retro-batch", "provider": "anthropic",
                                        "model": f"{analyze.MODEL} (batch)",
                                        "units": in_tok + out_tok, "est_usd": usd})
    log(f"colhidas {len(results)} análises ({errored} com erro) · batch ${usd}")
    json.dump(results, open(OUT / "retro_results.json", "w"), indent=2, ensure_ascii=False)
    if len(results) < 20:
        log("!! poucas análises colhidas — NÃO sintetizar com amostra quebrada. Abortando.")
        return
    synthesize(results, client)


def synthesize(results, client):
    """Síntese agregada (Sonnet, contexto longo) → 3 entregáveis + calibragem."""
    wins = [r for r in results if r["_retro"]["grupo"] == "win"]
    losts = [r for r in results if r["_retro"]["grupo"] != "win"]

    def slim(r):
        return {k: r.get(k) for k in
                ("resumo_3_linhas", "ponto_de_morte", "visita_proposta_houve",
                 "visita_proposta_como", "preco_antes_da_motivacao",
                 "proximo_passo_definido_houve", "proximo_passo_definido_qual",
                 "talk_ratio_operador", "classificacao_da_perda",
                 "justificativa_classificacao", "nota_da_call", "perguntas_do_cliente",
                 "script_coverage", "precos_falados", "extras_empurrados",
                 "sentimento_geral", "reacao_preco", "servico_interesse",
                 "resposta_tecnica_improvisada")} | {"_": r["_retro"]}

    prompt = f"""Estudo retrospectivo Elite Premium Detailing (docs/missoes/prompt-retro-eugene.md).
{len(wins)} calls WIN e {len(losts)} calls LOST analisadas (JSONs abaixo).
Gere EXATAMENTE 4 seções em markdown, separadas por linhas '===FILE: nome===':

===FILE: DIAGNOSTICO_EUGENE.md===
Tom construtivo, orientado a dinheiro (mais conversão = mais comissão). Anonimizar (primeiro nome só).
1. O que ele faz BEM (padrões dos Wins — manter)
2. Top 5 erros por frequência × impacto, SÓ perdas controláveis, cada um com 2-3 trechos/resumos
   reais anonimizados, o que dizer no lugar, e a regra prática
3. Comparativo Win vs Lost: % visita proposta, % próximo passo definido, cobertura de script,
   preço-antes-da-motivação, talk ratio médio, nota média
4. As 5 regras de mudança imediata (curtas, memorizáveis)

===FILE: PERDAS_REPORT.md===
Para o Rafael: distribuição controlável vs incontrolável · pontos de morte com % ·
perdas de alto valor caso a caso · receita recuperável estimada se os top 3 erros
controláveis caírem 50% (usar preços falados/starting da tabela).

===FILE: PERGUNTAS_DOS_CLIENTES.md===
Inventário de TODAS as perguntas de clientes, agrupadas por tema, com frequência e marcação:
`lane do Eugene` (com resposta-modelo extraída das melhores respostas dele nos Wins) vs
`transferir ao master tech`. Formato de tabela.

===FILE: CALIBRAGEM_ADVICE.md===
Regras derivadas dos dados para o motor de advice (ex.: 'visita não proposta' → advice
prioritário com evidência) — lista objetiva de gatilho → advice, pronta pra virar prompt.

DADOS:
WINS: {json.dumps([slim(r) for r in wins], ensure_ascii=False)}
LOSTS: {json.dumps([slim(r) for r in losts], ensure_ascii=False)}"""

    r = client.messages.create(model=analyze.MODEL, max_tokens=16000,
                               messages=[{"role": "user", "content": prompt}])
    text = next(b.text for b in r.content if b.type == "text")
    usd = round(r.usage.input_tokens / 1e6 * 3.0 + r.usage.output_tokens / 1e6 * 15.0, 2)
    cards._sb("POST", "cost_log", json={"call_id": "retro-sintese", "provider": "anthropic",
                                        "model": analyze.MODEL,
                                        "units": r.usage.input_tokens + r.usage.output_tokens,
                                        "est_usd": usd})
    parts = text.split("===FILE: ")
    for part in parts[1:]:
        name, _, body = part.partition("===")
        (ROOT / name.strip()).write_text(body.strip() + "\n")
        log(f"gravado {name.strip()}")
    log(f"síntese ok (${usd})")


if __name__ == "__main__":
    if "--collect" in sys.argv:
        collect()
    elif "--submit" in sys.argv:
        submit()
    elif "--harvest" in sys.argv:
        harvest()
    else:
        print("use: --collect | --submit | --harvest")
