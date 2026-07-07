# GATE G0-A — Proposta: custom fields de OPORTUNIDADE (aprovar antes de criar)

> Hoje a conta tem **0 custom fields de oportunidade**. O sistema precisa gravar o score e o estado de trabalho no nível da oportunidade. Abaixo o que proponho criar **via API** (`POST /locations/{locationId}/customFields` com `model=opportunity`). **Nada será criado até o Rafael aprovar esta lista.**

## Campos propostos

| # | Nome (label) | fieldKey | Tipo | Para que serve | Exemplo |
|---|---|---|---|---|---|
| 1 | Elite Score | `opportunity.elite_score` | NUMERICAL | Score total conhecido do lead (0–100) | `75` |
| 2 | Elite Score Breakdown | `opportunity.elite_score_breakdown` | TEXT | Decomposição legível do score | `car:35 mom:? eng:25 int:15` |
| 3 | Elite Sentimento | `opportunity.elite_sentimento` | TEXT | Sentimento extraído da última chamada (M2) | `positivo; achou preço ok` |
| 4 | Elite Quote Sent | `opportunity.elite_quote_sent` | CHECKBOX (bool) | Se já foi enviada quote (link Urable detectado) | `true` |
| 5 | Elite Quote Link | `opportunity.elite_quote_link` | TEXT | O link `go.urable.com/…` enviado | `https://go.urable.com/5aWeqD` |
| 6 | Elite Touchpoints | `opportunity.elite_touchpoints` | NUMERICAL | Nº de toques de saída (SMS+call+email) | `9` |
| 7 | Elite Next Action | `opportunity.elite_next_action` | TEXT | Próxima ação recomendada pelo cérebro | `Ligar — carro alvo` |

## Observações
- **CHECKBOX no GHL** pode exigir um valor de opção; se a API não aceitar boolean puro, uso TEXT com `true`/`false` (decido na criação e registro no `write_log.jsonl`).
- Score é gravado como número (`elite_score`) **e** como texto `conhecido/máximo` fica no breakdown — assim o funil filtra por número e o humano lê o contexto.
- Esses 7 campos cobrem M0 (write-back) e já deixam prontos os que o M2 preenche (sentimento, next_action).
- **Não** proponho custom fields de contato novos aqui — os de veículo já existem; se o M2 precisar de algum, entra em gate próprio.

## O que acontece após aprovação (GATE G0-A)
1. Crio os 7 campos via API (só criação, sem tocar em dado existente).
2. Registro cada criação em `out/write_log.jsonl`.
3. Devolvo os `id` gerados e sigo para **G0-B** (gravar os scores dos 330 leads nesses campos).

**Para aprovar:** responda "aprovado G0-A" (ou peça ajustes na lista acima).
