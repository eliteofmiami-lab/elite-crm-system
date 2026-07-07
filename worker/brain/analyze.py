"""Análise de transcrição de chamada com Claude (Sonnet) — spec 2.2 da Fase 1.
Saída em JSON estruturado garantido via output_config.format (json_schema)."""
import json

import anthropic

import config

MODEL = "claude-sonnet-5"

_cfg = config.load()

# Schema do JSON estruturado (spec 2.2). additionalProperties=false obrigatório.
S = {"type": "string"}
B = {"type": "boolean"}
SN = {"type": ["string", "null"]}
ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["vehicle", "momento", "intencao", "sentimento", "motivacao_principal",
                 "gancho_pessoal", "precos_falados", "script_coverage", "voicemail_left",
                 "resultado", "proxima_acao", "resumo_3_linhas", "coaching"],
    "properties": {
        "vehicle": {"type": "object", "additionalProperties": False,
                    "required": ["make", "model", "year", "is_new_or_just_bought", "delivery_date_or_window"],
                    "properties": {"make": SN, "model": SN, "year": SN,
                                   "is_new_or_just_bought": {"type": ["boolean", "null"]},
                                   "delivery_date_or_window": SN}},
        "momento": {"type": "object", "additionalProperties": False,
                    "required": ["faixa", "evidencia"],
                    "properties": {"faixa": {"anyOf": [
                                       {"type": "string",
                                        "enum": ["recem_entregue", "chegando", "menos_3m",
                                                 "mais_3m", "mais_6m", "mais_1a"]},
                                       {"type": "null"}]},
                                   "evidencia": SN}},
        "intencao": {"type": "object", "additionalProperties": False,
                     "required": ["nivel", "evidencia"],
                     "properties": {"nivel": {"anyOf": [
                                        {"type": "string",
                                         "enum": ["pediu_quote", "sem_recuar", "indeciso",
                                                  "so_pesquisando"]},
                                        {"type": "null"}]},
                                    "evidencia": SN}},
        "sentimento": {"type": "object", "additionalProperties": False,
                       "required": ["geral", "reacao_preco", "comparou_concorrente", "detalhes"],
                       "properties": {"geral": SN,
                                      "reacao_preco": {"type": "string",
                                                       "enum": ["achou_caro", "ok", "achou_barato", "nao_discutido"]},
                                      "comparou_concorrente": B, "detalhes": SN}},
        "motivacao_principal": SN,
        "gancho_pessoal": SN,
        "precos_falados": {"type": "array",
                           "items": {"type": "object", "additionalProperties": False,
                                     "required": ["servico", "escopo", "valor"],
                                     "properties": {"servico": S, "escopo": SN, "valor": SN}}},
        "script_coverage": {"type": "object", "additionalProperties": False,
                            "required": ["perguntou_carro_novo", "perguntou_garagem",
                                         "perguntou_keep_or_trade", "perguntou_outros_orcamentos",
                                         "apresentou_ballpark"],
                            "properties": {k: B for k in
                                           ["perguntou_carro_novo", "perguntou_garagem",
                                            "perguntou_keep_or_trade", "perguntou_outros_orcamentos",
                                            "apresentou_ballpark"]}},
        "voicemail_left": B,
        "resultado": {"type": "string", "enum": ["atendida", "nao_atendida", "voicemail"]},
        "proxima_acao": {"type": "object", "additionalProperties": False,
                         "required": ["tipo", "data_sugerida", "motivo"],
                         "properties": {"tipo": {"type": "string",
                                                 "enum": ["follow_up", "enviar_quote", "agendar",
                                                          "transferir_rafael", "descartar"]},
                                        "data_sugerida": SN, "motivo": S}},
        "resumo_3_linhas": S,
        "coaching": S,
    },
}

SYSTEM = """Você analisa chamadas de vendas da Elite Premium Detailing (detailing automotivo premium em Davie/FL: PPF, ceramic coating, wrap). Quem liga/atende pelo negócio é o Eugene (assistente) ou o Rafael (dono). O lead é um potencial cliente.

Extraia APENAS o que está na transcrição — não invente. Campos sem evidência ficam null.
- momento.faixa: quando o lead comprou/vai receber o carro (recem_entregue|chegando|menos_3m|mais_3m|mais_6m|mais_1a|null).
- intencao.nivel: pediu_quote|sem_recuar (discutiu preço sem recuar)|indeciso|so_pesquisando|null.
- gancho_pessoal: detalhe pessoal reutilizável no follow-up (ex.: "aniversário da filha, volta quarta").
- precos_falados: TODOS os valores citados, com serviço e escopo exatos.
- voicemail_left: se a call não foi atendida, o operador deixou recado?
- coaching: julgue PRIMEIRO pelo resultado. Se o cliente conseguiu o que queria (ex.: agendou,
  recebeu o preço que pediu), a call foi um SUCESSO — diga isso e sugira no máximo UMA melhoria
  proporcional ao contexto. NÃO cobre o checklist completo de qualificação (orçamento, garagem,
  concorrência, keep-or-trade) em chamadas simples/transacionais que converteram — esses itens
  são para conversas de venda consultiva (PPF/ceramic de alto valor) que NÃO fecharam.
  script_coverage continua sendo registrado como fato, mas ausência de item ≠ erro.
- resumo_3_linhas: máx 3 linhas, direto, em inglês (o Eugene lê em inglês).
A transcrição vem diarizada (S0/S1...) e pode ser em inglês, espanhol ou português.
O atendente pode ser o Eugene OU o Rafael (dono) — não presuma qual dos dois."""


def get_client():
    key = _cfg["ANTHROPIC_API_KEY"]
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY ausente no .env")
    return anthropic.Anthropic(api_key=key)


def analyze_call(transcript_text, call_meta, client=None):
    """transcript_text: transcrição diarizada. call_meta: dict direction/duration/lead name etc."""
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
        messages=[{
            "role": "user",
            "content": (
                f"Metadados da chamada: {json.dumps(call_meta, ensure_ascii=False)}\n\n"
                f"Transcrição diarizada:\n{transcript_text}"
            ),
        }],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("análise recusada pelo modelo")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
