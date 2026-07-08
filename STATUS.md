# STATUS — Sistema Elite CRM vs. plano da Fase 1
*Gerado em 2026-07-07 ~21h ET. Fonte: código no repo, write_log.jsonl, verificações ao vivo.*

## Milestones

| Item | Estado | Evidência |
|---|---|---|
| **M0** Fundações + Score v2 | **FEITO** | 7 custom fields de opp criados (G0-A, 201×7); score gravado em 330/330 opps 40d (G0-B, 0 falhas); score v2 em `worker/score.py`; backfill dos ativos migrados rodando agora |
| **M1** Migração ELITE ADS → New Pipeline | **FEITO** | G1 executado: 203/203 movidas (198→HOT LEADS), 95/95 dups tagueadas, 0 falhas; contagens pós-migração verificadas; stage HOT LEADS criado via API |
| **M2** Cérebro pós-chamada | **PARCIAL** | Ingestão+Deepgram+Claude RODANDO (ciclo 5min no GitHub Actions, calls novas transcritas/analisadas, advice bilíngue, persistência no Supabase, score em tempo real). **Escritas GHL pós-call (stages/tasks/notas/SMS) em DRY-RUN — aguardam GATE G2.** 2.4 (Urable prep) e 2.5 (nice-to-talk) não iniciados |
| **M3** Painel | **FEITO (v4)** | elite-crm-panel.vercel.app no ar; design do mockup v4; Eugene EN + Owner EN; clock in/out+break; task 1 expandida; snooze; advice; rules; 🇪🇸 flags; "Work the queue" + "View Eugene's screen"; fila com 56+ cards reais |
| **M4** Relatórios diários 18:30 | **NÃO INICIADO** | job das 22:30 UTC existe no workflow mas `eod_report.py` ainda não implementado |
| **M5** Cold calls ranqueadas | **NÃO INICIADO** | base pronta (2.066 opps no legado + 873 Lost + no-shows identificados), ranking não construído |

## Adendos

| Item | Estado | Evidência |
|---|---|---|
| **A1** HOT LEADS + inbound | **FEITO** | stage criado (posição 1); workflow inbound cria opp nele (Rafael ajustou); regra anti-regressão no cérebro; migração usou o mapeamento novo |
| **A2** Número Google Ads | **FEITO** | +17544650696 confirmado ("Google Leads" A2P); config no cérebro; tag `inbound-google-ads` aguarda G2 |
| **A3** Auditoria de SMS | **FEITO** | `docs/SMS_CADENCE_AUDIT.md` — 515 templates, taxas de resposta, ranking |
| **A4** Comissão $10/appointment | **PARCIAL** | tabela `commissions` + widget no painel + regras/bonus na UI prontos; **motor que registra/converte/expira comissões ainda não roda** (depende G2/M4) |

## Respostas diretas

**1. O painel usa dados reais ou mock?** **REAIS.** Cards vêm de leituras ao vivo do GHL (stages Quote Sent/HOT LEADS/Great Cars/calendários) gravadas no Supabase pelo worker; scores vêm dos custom fields reais; advice virá das análises reais. Mock: nenhum. Métricas ainda vazias (comissões, avg response) mostram 0/— até o motor respectivo ligar — não são simuladas.

**2. Custom fields de oportunidade criados (G0-A)?** **SIM.** 7 campos criados em 2026-07-07 (Elite Score `OKX1hfCHkn2FWZud9lj1`, Breakdown, Sentimento, Quote Sent, Quote Link, Touchpoints, Next Action) — respostas 201, verificados por GET. IDs em `out/opportunity_customfields.json`.

**3. Houve ESCRITA no GHL? Quais (write_log)?** **SIM — 1.462 escritas reais, todas gateadas e logadas:**
- G0-B: **920** (score/breakdown nos 330 leads 40d + extensão em curso p/ ativos)
- G1: **501** (203 movimentações de pipeline + 298 tags `migrated-from-elite-ads`/`dup-elite-ads`)
- G0-A: **7** (criação dos custom fields)
- Autorização direta no chat: **2** (criação do stage HOT LEADS)
- CAPI (Meta, não-GHL): **32** eventos
- **Dry-run: 1** intenção pós-call registrada (inbound→HOT LEADS) — nenhuma escrita automática de cérebro executada (G2 pendente)

**4. Pipeline de transcrição rodando?** **SIM.** Deepgram nova-2 diarizado (testado com call real, idioma auto) + análise Claude Sonnet 5 com JSON estruturado (testada: call da Melissa — veículo/momento/intenção/preços/advice extraídos). Roda a cada ciclo de 5min na nuvem para calls novas >20s atendidas. Volume real processado até agora: ~2 calls (operação começou hoje à noite).

**5. O que falta do Rafael?**
- ~~Escopos/token/chaves~~ ✅ tudo entregue (GHL full, Deepgram, Anthropic, Supabase, Meta, GitHub, Vercel)
- **Aprovar G2** quando eu apresentar a demo (~5 calls reais analisadas com "o que o robô teria feito")
- Subir os 2 CSVs no Meta Audiences (estão no Desktop)
- Ver a aba **Diagnostics** do Events Manager (badge vermelho) e me dizer o que aparece
- Trocar as senhas do painel (as temporárias estão no chat)
- Responder: confirmação do trigger do workflow "2.1 GREAT CARS" (é stage-changed?)

## Próximos 3 passos (minha visão)
1. **G2 demo → ligar as escritas do cérebro** (stages, tasks, alertas de missed call, nice-to-talk) — é o que transforma o painel de "lista inteligente" em "operação automática". Materializa também A4 (comissões) e o avanço de cadência.
2. **M4 — relatório de fim de dia 18:30** (Eugene + Rafael) — fecha o loop de accountability do trial do Eugene.
3. **M5 — fila fria ranqueada** (2.066 legado + 873 Lost) — dá volume infinito de trabalho pro time nos vales entre leads novos.
