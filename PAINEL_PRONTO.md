# PAINEL_PRONTO — Daily Board no ar · 2026-07-08 13:10 ET

**URL:** https://elite-crm-panel.vercel.app/ · espelho do GHL a cada 5 min (cron ativo)
· **zero IA, zero transcrição, zero escrita no GHL** (write_log mudo — md5 idêntico ao
baseline; custo IA do período: **$0,00** no cost_log).

## Screenshot textual — colunas populadas com dados REAIS (13:05 ET)

**Card verde (topo):** Calls today **51/100 valid** · Sales goal July (comissões
elegíveis: 14 — 5 confirmed · 8 done/waiting · 1 expired) · Clean-board bonus Jul 1–15
· Max this month $600. **Faixa vermelha: 16 calls do Eugene sem resolução** (4 de
outros usuários só na aba Owner).

| Col | Título | Abertos | Exemplos reais |
|---|---|---|---|
| 1 | Return · Reply · Hot | 204 | GEORGE LASHLEY (HOT since Jul 07) · JUDY MONDOL · 3 missed inbound · 4 SMS awaiting reply |
| 2 | New Leads — Call ASAP | 9 | Ianet Lopez (2020 RAV4) · Albert Meran (2026 Corolla) · Robert Mitchell (2019 Lexus GSF) |
| 3 | Tasks & Quote follow-ups | 4 | Sonia Gray "Call to check" due today · Jose Guilbe (2026 Model Y, "will receive the car…") · 1 Urable sem resposta |
| 4 | Pipeline follow-ups | 355 | Darío Stoka (2026 BMW M5 Touring, Contact 1 AM) · Bernard Goupy (Tesla 3, Both) |
| 5 | Appointments · next 2 days | 2 | ✓ Nelson Garcia (2026 CT4-V Blackwing, Jul 10 9:00) · ✓ Carl Casagrande (Jul 10 16:00) — com última nota do contato (ou "no notes yet") |
| 6 | Warm up (ração 20) | 18 | Rhonda Redd (Lost recuperável Jul 07) · Jermaine Jackson (Ceramic Pro) |

⚠️ **Nota da coluna 1:** os ~197 HOT são o bloco LEGADO que a migração de ontem moveu
pro stage HOT LEADS (stage-change = Jul 07). O espelho mostra a verdade; em 3 dias eles
**envelhecem sozinhos pra ração do Warm up** (janela de 3d). Se quiser antecipar: bulk
manual (FAXINA_DIA_ZERO.md tem as listas).

## Regra da Resolução — viva

- Tentativa válida (determinística): call atendida OU ≥25s + SMS manual do MESMO
  usuário ≤10 min; SMS de workflow NUNCA conta. Hoje: Eugene 51 válidas / 57 discadas.
- 16 cards vermelhos "NO RESOLUTION" reais agora (calls de hoje sem desfecho em 15 min)
  — cada um com a árvore fixa: appointment · task com data · estimate+Quote Sent ·
  Lost com motivo · (não atendida → próximo stage).
- Resoluções detectadas por leitura fecham sozinhas: 3 cards resolvidos no ciclo 2.

## Comissões (5 casos do Rafael) — auditáveis

- 22 appointments do mês processados: **14 criados pelo Eugene → elegíveis diretos**
  ("created by Eugene Jul 08"), 8 por "other" → só com confirmação ativa dele
  (nenhuma detectada → NÃO elegíveis, motivo gravado).
- ⚠️ **"other" inclui um userId deletado (`Aiqssn…`, via mobile_app)** — confirme:
  era uma conta SUA antiga? Se sim está correto (não-Eugene); se era do Eugene,
  me diga que eu adiciono o id ao mapa dele no config.

## Aceite (lead teste-interno — itens ao vivo para você rodar)

| Teste | Como verificar | Status |
|---|---|---|
| Inbound perdida → card col 1 em ≤5 min | ligue do teste-interno e não atenda | pronto p/ teste ao vivo |
| Call sem ação → vermelho em 15 min | ligue do painel e não registre nada | **já provado com dados reais (16 no ar)** |
| Task/stage/SMS fecha o card no ciclo | crie a task no GHL após a call | **provado (3 resoluções no ciclo 2)** |
| Appointment de amanhã sem confirmação → col 5 | crie appointment amanhã sem confirmar | grupo "To confirm" ativo (0 pendentes agora — os 2 do momento estão confirmados) |
| Clock-in libera o quadro | login do Eugene | implementado (gate na tela) |
| Win/pós-venda/teste-interno não geram cards | — | filtros ativos (test_contact_ids + estados silenciados) |
| Zero IA + custo ~$0 | cost_log desde 12:00 ET | **$0,00 ✓** |

## Config única (`board_config` no Supabase — edite lá, sem deploy)

janelas 3d/7d/14d/30d · ração 20 · 25s/10min · resolução 15 min · checkpoint 13:00 ·
metas 100/dia e 30/35/40 ($10/$20, bônus $50, teto $600) · user_ids · confirm_mode.

## Fora de horário (você cria, ~15 min)

[GUIA_WORKFLOWS_FORA_DE_HORARIO.md](GUIA_WORKFLOWS_FORA_DE_HORARIO.md) — 4 workflows
nativos com os textos prontos. + [FAXINA_DIA_ZERO.md](FAXINA_DIA_ZERO.md) (172 opps
>90d candidatas ao bulk → Lost) e suas 4 decisões pendentes (janelas, corte, horário,
textos).

## Congelado (código preservado, nada roda)

Advice/IA, sínteses, rascunhos, wrap-up, bonus guard antigo, comissões antigas,
relatórios 18:30, board de toques, briefing, cupom, retro (batches no servidor),
rail/fila antiga, extensão. CAPI watcher tb fora do ciclo (workflow nativo Great Cars
segue funcionando — me diga se quiser o watcher de volta).

*Painel entregue. Parado, aguardando o Rafael.*
