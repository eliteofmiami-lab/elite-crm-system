"""Análise de transcrição de chamada com Claude (Sonnet) — spec 2.2 da Fase 1.
Saída em JSON estruturado garantido via output_config.format (json_schema)."""
import json

import anthropic

import config

MODEL = "claude-sonnet-5"
MODEL_CHEAP = "claude-haiku-4-5"   # A8: calls curtas/simples → Haiku (5x mais barato)
ROUTE_THRESHOLD_SEC = 150          # <150s = call curta

# preço por 1M tokens (in, out) — para o cost_log
PRICING = {"claude-sonnet-5": (3.0, 15.0), "claude-haiku-4-5": (1.0, 5.0)}

_cfg = config.load()

# Schema do JSON estruturado (spec 2.2). additionalProperties=false obrigatório.
S = {"type": "string"}
B = {"type": "boolean"}
# nota: a API limita campos union/nullable a 16 — texto "sem evidência" usa "" (string vazia)
SN = {"type": "string"}
ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["vehicle", "momento", "intencao", "sentimento", "motivacao_principal",
                 "servico_interesse", "gancho_pessoal", "precos_falados", "script_coverage",
                 "voicemail_left", "resultado", "proxima_acao", "resumo_3_linhas",
                 "advice_en", "advice_pt", "advice_evidencia", "advice_alavanca",
                 "advice_motivo_silencio", "pergunta_tecnica", "visita_loja",
                 "extras_empurrados", "cupom_oferecido", "resolucao_da_call"],
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
        "servico_interesse": SN,
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
                                                          "agendar_visita",
                                                          "transferir_rafael", "descartar"]},
                                        "data_sugerida": SN, "motivo": S}},
        "resumo_3_linhas": S,
        # A12-d: advice com portão de qualidade — "" = sem advice (silêncio é válido)
        "advice_en": S,
        "advice_pt": S,
        "advice_evidencia": S,        # trecho LITERAL da transcrição que embasa o advice
        "advice_alavanca": S,         # fechamento_visita|defesa_valor|timing|objecao|upsell_contextual
        "advice_motivo_silencio": S,  # quando advice="" (ex.: "call bem conduzida")
        # A11/A11.1: pergunta técnica (modo observação)
        "pergunta_tecnica": {"type": "object", "additionalProperties": False,
                             "required": ["houve", "transferida", "resposta_improvisada",
                                          "prometeu_callback", "pergunta", "categoria"],
                             "properties": {"houve": B, "transferida": B,
                                            "resposta_improvisada": B,
                                            "prometeu_callback": B,
                                            "pergunta": SN, "categoria": SN}},
        # A12-c: visita à loja mencionada na call (vira visita_provavel, não prova)
        "visita_loja": {"type": "object", "additionalProperties": False,
                        "required": ["ja_visitou_mencionado", "evidencia"],
                        "properties": {"ja_visitou_mencionado": B, "evidencia": SN}},
        # A10: extras empurrados sem o cliente pedir (observação, nunca punição)
        "extras_empurrados": B,
        # A13: cupom de $200 mencionado/oferecido na call
        "cupom_oferecido": {"type": "object", "additionalProperties": False,
                            "required": ["houve", "contexto"],
                            "properties": {"houve": B, "contexto": SN}},
        # A14: resolução da call — qualificou|avancou|desqualificou|pendente ("" se n/a)
        "resolucao_da_call": SN,
    },
}

SYSTEM = """Você analisa chamadas de vendas da Elite Premium Detailing (detailing automotivo premium em Davie/FL: PPF, ceramic coating, wrap). Quem liga/atende pelo negócio é o Eugene (assistente) ou o Rafael (dono). O lead é um potencial cliente.

Extraia APENAS o que está na transcrição — não invente. Campos de TEXTO sem evidência
ficam com string vazia "" (nunca invente); enums sem evidência ficam null.
- momento.faixa: quando o lead comprou/vai receber o carro (recem_entregue|chegando|menos_3m|mais_3m|mais_6m|mais_1a|null).
- intencao.nivel: pediu_quote|sem_recuar (discutiu preço sem recuar)|indeciso|so_pesquisando|null.
- gancho_pessoal: detalhe pessoal reutilizável no follow-up (ex.: "aniversário da filha, volta quarta").
- servico_interesse: o serviço que o cliente ESTÁ buscando AGORA, em inglês, nome curto
  (ex.: "Color change PPF", "Full front PPF", "Ceramic coating", "Window tint", "Vinyl wrap").
  null se a call não deixar claro.
- precos_falados: TODOS os valores citados, com serviço e escopo exatos.
- voicemail_left: se a call não foi atendida, o operador deixou recado?
- proxima_acao: a FILOSOFIA da loja é fechar a VISITA, não número final por telefone.
  Para lead engajado (e SEMPRE para vinyl wrap / color change), prefira tipo=agendar_visita
  (ver materiais na loja → preço final na hora → depósito trava material e agenda).
  enviar_quote continua válido quando o cliente pede número por escrito.

REGRA Nº 1 — ADVICE COM PORTÃO DE QUALIDADE (A12). Advice só existe se passar nos 4 testes:
  (a) EVIDÊNCIA: advice_evidencia = trecho LITERAL da transcrição em que se baseia
      (copie as palavras exatas). Sem trecho literal → NÃO há advice.
  (b) ALAVANCA DE CONVERSÃO: só fechamento de visita, defesa de valor, timing, tratamento
      de objeção ou upsell contextual (advice_alavanca com um desses valores).
      Higiene de processo NUNCA é advice.
  (c) NÃO-REDUNDANTE: PROIBIDO recomendar o que o sistema já automatiza — registrar
      telefone/dados (o caller ID já captura), anotar/logar informações, mover stage,
      agendar follow-up (já vira task), mandar mensagem de wrap-up (já tem fluxo).
  (d) SILÊNCIO É OUTPUT VÁLIDO E PREFERÍVEL A FILLER: call bem conduzida →
      advice_en = advice_pt = "" e advice_motivo_silencio = "call bem conduzida" (ou similar).
  LISTA BANIDA (nunca gere): pedir dados que o sistema já captura; "seja mais
  empático/confiante" e genéricos sem evidência; sugestões de CRM/processo; qualquer coisa
  não ancorada na transcrição. Julgue PRIMEIRO pelo resultado: se o cliente conseguiu o que
  queria, a call foi um SUCESSO — o padrão é silêncio. NÃO cobre checklist de qualificação
  em call transacional que converteu. advice_en/advice_pt = o MESMO insight nos 2 idiomas,
  1-2 frases, tom construtivo. O advice deve reforçar a estratégia da visita quando couber
  ("não feche número final por telefone — feche a visita").
- pergunta_tecnica (classificação CONSERVADORA — A11.1): técnica = exige julgamento de
  especialista (avaliação do estado da pintura, instalação painel a painel, comparação
  profunda de specs, caso-limite de garantia). NÃO são técnicas (lane do operador): marca e
  linha de produto (usamos Ceramic Pro, instalador certificado, garantia vitalícia, Carfax),
  conteúdo dos pacotes, garantia básica, prazos e preços. houve=true só para pergunta
  técnica DE VERDADE; prometeu_callback=true se o operador prometeu retorno do
  técnico/dono; categoria = tema curto (ex.: "estado da pintura").
- visita_loja.ja_visitou_mencionado: true APENAS se a conversa indicar que o lead JÁ ESTEVE
  na loja (ex.: "when I was there...", "passei aí semana passada") — com o trecho em
  evidencia. Planejar visita futura NÃO conta.
- extras_empurrados: true se o operador ofereceu add-ons (paint correction, interior
  coating, wheels) SEM o cliente perguntar. Não oferecer extras NUNCA é erro.
- cupom_oferecido (A13): houve=true se o operador ofereceu/mencionou um cupom/desconto de
  $200 para fechar agendamento/visita; contexto = a frase usada.
- resolucao_da_call (A14): o desfecho REAL da conversa — "qualificou" (interesse+dados
  confirmados), "avancou" (agendou/pediu quote/aceitou próximo passo), "desqualificou"
  (sem carro, sem interesse real, fora de perfil, número errado — derruba o lead),
  "pendente" (nada definido) ou "" se não se aplica (ex.: voicemail).
- resumo_3_linhas: máx 3 linhas, direto, em inglês (o Eugene lê em inglês).
A transcrição vem diarizada (S0/S1...) e pode ser em inglês, espanhol ou português.
O atendente pode ser o Eugene OU o Rafael (dono) — não presuma qual dos dois."""


def get_client():
    key = _cfg["ANTHROPIC_API_KEY"]
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY ausente no .env")
    return anthropic.Anthropic(api_key=key)


def analyze_call(transcript_text, call_meta, client=None):
    """transcript_text: transcrição diarizada. call_meta: dict direction/duration/lead name etc.
    A8: roteia Haiku (curtas) / Sonnet (longas); cache no system prompt; anexa _meta de custo."""
    client = client or get_client()
    # A8 (spec integral): análise COMPLETA de call atendida é SEMPRE Sonnet.
    # Haiku fica para tarefas leves (voicemail check, triagens, classificação de porte).
    model = MODEL
    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=[{"type": "text", "text": SYSTEM,
                 "cache_control": {"type": "ephemeral"}}],
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
    result = json.loads(text)
    pin, pout = PRICING[model]
    u = response.usage
    result["_meta"] = {
        "model": model,
        "in_tokens": u.input_tokens, "out_tokens": u.output_tokens,
        "est_usd": round(u.input_tokens / 1e6 * pin + u.output_tokens / 1e6 * pout, 5),
    }
    return result
