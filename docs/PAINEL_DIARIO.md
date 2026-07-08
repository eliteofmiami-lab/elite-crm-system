# PAINEL DIÁRIO — espelho e controle do dia (MISSÃO FINAL — substitui todas as anteriores)

## Princípio (inegociável)

O painel **ESPELHA** o GHL. Não cria dados, não analisa conteúdo, não lê chamadas, não usa IA, não escreve nada no GHL. Zero Deepgram, zero API de análise, zero batch — **desligar e manter desligado tudo isso**. Fonte única: eventos e metadados do GHL (calls: direção/atendida/duração · mensagens: direção/timestamp/texto para string-match de link · stages · tasks · appointments · campos de formulário já existentes). Polling de leitura a cada 2–5 min. Custo marginal ~zero.

**UI 100% em INGLÊS** — Board e aba do dono (rotulada "Owner"), todos os textos, alertas, pendências e labels. Vive **dentro do GHL** via Custom Menu Link (página completa, não rail). Inclui **clock in / clock out** (quadro só libera após clock-in) e **inatividade**: 10 min sem evento → banner amarelo · 15 min → alerta forte no painel (visual + som) · 20 min → bloco registrado. Pausas declaradas não contam.

## O quadro — 6 colunas (espelho puro, sem fila de prioridade; ordem interna: mais antigo primeiro)

1. **Retornar / Responder / Hot** — inbound perdida sem retorno · conversa cuja última mensagem é do lead · leads no stage HOT LEADS
2. **New Leads — Call ASAP** — opps no stage New Lead
3. **Tasks & Quote follow-ups** — tasks do GHL de hoje/atrasadas · leads que receberam link do Urable (string-match `go.urable.com` em SMS outbound) há N dias sem resposta
4. **Follow-ups do pipeline** — espelho dos stages Contact 1/2 (AM/PM) e Follow Up
5. **Appointments — próximos 2 dias** — dois grupos na mesma coluna: **A confirmar** (cards de ação, fecham com SMS de confirmação OU status confirmed) e **✓ Confirmados — quem está vindo** (cards informativos, sem ação): horário, nome, veículo, interesse e a **última nota do contato na íntegra/trecho** (é ali que os preços falados aparecem — espelho do que foi registrado; sem nota = o card exibe "no notes yet", expondo o registro faltante). Visível para Eugene E Rafael (mesma coluna no board; o Controle tem a lista resumida). Dados atualizam a cada ciclo de leitura.
6. **Warm up** — ração diária (default 20, config) de: Lost com motivo recuperável + stages parados há 30+ dias (config)

Card mínimo: nome · veículo/interesse (campos existentes) · de onde nasceu (evento + data) · idade do card · telefone · abrir contato (botão "Open" — a página já vive dentro do GHL). **Nenhum botão executa nada.** O board do Eugene NÃO tem botão de feedback.

## A REGRA DA RESOLUÇÃO (o coração do tracking)

**Discagem não fecha card. Resolução fecha — para TODA coluna com ligação (New Leads, Hot, Follow-ups, Tasks, Warm up), SEM EXCEÇÃO.** Exatamente como já é no GHL: a call termina e a pergunta é respondida com uma ação registrada. A árvore:
- **Não atendeu** → stage avançado (a cadência de mensagens dispara) — detecção: call não atendida + mudança de stage. *(Warm up/Lost, que não têm cadência: resolução = SMS de reativação enviado após a tentativa, OU marcado Lost terminal.)*
- **Atendeu** → UMA das quatro, detectada por leitura:
  · **Fechou appointment** → appointment criado no calendário
  · **Marcou follow-up** → task criada com data
  · **Pediu estimate** → link do Urable enviado + stage → Quote Sent
  · **Não interessado** → oportunidade fechada como **Lost com o motivo**
- O card exibe essa árvore como texto fixo (as resoluções válidas do seu tipo) — o Eugene sempre sabe o que encerra o card. Atualizar o perfil (interesse, veículo, dados) continua obrigação de registro no GHL, mas quem FECHA o card é o desfecho.

**O ÚNICO ALERTA DO SISTEMA:** call finalizada há mais de 15 min (config) **sem resolução detectada** → o card fica **vermelho "SEM RESOLUÇÃO"** e entra no contador do dia. Persiste até a resolução aparecer na leitura. Sem coach, sem sugestão, sem texto além de: *"Call de [hora] com [nome] sem resolução — mova o stage, crie o follow-up, envie o estimate ou marque Lost."*

Outras resoluções: card de SMS fecha com resposta enviada · confirmação de appointment fecha com SMS de confirmação enviado OU status confirmed no GHL (config: qualquer um).

Card não resolvido no dia **carrega** para o dia seguinte com a idade visível.

## Atribuição por usuário — as metas do Eugene são DELE (o Rafael também trabalha o quadro)

Todo evento lido do GHL é atribuído pelo `userId` (config: `eugene_user_id`, `rafael_user_id`; demais = "other/automation"). Regras:
- **Cards fecham com resolução de QUALQUER usuário** — o Rafael trabalha pelo que julga mais importante, o Eugene pela sequência; o quadro reflete o estado real do trabalho, feito por quem for.
- **Métricas do Eugene contam SÓ eventos dele:** tentativas válidas (call DELE ≥25s + SMS enviado POR ELE em 10 min — **SMS de workflow/automação NUNCA conta**), resoluções registradas, comissões (appointment criado POR ELE → Win), vendas da escada 30/35/40.
- **SEM RESOLUÇÃO é por autor da call:** a faixa vermelha do board do Eugene mostra só as calls DELE; calls do Rafael sem resolução aparecem apenas na aba Owner, rotuladas "by Rafael", e **não afetam o dia limpo do Eugene**.
- **Dia limpo do Eugene** = 100 válidas DELE + zero sem-resolução DELE + confirmações do quadro feitas (por qualquer um — estado do quadro) + tasks ATRIBUÍDAS A ELE com vencimento hoje concluídas.
- **Aba Owner ganha a linha de atividade por usuário:** hoje — Eugene (calls/SMS/resoluções) vs. Rafael vs. automação.

## Card verde — ganhos do Eugene (no topo do board)

- **Comissões e metas (estrutura completa, sempre visível no card):**
  · **$10 por venda** = appointment ELEGÍVEL ao Eugene cuja oportunidade vira **Win**. **Elegibilidade (casos definidos pelo Rafael — comissão segue o TRABALHO ATIVO):**
    | Quem agendou | Como confirmou | Comissão? |
    |---|---|---|
    | Eugene | Automação (cliente respondeu o texto) | **SIM** — criar é o trabalho |
    | Eugene | Eugene ligou para confirmar | **SIM** |
    | Rafael | Automação confirmou sozinha | **NÃO** |
    | Rafael (walk-in incluído) | Eugene não tocou no appointment | **NÃO** |
    | Rafael | Cliente não respondeu a automação e **Eugene ligou/confirmou ativamente** | **SIM** — o pastoreio salvou o appointment |
    Detecção determinística: `created_by = Eugene` → elegível direto. `created_by ≠ Eugene` → elegível SOMENTE se houver confirmação ATIVA dele na janela (48h, config): call outbound DELE atendida ou SMS manual DELE ao contato, **antes de qualquer confirmação já registrada** (se a automação já tinha confirmado, toque posterior não conta). Booking online (cliente se agendou pelo link) segue a mesma lógica de "não criado por ele": só ganha com confirmação ativa. **Cada comissão guarda o motivo** ("created by Eugene Jul 5" / "active confirmation by Eugene Jul 8 — no auto-reply") — visível no Owner para auditoria; teste-interno nunca conta. **Layout do card: GRID de 5 colunas iguais (mesma altura), enxuto — Calls today · Sales goal · Your wins · Potential · Clean-board bonus — cada uma com rótulo + número grande + UMA linha de contexto; barras em largura total da coluna. Rodapé separado por tracejado: à esquerda a nota consolidada (escada 30/35/40 em $ + definição de clean day), à direita o "Max this month" com o status do dia.** O funil vive em duas seções de mesmo peso: **"Your wins · July" (booked → confirmed → closed-won = $ earned)** e **"Potential" ($ em número grande, verde — "keep tracking it: booked & done, waiting for confirmation & sale close")** — e, EM DESTAQUE (âmbar) dentro do Potential, o **"to confirm" dos próximos 2 dias com o aviso do vínculo com o bônus**: "unconfirmed at clock-out = clean day lost = fortnight bonus at risk". O potencial nunca sai do board de metas — é o dinheiro que ele enxerga pendurado nas confirmações. Tudo por leitura, zero IA.
  · **Escada de metas — 3 tiers: 30 · 35 · 40 vendas.** Regra simples de monitorar: **$10/venda até a 30ª · $20/venda da 31ª à 40ª** → 30 = $300 · 35 = $400 · 40 = $500.
  · **Bônus de quadro limpo: $50/quinzena** (tudo-ou-nada) = até $100/mês.
  · **Teto mensal de incentivos: $600** — exibido no card ("Max this month: $600 = $500 sales + $100 clean-board").
  · Card mostra: barra de vendas do mês (x/40) com marcadores nos 3 tiers (30/35/40), ganho confirmado + potencial, e a régua de pagamento escrita.
- **Meta de volume — 100 ligações válidas/dia (config), em destaque no card verde com barra de progresso.** **Tentativa VÁLIDA** (determinístico, sem IA): call DO EUGENE atendida · OU call dele não atendida com duração ≥ 25s (proxy de voicemail, config) **+ SMS enviado POR ELE ao mesmo contato em até 10 min** (config; SMS de workflow não conta). Tocar-e-desligar não conta. O Controle exibe discagens brutas vs. válidas (a diferença expõe tentativa falsa); auditoria humana: Rafael ouve gravações aleatórias no GHL quando quiser. **Lembrete de ritmo:** checkpoint no meio do dia (13:00, config) — se abaixo do ritmo esperado, banner âmbar no painel (visual + som): "34/100 — behind pace. Hit the queue and warm-up list."
- **Warm up com reabastecimento:** ração mínima de 20/dia; se o quadro do dia esvaziar antes da meta de 100 ser atingível, o Warm up libera automaticamente mais leads da fila de resgate até a meta caber no dia. A fila nunca deixa o Eugene sem quem ligar.
- **Bônus de quadro limpo:** **dia limpo** = clock-out com (a) **100 tentativas válidas**, (b) zero calls sem resolução abertas, (c) confirmações do dia feitas, (d) tasks com vencimento hoje concluídas. **Regra do bônus (definida): $50 por quinzena (1–15 e 16–fim) se TODOS os dias de turno foram limpos.** Um dia não-limpo = bônus da quinzena perdido; o contador reinicia na quinzena seguinte — e o card passa a exibir "bonus lost — restarts on the [16th/1st]" para manter o alvo vivo. O card mostra: estado do bônus (on track / lost, com dias limpos ex. 6/6), status do dia ao vivo ("on track — 1 to resolve") e comissões do mês (confirmadas + potenciais).
- Visão do Rafael (Controle) espelha: confirmadas/potenciais/expiradas + dias limpos da quinzena.

## Feedback do beta — SÓ na aba Owner (Rafael)

Card "Beta feedback" exclusivo da aba Owner: campo de referência (lead/card) + texto livre + Send. O Eugene relata problemas ao Rafael; o Rafael registra. Grava em `beta_feedback` (referência, texto, timestamp, snapshot do card quando a referência bater) → consolidação diária em `BETA_FEEDBACK.md` — matéria-prima das rodadas de correção. Nenhum feedback altera nada automaticamente.

## Visão do Rafael (controle — uma aba)

Por coluna: criados hoje · resolvidos hoje · abertos (com idade) · **lista dos SEM RESOLUÇÃO** · cards com 2+ dias · **espelho dos appointments dos próximos 2 dias — confirmados E a confirmar, cada um com a última nota do contato** · clock in/out e blocos de inatividade do Eugene · ganhos do Eugene (vendas x/40, comissões, bônus) · card Beta feedback (exclusivo do Owner). Contadores e listas — sem relatório elaborado, sem análise.

## Aceite (teste ao vivo com lead teste-interno)

- Inbound perdida gera card na coluna 1 em ≤ 5 min · call finalizada sem ação vira "SEM RESOLUÇÃO" vermelho em 15 min · criar a task/mover o stage/enviar o SMS fecha o card sozinho no ciclo seguinte · appointment de amanhã sem confirmação aparece na coluna 5 · clock-in libera o quadro · leads Win/pós-venda/teste-interno não geram cards (exceto o teste durante o aceite)
- Confirmação de zero chamadas a APIs de IA/transcrição no período + custo do dia no cost_log (~$0)

Entregar: painel no ar + instruções do Custom Menu Link para o Rafael + `PAINEL_PRONTO.md` com screenshot textual das colunas populadas com dados reais. Depois: parar.
