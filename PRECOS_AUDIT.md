# PRECOS_AUDIT — auditoria da tabela de preços (2026-07-08)

## 1. De onde vieram os valores ERRADOS (confissão técnica)
Eu **nunca tive as tabelas oficiais** (as versões do spec com A7.3 não chegaram como arquivo).
Para não deixar o painel sem preços, **estimei** a partir de dados observados — e errei em dois níveis:
- **Fonte errada:** usei valores de JOBS reais das planilhas 2024–2026 e de chamadas (ex.: job da Nina
  "Full Front PPF + gold pack $5.849" virou uma linha de tabela; job do Felipe "$5.570 full colored"
  virou "full body from $5.350"; "$1.500 partial" e "$6.500 full body" foram interpolações minhas).
  Jobs contêm negociação/combos únicos — **não são tabela**.
- **Produto composto inventado:** "Full front + gold pack" nunca existiu como item de tabela. PROIBIDO
  daqui em diante (regra gravada no próprio prices.json).

## 2. Diff completo — antes (errado) → depois (tabela oficial do Rafael)
| Item | ANTES (estimado) | DEPOIS (oficial) |
|---|---|---|
| PPF partial front | $1.200–1.900 por tier | **from $899** |
| PPF full front | 1900/2200/2500/2900 | **1990/2200/2350/2450** |
| PPF track pack | (não existia) | **from $2.690** |
| PPF full body | 5500/6500/7500/8500 | **4990/5550/5850/6450** |
| PPF full front + gold pack | $5.849 ← INVENTADO | **REMOVIDO** |
| PPF full colored/matte | from $5.350 ← job real, não tabela | **REMOVIDO** |
| Ceramic Bronze | (não existia) | **599/699/799/899** |
| Ceramic Silver | 799/799/999/1199 | **799/999/1099/1300** |
| Ceramic Gold | 1400/1600/1800/2100 | **1749/1975/2199/2349** |
| Paint correction (por etapa) | 300/350/400/500 | **500/500/550/600** |
| Wheels off | (não existia) | **$450 (fixo)** |
| Leather protection | (não existia) | **$499 (fixo)** |
| Interior ceramic 500-800 · Tint 200-850 · Wrap from 5000 | estimados | **REMOVIDOS** (não estão na tabela oficial passada; se existirem tabelas deles, Rafael adiciona no prices.json) |

Backup do arquivo errado: `out/prices_ANTES_auditoria.json`.

## 3. Hierarquia do card de quote (spec 6.1) — corrigida
- Card de quote agora abre com o bloco **"The quote (what THIS client received)"**: serviço + valor
  exato falado na call + data de envio + **link clicável** go.urable.com + sentimento da call.
- Sem dados extraídos ainda → o card declara: *"Quote sent [data] — details pending analysis.
  **Open the conversation to review before calling.**"*
- A tabela genérica **nunca mais aparece** em card de quote (bloqueada no código).

## 4. Varredura dos cards no ar
- 11 cards de quote retro-enriquecidos agora: **K WASHINGTON** e Shahram Siddiqui já mostram
  link+data reais da quote; os outros 9 mostram o aviso honesto de "pending analysis".
- Preços armazenados fora da tabela oficial em qualquer card aberto: **0** (os preços genéricos
  eram renderizados dinamicamente do prices.json — corrigida a fonte, corrigiu-se toda a exibição).
- Porte desconhecido → agora exibe a **linha completa** rotulada "General price table — car tier
  unknown" (nunca chuta Standard).

---

## 5. A9.1 + A10 (2026-07-08, noite) — três classes de preço + filosofia da visita

### Classes no prices.json (fonte única, editável pelo Rafael)
| Classe | Itens | Comportamento no card |
|---|---|---|
| `tabela` | PPF partial/full front/track/full body · Ceramic Bronze/Silver/Gold · paint correction · wheels · leather | Valor do tier exibido como **"starts at $X"** — regra universal A10: telefone não fecha número final |
| `starting_price` | **Vinyl wrap: 3.000 / 3.500 / 3.800 / 4.000** (+ "final price depends on the material selected") · **Color change PPF: 4.990 / 5.550 / 5.850 / 6.450** (valores do Full Body, + "price varies by color") | "Starting at $X" + a JOGADA: convidar pra loja → ver materiais → preço final na hora → **depósito trava material e agenda a instalação** |
| `custom_quote` | (vazia — Rafael adiciona o que quiser) | Nunca exibe preço; manda checar quote do Urable ou escalar |

### Mudanças de classe nesta rodada
- **Vinyl wrap**: custom_quote → **starting_price** (A9.1) com os 4 tiers acima.
- **Color change PPF**: custom_quote → **starting_price** (A10.3) herdando os valores do Full Body PPF.

### Regras que acompanham
- **Feche a visita (A10, universal)**: todo "How to play it" (new lead, warm, quote, first touch)
  termina no convite/agendamento da visita; venda final e upsell são presenciais (Rafael).
- **Add-ons "only if asked"** (`mention_only_if_asked`): paint correction, interior/leather
  coating, wheels & calipers — rotulados no card e no Price sheet; a análise NÃO penaliza não
  oferecer e registra observação se forem empurrados (`extras_empurrados`).
- **Análise**: wraps/color change → `proxima_acao = agendar_visita` (nunca enviar_quote por padrão);
  advice reforça "não feche número por telefone".
- **Validação de ballpark (viva, tabela `price_alerts`)**: starting_price → falar **ACIMA** do
  starting do tier é ok (material melhor), **ABAIXO** gera alerta na visão do dono; tabela →
  divergência ±5% gera alerta. Tier desconhecido → compara com a faixa geral, nunca chuta.
- **Briefing pré-venda (spec 6.5)**: visão do Rafael ganhou "Visitas de hoje e amanhã" com dossiê
  por appointment (interesse, preços exatos falados com data, sentimento, ganchos, quote/link,
  upsell por perfil) + versão no relatório das 18:30 (visitas de amanhã).
