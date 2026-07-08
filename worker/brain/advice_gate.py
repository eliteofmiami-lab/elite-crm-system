"""
A12-d: crítico automático de advice — segunda passada com Haiku valida cada advice
contra os 4 testes e a lista banida ANTES de exibir. Reprovado = descartado + logado
em `advice_rejected` (auditoria). Terminologia: Advice/Alert — nunca "coaching".
"""
import json

from brain import analyze, cards

CRITIC_MODEL = "claude-haiku-4-5"

GATE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["aprovado", "motivo"],
    "properties": {"aprovado": {"type": "boolean"}, "motivo": {"type": "string"}},
}

SYSTEM = """Você é o crítico de qualidade de "advice" de vendas da Elite Premium Detailing.
Recebe um advice gerado por outra IA a partir de uma transcrição de call, e decide se ele
pode ser exibido. REPROVE (aprovado=false) se falhar QUALQUER teste:
1. EVIDÊNCIA: a evidência citada deve ser um trecho real da transcrição (compare o texto —
   pequenas diferenças de diarização são ok; evidência vazia ou inventada = reprovado).
2. ALAVANCA DE CONVERSÃO: o advice deve mexer em fechamento de visita, defesa de valor,
   timing, tratamento de objeção ou upsell contextual. Higiene de processo = reprovado.
3. NÃO-REDUNDANTE: reprovar se recomenda o que o sistema já automatiza: registrar/pegar
   telefone ou dados do cliente (caller ID já captura), anotar/logar informações no CRM,
   mover stage, criar/agendar follow-up (vira task automática), mandar wrap-up.
4. LISTA BANIDA: pedir dados que o sistema já captura; "seja mais empático/confiante" e
   genéricos; sugestões de CRM/processo; qualquer coisa não ancorada na transcrição.
Advice bom é raro e específico. Na dúvida, REPROVE — silêncio vale mais que filler.
motivo: 1 frase objetiva (em português) citando o teste que falhou ou "passa nos 4 testes"."""


def validate(advice_en, evidencia, transcript, resumo="", client=None):
    """Retorna (aprovado: bool, motivo: str). Falha do crítico = reprova (fail-closed)."""
    if not advice_en:
        return False, "advice vazio"
    client = client or analyze.get_client()
    try:
        r = client.messages.create(
            model=CRITIC_MODEL, max_tokens=300,
            system=[{"type": "text", "text": SYSTEM,
                     "cache_control": {"type": "ephemeral"}}],
            output_config={"format": {"type": "json_schema", "schema": GATE_SCHEMA}},
            messages=[{"role": "user", "content": (
                f"ADVICE: {advice_en}\n\nEVIDÊNCIA CITADA: {evidencia or '(vazia)'}\n\n"
                f"RESUMO DA CALL: {resumo}\n\nTRANSCRIÇÃO:\n{(transcript or '')[:12000]}"
            )}])
        out = json.loads(next(b.text for b in r.content if b.type == "text"))
        return bool(out.get("aprovado")), out.get("motivo", "")
    except Exception as e:
        return False, f"crítico indisponível ({str(e)[:80]}) — fail-closed"


def gate_analysis(analysis, transcript, call_id=None, contact_id=None, client=None):
    """Aplica o portão ao payload da análise IN-PLACE. Retorna (payload, aprovado, motivo).
    Reprovado: advice_* esvaziados + linha em advice_rejected p/ auditoria."""
    adv = analysis.get("advice_en") or ""
    if not adv:
        return analysis, True, "sem advice (silêncio válido)"
    ok, motivo = validate(adv, analysis.get("advice_evidencia"),
                          transcript, analysis.get("resumo_3_linhas", ""), client=client)
    if not ok:
        cards._sb("POST", "advice_rejected", json={
            "call_id": call_id, "contact_id": contact_id,
            "advice_en": adv, "advice_pt": analysis.get("advice_pt"),
            "evidencia": analysis.get("advice_evidencia"), "motivo": motivo})
        analysis["advice_en"] = analysis["advice_pt"] = ""
        analysis["advice_motivo_silencio"] = f"reprovado pelo crítico: {motivo}"
        print(f"  [advice-gate] REPROVADO: {adv[:60]!r} — {motivo}")
    return analysis, ok, motivo
