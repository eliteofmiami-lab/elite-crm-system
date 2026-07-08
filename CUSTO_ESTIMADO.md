# CUSTO_ESTIMADO — projeção mensal de IA (base: volume real de 40 dias)

## Volume observado
- Calls atendidas >20s: **338** em 40 dias → **8.4/dia** ≈ 253/mês
- Duração média: **2.3 min**

## Projeção mensal (com as otimizações A8 ativas)
| Item | Cálculo | $/mês |
|---|---|---|
| Deepgram (nova-2, $0.0043/min) | 253 calls × 2.3 min | **$2.48** |
| Claude Sonnet 5 (calls ≥150s, ~55%) | ~3.5k in + 1.2k out tokens/call | **$3.97** |
| Claude Haiku 4.5 (calls <150s, ~45%) | idem, 5x mais barato | **$1.08** |
| **TOTAL projetado** | | **$7.54/mês** |

Teto configurado: **$150/mês** → projeção usa **5%** do teto. Alerta automático no relatório diário se o acumulado passar de $150.

## Otimizações A8 ativas
- Roteamento por duração (<150s → Haiku) · skip de calls <20s · cache no system prompt
  (efetivo só se o prompt crescer >2k tokens) · custo real de CADA call em `cost_log`
  (painel/relatório) · linha de custo no relatório do dono · batch reservado p/ backfills.
