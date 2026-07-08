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
