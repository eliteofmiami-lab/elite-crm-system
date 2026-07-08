# MISSÃO FASE 1: Construção do Sistema Elite — Cérebro + Painel + Relatórios

## Contexto

A Fase 0 (recon + backfill) está concluída. Os achados estão em `RECON_REPORT.md`, `GAPS_E_RECOMENDACOES.md`, `leads_score.csv` e `out/*.json` — **leia todos antes de começar**. Agora vamos construir o sistema completo em cima da estrutura real levantada.

**Decisões tomadas pelo Rafael:**
1. **Pipeline oficial = New Pipeline** (`oUL5N3vxYqL13sBLrZUF`). Do ELITE ADS, migrar os leads bons e depois deixá-lo inativo (arquivamento manual na UI depois).
2. **Nedzo AI está desativado** — ignore os workflows dele; nosso sistema assume a operação.
3. **Transcrição via API paga** — usar **Deepgram** (modelo nova, com diarização de speakers). Chave em `DEEPGRAM_API_KEY` no `.env`.

**Regras globais desta fase:**
- Toda operação de ESCRITA (GHL, Urable, Supabase é livre) só acontece após passar pelo **gate de aprovação** indicado em cada milestone: você gera um dry-run (CSV/relatório do que SERÁ feito), o Rafael aprova explicitamente, e só então executa.
- **NUNCA delete nada** no GHL ou Urable. Sem exceções.
- Registre toda escrita em `out/write_log.jsonl` (timestamp, endpoint, id, payload resumido) — é nossa trilha de auditoria e rollback.
- Segredos só no `.env` (gitignored). Nunca em logs, commits ou saídas.
- Commits pequenos e frequentes. Estruture o repo em: `worker/` (cérebro Python), `web/` (painel Next.js), `docs/`, `out/`.

## Pré-requisitos (pedir ao Rafael antes de executar o que depender deles)

Gere um arquivo `INSTRUCOES_RAFAEL.md` consolidando o que ele precisa fazer na UI/contas, incluindo:
1. **Ampliar scopes da Private Integration** no GHL para incluir escrita: Contacts (write), Opportunities (write), Conversations/Messages (write — envio de SMS), Notes (write), Tasks (write), Custom Fields (write), Tags (write). Manter os de leitura já existentes.
2. **Criar conta Deepgram** e colocar `DEEPGRAM_API_KEY` no `.env`. Preencher também `ANTHROPIC_API_KEY`.
3. **Supabase**: criar projeto `elite-crm` e colocar `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` no `.env` (mesmo fluxo do Portal de Vagas).
4. **Vercel + GitHub**: repo privado `elite-crm-system`, deploy do `web/` na Vercel, secrets do GitHub Actions espelhando o `.env`.
5. **Telefone do Eugene** para os nudges por SMS (vira configuração no painel).
6. Tarefas de UI no GHL que a API não cobre (você vai gerar instruções passo a passo): branch de horário no workflow de primeiro SMS (mensagem fora de horário/fim de semana), verificação de que mover pro stage `Great Cars` dispara o workflow `2.1: GREAT CARS - ADS` (CAPI/Meta), confirmação de qual stage dispara o drip de remarketing, e desativação dos calendários obsoletos (manter: `Booking Request`, `ELITE BOCA RATON`, `Ceramic Pro Silver Package`).

## MILESTONE 0 — Fundações de dados e score v2

**0.1 Custom fields de oportunidade (GATE G0-A):** proponha e, após aprovação, crie via API os campos de oportunidade: `elite_score` (número), `elite_score_breakdown` (texto, ex. "car:35 mom:? eng:25 int:12"), `elite_sentimento` (texto), `elite_quote_sent` (bool), `elite_quote_link` (texto), `elite_touchpoints` (número), `elite_next_action` (texto). Liste antes de criar.

**0.2 Score v2 (recalcular os 330 + tudo que entrar):**
- Carro (0–35) e Engajamento (0–25): como na Fase 0, com um ajuste — **chamada inbound do lead = 25** no engajamento (mesmo peso de "pediu ligação").
- **Intenção (0–15) com proxy `how_soon`** enquanto não houver transcrição: "As soon as possible" = 15 · "Within the next 2 weeks" = 12 · "Within the next month" = 8 · "Not sure / just exploring" = 3 · vazio = `?`. Quando a transcrição existir, o valor derivado da call SOBRESCREVE o proxy.
- Momento (0–25): segue o modelo (recém-entregue 25 / <3m 20 / >3m 15 / >6m 10 / >1a 5), preenchido só por transcrição/nota. `?` até lá.
- Score exibido sempre como `conhecido/máximo_possível` + breakdown.

**0.3 Write-back (GATE G0-B):** dry-run com 20 exemplos (CSV: lead → o que será gravado onde). Após aprovação, gravar score nos custom fields de oportunidade de todos os leads dos 40 dias.

## MILESTONE 1 — Migração ELITE ADS → New Pipeline

**Critérios de "lead bom" a migrar** (proponha ajustes se os dados sugerirem): score de carro = 35, OU engajamento ≥ 15, OU stage em (`GREAT CARS`, `NEW LEADS-CALL ASAP`, `HOT LEADS`, `FOLLOW UP-CHECK LEAD`, `Day1/2/3 *`), OU appointment nos últimos 90 dias. Os demais (ex.: `NEVER ANSWERED-REMARKETING` 698, `NOT INTERESTED` 740) **não migram** — permanecem no legado e entram na base de cold calls por referência (M5).

**Mapeamento de stages** (proponha a tabela completa; base): `GREAT CARS→Great Cars`, `NEW LEADS-CALL ASAP→New Lead`, `HOT LEADS→Follow Up`, `Day1 No Answer1→Contact 1 (AM)` (e análogos), `APPOINTMENT BOOKED→Appointment Booked`.

**Dedupe:** os 17 telefones presentes nos dois pipelines — manter a opp do New Pipeline, tagear a do legado com `dup-elite-ads` (não mover, não deletar).

**GATE G1:** gerar `migration_dryrun.csv` completo (opp → stage destino, motivo). Rafael aprova → executar movendo `pipelineId`/`pipelineStageId` via API + tag `migrated-from-elite-ads` → relatório pós-migração com contagens.

## MILESTONE 2 — O Cérebro (worker pós-chamada)

Worker Python em `worker/`, rodando via **GitHub Actions a cada 5 minutos, seg–sáb, 8am–7pm ET** (+ um job de fim de dia às 6:30pm ET para relatórios). Estado (última call processada, cards, shifts) no Supabase.

**2.1 Ingestão:** varrer conversas com mensagens novas desde o último ciclo. Para cada `TYPE_CALL` nova: baixar gravação (`GET /conversations/messages/{messageId}/locations/{locationId}/recording`), transcrever no Deepgram (diarização ligada, idioma auto en/es/pt), salvar transcript no Supabase.

**2.2 Análise com Claude** (API Anthropic, modelo Sonnet): para cada transcript, extrair JSON estruturado:
```
{ vehicle: {make, model, year, is_new_or_just_bought, delivery_date_or_window},
  momento: {faixa, evidencia},          // → score 25/20/15/10/5
  intencao: {nivel, evidencia},          // → 15/10/5
  sentimento: {geral, reacao_preco: "achou_caro|ok|achou_barato|nao_discutido",
               comparou_concorrente: bool, detalhes},
  motivacao_principal, gancho_pessoal,   // ex.: "aniversário da filha, volta quarta"
  precos_falados: [{servico, escopo, valor}],
  script_coverage: {perguntou_carro_novo, perguntou_garagem, perguntou_keep_or_trade,
                    perguntou_outros_orcamentos, apresentou_ballpark},
  voicemail_left: bool,                  // se call não atendida: deixou voicemail?
  resultado: "atendida|nao_atendida|voicemail",
  proxima_acao: {tipo: "follow_up|enviar_quote|agendar|transferir_rafael|descartar",
                 data_sugerida, motivo},
  resumo_3_linhas, coaching: "o que poderia ter sido melhor nesta call" }
```

**2.3 Escritas automáticas pós-call (autorizadas de forma permanente após GATE G2 — demonstre com 5 calls reais antes):**
- Atualizar custom fields do contato (veículo se faltar, etc.) e da oportunidade (score recalculado, sentimento, next_action).
- Criar **nota estruturada** no contato (resumo, preços falados, gancho pessoal, score breakdown).
- Criar **task** quando `proxima_acao` tiver data (título curto + motivo humano), atribuída ao Eugene.
- **Avanço de cadência no-answer:** call não atendida → avançar a opp para o próximo stage da cadência existente (`New Lead/Contact 1 (AM) → Contact 1 (PM) → Contact 2 (AM) → ... → Follow Up`), o que dispara os SMS automáticos já configurados. Nunca retroceder stage. Incrementar `elite_touchpoints`.
- **Great cars:** lead novo com carro exótico/premium/2026 → tag `great-car` + mover para stage `Great Cars` (dispara o workflow CAPI existente — confirmar com Rafael na UI, ver INSTRUCOES_RAFAEL).
- **Reaquecimento:** `elite_touchpoints` ≥ 5 sem NENHUMA resposta do lead (≥ 8 se score ≥ 80) → mover para `Lost` + tag `reaquecimento` (drip semanal existente — confirmar trigger com Rafael).
- **Detecção de quote:** SMS outbound com link `go.urable.com/*` → gravar link em `elite_quote_link` + nota + `elite_quote_sent=true` + mover opp para `Quote Sent` + fechar o card correspondente.
- **Inbound:** call inbound de número novo → criar card "New Lead — Inbound" (engajamento 25); inbound perdida → card urgente de callback.
- **Voicemail:** call não atendida com `voicemail_left=false` → registrar falha da regra no relatório do dia.

**2.4 Preparação de quote:** quando `proxima_acao=enviar_quote` → criar/atualizar **Customer + Item (veículo)** no Urable via API (GATE G2-U na primeira vez) → criar card de quote no painel com: dados do cliente, serviço/escopo, valores exatos falados, prazo, e rascunho da mensagem de envio.

**2.5 Nice-to-talk-to-you:** gerar rascunho personalizado (com base no gancho pessoal e no que foi discutido) → card de aprovação no painel → Eugene revisa/edita → clique envia via API do GHL (SMS outbound como Eugene).

## MILESTONE 3 — O Painel (web/, Next.js + Supabase + Vercel)

Auth Supabase com 2 usuários (Eugene = operador, Rafael = owner; RLS por papel). Layout mobile-friendly. Duas abas:

**Aba 1 — FILA (a esteira, tela default):**
- Card do topo = próxima ação, recalculada a cada evento. Prioridade: **Camada 1 (interrupções):** lead novo (speed to lead) > respondeu SMS/pediu ligação > inbound perdida > score 80+ chegando em 24h sem contato. **Camada 2 (dia planejado):** tasks de hoje na hora marcada > confirmações de appointment (bloco até 11am) > quotes pendentes. **Camada 3 (cold calls ranqueadas):** quando 1 e 2 estiverem limpas.
- Cada card: O QUÊ (ação) / POR QUÊ (contexto + score + gancho) / COMO (coaching por tipo: script de pré-qualificação com as frases para New Lead; resumo da conversa anterior para Follow-up; preços + sentimento + política de desconto para Quote Sent) / AÇÃO (botão deep-link `https://app.gohighlevel.com/v2/location/{loc}/contacts/detail/{id}`).
- **Fechamento automático por evidência:** o worker detecta o evento (call outbound pro número, SMS enviado, link Urable, appointment criado) e fecha o card com o resultado. Card de call não atendida vira retry automático (mesmo dia, outro horário). Sem botão "marcar feito" — exceção única: card de quote pode ter confirmação manual com verificação cruzada do link.
- **Clock in/out + pausas:** fila só libera após clock-in. Pausas declaradas (config: almoço + 2 pausas) não contam como inatividade.
- **Nudges:** 10 min sem evento → banner amarelo ("X leads esperando na fila") · 15 min → vermelho + SMS pro Eugene via GHL · 20 min → bloco de inatividade registrado (Supabase) e exibido nos relatórios.

**Aba 2 — PLACAR & INSIGHTS:**
- Hoje: calls, SMS, quotes enviadas, appointments booked, transferências (heurística: calls encadeadas no mesmo contato com `userId` diferente em <30 min), tempo médio de resposta a lead novo, funil do dia.
- Recomendações de coaching (dos análises 2.2) e alertas (voicemail não deixado, quote não enviada no dia, score 80+ órfão).
- Visão do Rafael (a mais): metas auditadas do dia, blocos de inatividade, timeline de atividade, histórico.

## MILESTONE 4 — Relatórios diários

Job de fim de dia (6:30pm ET) gera e salva no Supabase (exibidos no painel; export .md no repo):
- **Relatório Eugene:** o que ficou pendente e por quê, tasks de amanhã, appointments dos próximos 2 dias a confirmar, 3 coachings principais do dia.
- **Relatório Rafael:** funil do dia (leads → contatados → qualificados → quotes → appointments → win), auditoria das 6 metas binárias (speed to lead 15min, resposta 30min, voicemail 100%, quote no dia, confirmações até 11am, zero 80+ órfão), calls com análise/coaching por chamada, atividade e inatividade, transferências e o que aconteceu depois delas.

## MILESTONE 5 — Cold calls ranqueadas (Camada 3)

Popular a fila fria com: `Lost` do New Pipeline (873), no-shows (15+), quotes sem resposta, e os stages não migrados do legado (`HOT LEADS`, `NEVER ANSWERED-REMARKETING` — por referência ao contato, sem mover nada). Ranking = score_original × fator de recência × ponto onde a conversa morreu (no-show > quote sem resposta > respondeu e sumiu > nunca respondeu). Refresh semanal + reentrada imediata na fila ativa se o lead responder qualquer coisa.

## Ordem de execução e aceite

M0 → M1 → M2 → M3 → M4 → M5, com gates. Cada milestone termina com: demo/relatório do que foi feito, testes básicos, e commit. Se algo da API se comportar diferente do documentado no RECON_REPORT, pare e reporte antes de contornar. Ao final, gere `SISTEMA_OVERVIEW.md` explicando a arquitetura para leigos (o Rafael não é técnico).

---

## ADENDO A — Ajustes definidos após a entrega inicial

**A1. Stage HOT LEADS (inbound) no New Pipeline.** O Rafael vai criar o stage `HOT LEADS` na UI (logo após `Great Cars`) ANTES da migração do M1. Ajustes decorrentes:
- **Mapeamento do M1 atualizado:** `HOT LEADS (legado) → HOT LEADS (New Pipeline)` em vez de Follow Up.
- **Regra do cérebro (M2):** toda call inbound → mover a opp para `HOT LEADS` (criar opp se não existir; o workflow "Create opportunity via incoming Phone call" pode já criar — verificar e complementar, sem duplicar). EXCEÇÃO anti-regressão: se a opp já está em `Quote Sent`, `Appointment Booked` ou `Win`, NÃO mover — apenas registrar a call, criar o card e atualizar score.
- Não iniciar o M1 até o stage existir (verifique via API antes do dry-run).

**A2. Rastreio do número Google Ads em inbound.** Cada `TYPE_CALL` traz o número discado (`to`). Tarefa: inferir o número de tracking do Google Ads analisando as calls dos 34 leads com source "Call Google Ads" da recon → apresentar ao Rafael para confirmação → fixar como config. Regra do cérebro: inbound com `to` = número Google Ads → tag `inbound-google-ads` + corrigir source da opp. Registrar origem no card e nos relatórios (inbound Google Ads vs. outros).

**A3. Auditoria de SMS por stage (tarefa imediata, somente leitura — pode rodar em paralelo aos milestones).** Reconstruir empiricamente a cadência dos DOIS pipelines a partir das mensagens realmente enviadas nos últimos 40 dias (ampliar janela se o volume for baixo): agrupar SMS outbound por template (normalizar corpos quase idênticos — remover nome/veículo/links antes de comparar), associar cada template ao stage da opp no momento do envio (usar `lastStageChangeAt`/histórico disponível; quando ambíguo, marcar como incerto), e calcular por template: volume, taxa de resposta (inbound do lead em até 48h), taxa de opt-out/negativa. Entregável: `SMS_CADENCE_AUDIT.md` com a cadência mapeada por pipeline/stage, ranking de performance dos templates e recomendações do que manter/reescrever. NÃO alterar nenhuma mensagem — a revisão de copy será feita pelo Rafael.

**A4. Comissão do Eugene — $10 por appointment que vira venda (painel M3 + relatórios M4).**
- Evento "appointment booked" atribuível ao Eugene (appointment criado em lead trabalhado por ele — v1: qualquer appointment criado após call/SMS dele no lead) → registrar `ganho_potencial = $10` com referência ao appointment e ao lead.
- Quando a opp do lead chegar a `Win` (ou invoice do Urable detectada) → converter em `ganho_confirmado`.
- No-show sem reagendamento ou opp em `Lost` → potencial expira (status `expirado`, mantido no histórico).
- **Painel (aba Placar):** widget de ganhos — hoje e mês corrente: potencial / aguardando desfecho / confirmado, com lista dos appointments e status de cada um.
- **Relatórios diários:** linha de ganhos no relatório do Eugene ("hoje você gerou $X potenciais; $Y confirmados este mês") e no do Rafael (total a pagar no mês, conciliável com as vendas na Fase 2).
- Tabela `commissions` no Supabase com trilha completa (appointment_id, lead, data, status, transições).

**A5. Bônus quinzenal de disciplina — $50 (painel M3 + relatórios M4 + fechamento).**
- Períodos: dia 1–15 e dia 16–fim do mês. A cada período, se o Eugene fechar SEM NENHUMA falha grave, `bonus_quinzena = $50` é adicionado ao resumo de pagamento (comissões + bônus).
- **Falha grave (config `critical_misses`, valores default — Rafael confirmará antes do M4):** (a) lead novo em horário comercial sem NENHUMA tentativa de contato no mesmo dia; (b) quote com preço discutido em call não enviada até o fim do dia útil seguinte; (c) appointment dos próximos 2 dias sem confirmação; (d) lead score 80+ órfão por mais de 24h (sem contato E sem task datada); (e) bloco de inatividade > 45 min sem pausa declarada nem justificativa; (f) 3+ adiamentos com motivo rejeitado pelo sistema no período.
- Falhas MENORES (speed-to-lead estourado pontual, voicemail esquecido isolado) NÃO derrubam o bônus — continuam nas metas diárias e no coaching, mas o bônus só cai com falha grave.
- **Painel Eugene:** no cartão de comissões, status do bônus em tempo real: "on track — X/14 dias, 0 falhas graves" ou "lost this period — [motivo, data]". Se perder, mostra quando o próximo período começa (recomeço limpo).
- **Painel Rafael:** mesma linha de status no card de comissão; falha grave gera item vermelho nos alertas no dia em que ocorre (nunca surpresa no fechamento).
- **Fechamento da quinzena (job do dia 15 e do último dia):** resumo de pagamento no relatório do Rafael: comissões confirmadas do período + bônus (sim/não + motivo) = total a pagar. Registrar em tabela `payouts` no Supabase com trilha completa.

**A5.1 Bonus guard — o sistema protege o bônus, não só audita.** Terminologia voltada ao usuário: usar sempre "Advice"/"Alert"/"Atenção"/"Reporte" — NUNCA "coaching". Lembretes proativos pré-falha-grave, gerados pelo worker e exibidos no painel do Eugene (linha "Bonus guard" no cartão de comissões + interrupção Camada 1 quando urgente) e opcionalmente por SMS: (a) quote com preço discutido e não enviada → lembrete 15:00, card urgente 16:30; (b) appointment de amanhã sem confirmação → lembrete 10:15; (c) lead 80+ a 4h do limite de 24h órfão → card urgente; (d) inatividade já coberta pela escala 10/15/20. Estado "all clear" em verde quando nada ameaça o bônus. Todos os lembretes e seus desfechos são registrados (tabela `bonus_guard_events`) e aparecem no relatório do Rafael.

**A6. Advice compartilhado e bilíngue (Eugene + Rafael).** O JSON da análise (M2, item 2.2) passa a gerar `advice_en` e `advice_pt` — o mesmo insight nos dois idiomas, na mesma chamada à API. Surfacing em 4 pontos: (1) vista do Eugene, card "Advice from today's calls" em tempo real, cada item com deep-link para o lead; (2) vista do Rafael, feed "Alertas e recomendações" com a tag `Advice`; (3) injeção do advice mais recente daquele lead na seção "How to play it" do próximo card dele (insight vira ação); (4) top 3 do dia nos dois relatórios. Regra explícita na UI e no código: advice NUNCA entra no cálculo de metas, falhas graves ou bônus.

**A7. Prioridade de New Leads parados + formulário de pré-qualificação + modo de teste.**
(1) **Fila:** lead em `New Lead`/`HOT LEADS` sem nenhuma tentativa de contato (qualquer idade) → topo da Camada 2, acima de follow-ups agendados, ordenado por score desc e recência; Camada 1 inalterada (recém-chegado, SLA 15 min).
(2) **Log call details:** formulário no card expandido com os campos do script de pré-qualificação (veículo, novo/recém-comprado nas faixas do Momento, chegada do carro, garaged/street, keep/trade, outros orçamentos, motivação, ballpark, próximo passo + data). Save = write-through imediato nos custom fields do contato + nota estruturada. Reconciliação: entrada manual do Eugene VENCE; o cérebro (pós-G2) apenas completa vazios e registra divergências como nota — nunca sobrescreve. Antes do G2, o formulário é o único caminho de escrita pós-call.
(3) **Modo de teste:** tag `teste-interno` exclui o contato de score write-back, eventos CAPI/Meta, relatórios, comissões e bônus — mas ele aparece na fila e no pipeline normalmente, permitindo teste ponta a ponta. Documentar no Diagnostics como criar/limpar leads de teste.

**A7.1 Refinamentos do Log call details.** (a) Campos de conversa exibem a frase sugerida de abordagem (as do playbook) como hint sob o rótulo. (b) `keep_or_trade` é enum fixo: Leasing · Trade in 2–3 years · Keeping for about 5 years · Keeping for more than 5 years — "Leasing" deve alimentar o advice com o ângulo de PPF contra taxas de devolução de lease. (c) Next step = Not interested revela select de Lost reason sincronizado dos motivos de perda do GHL (buscar via API; fallback: lista em config copiada de Settings → Opportunities → Lost Reasons). Ao salvar: opp → Lost + motivo; motivos recuperáveis (preço/timing) permanecem elegíveis para cold calls com o contexto; motivos terminais (comprou em outro lugar / vendeu o carro / spam / número errado) são excluídos das cold calls e do reaquecimento.

**A7.2 Wrap-up e frases integrais.** (a) Ciclo do card revisado: primeira call ATENDIDA de um lead → card entra em estado Wrap-up e só conclui quando o SMS "nice to talk to you" outbound é detectado no GHL (rascunho do cérebro pós-G2; template editável pré-G2, com nome/veículo/contexto). Calls atendidas seguintes do mesmo lead não exigem repetição. Wrap-ups pendentes reaparecem em "Needs your OK" e contam na meta de higiene do dia. (b) Hints do formulário com as frases INTEGRAIS do playbook; "Seen other quotes" com expansível "+ 2 more ways to ask" contendo a frase de defesa de valor e a de timeline (textos exatos no spec 8.2).

**A7.3 Preços por card + tabela fixa (fonte única).** Criar `prices.json` no repo com a matriz oficial (PPF, Ceramic, add-ons × Compact/Standard/Medium/Large) — única fonte de verdade, editável pelo Rafael. (1) Classificação de tamanho do veículo: tabela determinística make/model → tier (ex.: 911/sedans/coupes=Standard, Cayenne/Model Y=Medium, Escalade/Suburban/pickups=Large, compactos=Compact), fallback via Claude para modelos fora da tabela, override manual do Eugene no card (select) — cada override registrado realimenta a tabela. (2) Card: seção "Prices for this car" com as linhas do tier do veículo. (3) Price sheet recolhível sempre acessível com a matriz completa. (4) A validação já planejada (ballpark falado vs. tabela) e o preparo de quotes leem do mesmo prices.json.

**A7.4 Elegibilidade da fila — Win/Lost/delete.** Regra dura no gerador de cards e no worker: (1) opp em `Win` nunca gera card; lead que vira Win fecha automaticamente TODOS os cards abertos (resultado "won") e confirma a comissão do appointment vinculado; contato com opps duplicadas usa a mais avançada (Win em qualquer = fora da fila ativa). (2) `Lost` só participa da Camada 3 conforme ranking e motivo recuperável; `delete`/spam nunca. (3) AÇÃO IMEDIATA: auditar os cards atuais no ar contra o stage real de cada opp e expurgar os inelegíveis (o backfill da Fase 0 incluiu leads em Win no TOP_PRIORITIES — ex.: Karol, Naomi, Jose Rodrigues, Jason M.); reportar quantos foram removidos. (4) Backlog (não construir agora — Fase 2): monitoramento de reviews pós-Win, SEM envio automático. O sistema cruza os Wins recentes com os reviews novos do Google Business Profile (via API do GBP; matching por nome é heurístico — marcar como "provável") e apresenta ao Rafael a lista de clientes que provavelmente não escreveram, com botão de aprovação por cliente: "disparar solicitação no GHL?" — só envia com o clique do Rafael, usando template existente no GHL. Nunca automático. + métrica Wins → reviews no fechamento mensal.

**A8. Controle de custos do sistema.** (1) **Model routing:** Haiku 4.5 para tarefas leves (checagem de voicemail, validação de snooze, classificação de tamanho fallback, triagens); Sonnet 4.6 apenas para a análise completa de calls atendidas, relatórios e advice. (2) **Prompt caching** no system prompt fixo da análise (90% de desconto na parte cacheada). (3) **Batch API (50% off)** para tudo que não é tempo real: relatórios de fim de dia, ranking semanal de cold calls, reprocessamentos. (4) **Pular análise completa** de calls com menos de 20 segundos — registrar só o resultado (no-answer/voicemail) via metadados + Haiku. (5) **Telemetria de custo:** logar tokens e minutos por job em tabela `cost_log`; linha "Custo do sistema (mês)" no relatório mensal do Rafael; alerta no painel do Rafael se o custo projetado do mês passar do teto configurável (default $150). (6) Instruir o Rafael a ativar budget alerts nos consoles da Anthropic e do Deepgram.

**A9. Interesse de serviço vivo + preços por interesse + serviços custom-quote.** (1) Criar custom field `elite_interesse_atual` (contato): seed do campo de formulário existente (que fica preservado como origem); atualizado a cada call analisada (campo serviço/escopo do JSON) e pelo Log call details (entrada manual vence); manter trilha de mudanças em `interest_history` no Supabase. Todo card exibe "Looking for: {interesse_atual}" com a mudança mais recente. (2) Exibição de preços condicionada ao interesse: mostrar a(s) linha(s) do serviço de interesse no tier do carro; interesse indefinido → pergunta de abertura + Price sheet. (3) `prices.json` ganha `custom_quote_services` (inicial: color change PPF, vinyl wrap — editável pelo Rafael): para esses, nunca exibir preço de tabela — card mostra "Custom-quote service — priced per project" + instrução de checar a quote do Urable ou escalar ao Rafael. (4) Cards quote-sent: "How to play it" sempre derivado de dados reais (valores falados, sentimento, quote/link/data); na ausência de análise, declarar pendência honesta — nunca coaching genérico. Varrer os cards no ar e corrigir os que violam (a K WASHINGTON é o caso-teste: color change PPF + quote já enviada).

**A9.1 Vinyl wraps — classe starting_price e jogada de visita à loja.** prices.json passa a ter três classes: `tabela` (PPF/Ceramic/add-ons, valores fechados), `starting_price` (vinyl wraps: Compact 3000 · Standard 3500 · Medium/small SUV 3800 · Large/SUV 4000 — sempre exibido como "starting at" + "final price depends on the material selected") e `custom_quote` (color change PPF, até o Rafael definir preços). Para leads com interesse em wrap: (1) card mostra o starting price do tier + a jogada: convidar para a loja — ver materiais, preço final na hora, depósito trava o material e agenda a instalação; (2) a análise deve sugerir `proxima_acao = agendar_visita` (não enviar_quote) para wraps; (3) o advice reforça a estratégia ("não feche número final por telefone — feche a visita"). Validação de ballpark: para starting_price, falar ACIMA do starting do tier é ok (material melhor); falar ABAIXO gera alerta.

**A10. Filosofia "feche a visita" + extras fora do telefone + briefing pré-venda.** (1) REGRA UNIVERSAL: todo preço é starting price e todo card orienta fechar a VISITA à loja — o "How to play it" de qualquer tipo termina no convite/agendamento; venda final e upsell são presenciais (Rafael). (2) prices.json: lista `mention_only_if_asked` = [paint correction, interior/leather coating, wheels & calipers coating]; cards exibem add-ons rotulados "only if asked"; análise de script não penaliza não oferecer extras e registra observação se forem empurrados proativamente. (3) Color change PPF migra para classe `starting_price` com os valores do Full Body PPF por tier + nota "price varies by color" (custom_quote fica vazia, editável). (4) **Briefing pré-venda (visão Rafael, spec 6.5):** seção "Visitas de hoje e amanhã" com dossiê por appointment (interesse_atual, preços exatos falados com data, sentimento, ganchos, quote/link, sugestões de upsell por perfil), gerado das análises e atualizado a cada call nova; incluir versão no relatório das 18:30 (visitas de amanhã). Ajustar o prompt de análise: `proxima_acao` privilegia agendar_visita para qualquer lead engajado; quote no Urable continua existindo quando o cliente pede número por escrito, sempre apresentada como starting.

**A11. Perguntas técnicas — hierarquia, transferência e callback do master tech.** (1) Playbook v1.4 já define a regra e os scripts (seção 4.7): Eugene nunca improvisa resposta técnica; transfere ao vivo ou promete callback pessoal do Rafael no mesmo dia, posicionando a hierarquia como tratamento premium ("assistant → master technician/owner"). (2) Análise de call passa a extrair `pergunta_tecnica {houve, transferida, resposta_improvisada, pergunta}`. (3) Automação: pergunta técnica sem transferência ao vivo → criar TASK atribuída ao RAFAEL no GHL ("Callback técnico — {nome}: '{pergunta resumida}'" + link do contato + contexto da call), prazo mesmo-dia, exibida na visão do dono (alertas) e no relatório 18:30; a execução do callback é detectada (call outbound do Rafael pro contato) e fecha a task. (4) `resposta_improvisada=true` gera advice de lane para o Eugene ("essa pergunta era do master tech — na próxima, transfira") — nunca conta como falha grave. (5) Métrica no fechamento: perguntas técnicas/mês, % transferidas ao vivo, tempo médio do callback, conversão pós-contato técnico (hipótese: contato com o dono converte mais — validar com dados).

**A11.1 Calibragem da fronteira técnica (corrige o A11).** (1) Perguntas de marca/produto NÃO são técnicas — resposta é lane do Eugene (Ceramic Pro, certificação, garantia vitalícia, Carfax); idem pacotes, garantia básica, prazos, preços. Técnica = julgamento de especialista (pintura, instalação por painel, spec profundo, garantia caso-limite). (2) MODO OBSERVAÇÃO por 2 semanas: detecções de pergunta_tecnica são logadas e apresentadas ao Rafael em lista (pergunta, categoria sugerida, como o Eugene tratou) — sem advice de lane e sem task automática; EXCEÇÃO: se o Eugene prometeu callback na call, a task para o Rafael nasce normalmente (promessa a cliente não espera calibragem). (3) Após revisão do Rafael, a taxonomia aprovada vira config `technical_taxonomy` e o fluxo completo do A11 ativa. Princípio geral do sistema: classificações novas estreiam em observação antes de gerar ação ou coaching.

**A12. REGRA Nº 1 — qualidade de advice e integridade de score (correção urgente).**
(1) **Advice — portão de qualidade obrigatório.** Todo advice deve: (a) citar a evidência (trecho literal da transcrição em que se baseia — campo `evidencia` obrigatório); (b) mexer numa alavanca de CONVERSÃO (fechamento de visita, defesa de valor, timing, objeção, upsell contextual) — nunca higiene de processo; (c) ser não-redundante — PROIBIDO recomendar o que o sistema já automatiza (registrar telefone/dados, anotar, logar, mover stage, fazer follow-up que já vira task); (d) **silêncio é output válido**: `advice: null` com `motivo: "call bem conduzida"` — preferível a filler. LISTA BANIDA (rejeição automática): pedir dados que o caller ID/sistema já captura; "seja mais empático/confiante" e genéricos sem evidência; sugestões de CRM/processo; qualquer coisa não ancorada na transcrição. **Crítico automático:** segunda passada (Haiku) valida cada advice contra os 4 testes e a lista banida; reprovado = descartado e logado (`advice_rejected`) para auditoria. VARRER e apagar todos os advices já exibidos que violam a regra (o "grab his phone number" da K WASHINGTON é o caso-teste do que deve morrer).
(2) **Score — integridade e honestidade.** (a) DEBUG imediato do lead K WASHINGTON: gerar `SCORE_DEBUG.md` mostrando cada componente, de onde veio (ou por que está vazio) — pela descrição do Rafael esse lead é ~100 (inbound + carro chegando + quote + carro), exibir 35 é bug de integração; corrigir a causa raiz, não o caso. (b) EXIBIÇÃO HONESTA obrigatória (já no spec, não implementada): score sempre como `conhecido/máximo-apurável` + selo `call-verified` ou `partial` — nunca número seco quando componentes faltam. (c) **Novo sinal: VISITA À LOJA** — evento mais forte do funil; entra no modelo como marcador de intenção máxima (Intenção = 15 automático + flag `visitou_loja` destacada no card e no briefing). Registro no GHL: aguardando definição do Rafael (appointment com status showed OU tag `visitou-loja` — implementar leitura dos dois até definição). (d) Princípio: componente sem dado = `?` visível, JAMAIS zero silencioso.
