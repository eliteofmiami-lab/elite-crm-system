# PENDENCIAS — verificação item a item (Missão Final, Etapa 1)
*2026-07-08 (rev 2). Os adendos completos A5–A8 chegaram VIA CHAT — deltas fechados nesta revisão:
enum exato keep_or_trade (Leasing→ângulo PPF lease) · campos garaged/chegada/motivação ·
Lost reasons c/ terminais fora das cold calls + opp→Lost no save · wrap-up SÓ na 1ª call
atendida · advice do lead injetado no próximo card (A6.3) · bonus_guard_events + estado
"lost this period" no painel · análise completa SEMPRE Sonnet (A8) · matriz de preços
por porte + classificador de tier + Price sheet em tabela (A7.3).
AINDA DEPENDEM DE INSUMO: valores oficiais da matriz (Rafael revisa config/prices.json) ·
frases integrais do playbook (docx não lido — hints atuais são aproximações) ·
lost reasons oficiais do GHL (usando lista padrão) · override manual de tier no card (v2).*

| Item | Estado | Evidência |
|---|---|---|
| Acordeão da fila (todos os cards abrem) | ✅ FEITO agora | clique em qualquer linha expande (Why now/How/preços/ações); task 1 sempre aberta |
| Wrap-up condiciona conclusão ao nice-to-talk (8.1) | ✅ FEITO agora ⚠️ | Log call "Answered — good talk" → card vira `wrapup` com rascunho; só conclui no "Approve & send" (envio real aguarda G2 via `outbox`) |
| Log call details completo (8.2/A7.1) | ✅ FEITO agora ⚠️ | + `keep_or_trade` (4 opções), `seen_other_quotes` c/ campo expansível de frases integrais, `lost_reason` (6 motivos sincronizados painel↔nota GHL) |
| Preços por card + Price sheet + prices.json fonte única (6.2/A7.3) | ✅ FEITO agora | `config/prices.json` (repo) → robô sincroniza → botão 💲 Price sheet no topo + bloco "Prices" no card por categoria detectada |
| Prioridade New Leads parados (A7) | ✅ já estava | first_touch topo da Camada 2, score desc + recência (64 achados na 1ª varredura) |
| Elegibilidade Win/Lost/delete + expurgo (A7.4) | ✅ já estava | regra dura na criação + purge por ciclo; auditoria: fila viva tinha 0 inelegíveis (os 4 nomes citados estavam só no doc estático da F0, agora marcado OBSOLETO) |
| Bonus guard proativo (A5.1) | ✅ FEITO agora ⚠️ | 10:15 appts amanhã · 15:00 quotes do dia · 16:30 card urgente · 80+ perto das 24h → card + linha no cartão de comissões |
| Advice bilíngue nas duas vistas (A6) | ✅ já estava | `advice_en`/`advice_pt` por análise; Eugene vê EN, dono vê EN (decisão do Rafael: tudo EN) |
| teste-interno fora de score/CAPI/relatórios/comissões | ✅ já estava | guards no worker + Diagnostics c/ "Clear test data" |
| Zero "COACHING" na UI | ✅ | grep no web/: zero ocorrências; tags = Advice/Alert/Watch/Report |

## Etapas seguintes (mesma missão)
| Etapa | Estado |
|---|---|
| E2 — G2 | G2_DEMO.md pronto (5 calls) — **aguarda "aprovado G2" do Rafael**; ativação = flip do DRY_RUN com guardrails já codificados |
| E3 — M4 relatórios+quinzena+payouts | ✅ construído e testado hoje (job 18:30 ET agendado; payout dias 15/último; deadline 15/07 OK) |
| E4 — M5 cold calls | ✅ pool 1.433 ranqueados (lost/no-show/legado), refresh semanal, top-up automático da fila |
| E5 — A8 custos | ✅ routing Haiku/Sonnet + cache + skip<20s + cost_log + linha no relatório + alerta $150 + CUSTO_ESTIMADO.md (~$7,5/mês) |
| E6 — hardening/handover | ✅ idempotência (ids processados/event_id/upserts), retry 429+timeout, ET na quinzena/relatórios/guard, retry de gravação 3x c/ flag, SISTEMA_OVERVIEW.md + RUNBOOK.md · **senhas: Rafael ainda não trocou** |
| E7 — GO | ver checklist no chat (itens do Rafael pendentes) |
