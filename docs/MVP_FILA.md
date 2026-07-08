# MVP — FILA DENTRO DO GHL (escopo enxuto e final até segunda ordem)

## Decisão do Rafael

Simplificar radicalmente. O sistema faz UMA coisa até provar que faz bem: **a fila de ligações dentro do GHL, ordenada pela análise completa de cada lead**. Todo o resto está CONGELADO (não deletar código — desativar, ocultar da UI e não executar): advice engine, rascunhos/aprovações de mensagem, wrap-up automático, bonus guard, motor de comissões, relatórios 18:30, Appointments Board, briefing, rastreio de cupom, estudo retro (ações), nudges/clock-in, extensão Chrome. Nada disso roda nem aparece.

## O que o MVP entrega (só isto)

**1. Síntese cronológica por lead (Regra Zero / A16)** — para todo lead elegível (A7.4: sem Win, sem delete/spam, sem pós-venda, sem teste-interno): linha do tempo completa (análises de call + SMS in/out + eventos: quotes, appointments, no-shows, inbound perdidas — incluindo de contatos existentes) → `estado_do_lead` com evidência datada: ativo_venda · aguardando_decisao_cliente(data) · aguardando_evento_externo(qual, janela) · agendado(data) · callback_devido · esfriou · pos_venda(inerte). **Evidência mais nova sobrescreve a antiga.**

**2. Score sobre o estado atual** — régua já validada (Carro 35 / Momento 25 / Engajamento 25 / Intenção 15, visita à loja = intenção máxima), componentes com data e fonte, exibição `conhecido/máximo` + selo call-verified/partial, `?` visível.

**3. A fila** — 3 camadas como definidas nas REGRAS DO MOTOR (§1–4): interrupções → dia planejado → cold ranqueadas. Estados governam presença: `aguardando_decisao_cliente` sai da discagem ativa (nurture mínimo, Camada 3 com estado explícito) · `agendado` só aparece na data · `aguardando_evento_externo` só na janela · `callback_devido` = topo da Camada 1 · `pos_venda` = invisível.

**4. Dentro do GHL** — modo `?layout=rail` (coluna única) servido via **Custom Menu Link** (gerar instruções passo a passo pro Rafael criar em Settings). Card SIMPLIFICADO: **quem ligar** (nome · veículo · interesse) · **por que ligar** (a narrativa do estado em 2 linhas, com datas) · **score x/y + selo** · telefone · botão "abrir contato" (link GHL). Botão **(i)** no score abre a CONTAGEM: cada componente com valor, fonte, data e a evidência em 1 linha ("Intenção 15 — 'asked how much to wrap' · call 2/jul") — é assim que o Rafael valida a régua caso a caso. Acordeão simples. **Nenhum botão que escreva em nada no GHL.**

**5. ZERO escrita no GHL** — remover/ocultar da UI todo caminho de escrita; o write_log não pode ganhar nenhuma entrada nova. Supabase é o único destino. O Eugene registra tudo direto no GHL (campos e notas nativos), e o worker LÊ essas entradas no próximo ciclo (entrada manual segue vencendo na síntese).

**6. Verificador pós-call — analítico e orientativo, NUNCA executa.** Após cada call analisada, comparar o que foi dito na call vs. o estado atual no GHL (custom fields, notas, stage, mensagens enviadas). Lacunas viram **Pendências** no card — com regras de redação DURAS:
- **Formato fixo: [FATO com evidência e data] → [AÇÃO exata no GHL].** Ex.: *"Call de hoje 14:32 — cliente disse 'it's a 2026 Tesla Model Y, arrives end of May'. O veículo não está no perfil → adicione no contato."*
- **Zero tom de coach, zero opinião, zero suposição.** Sem evidência literal específica = a pendência NÃO existe (fail-closed, mesma Regra nº1 do advice). Proibido "considere", "seria bom", "lembre-se de".
- **Resoluções alternativas válidas — a pendência conhece as opções e some com QUALQUER uma delas:**
  · Call atendida sem fechamento registrado → *"Envie o follow-up de hoje OU, se o cliente não tem interesse, marque Lost com o motivo."* (some quando o SMS é detectado OU o stage vira Lost)
  · Se a análise detectou desinteresse explícito, a pendência já aponta direto: *"Cliente disse 'not interested, just looking' (call 14:32) → marque Lost com motivo."* — nunca cobra o follow-up nesse caso
  · Call não atendida → *"Voicemail não foi deixado (tentativa 14:32)"* + *"mova o lead para o próximo stage para a mensagem de tentativa disparar"* (some com o avanço de stage)
- As pendências são detectadas por LEITURA e desaparecem sozinhas quando a leitura confirma qualquer resolução válida. O sistema jamais preenche, envia ou move — só aponta. Pendências abertas contam no `FILA_PRONTA.md` e nos relatórios de validação.

**7. Feedback do beta — erro vira dado.** Todo card tem o botão **"Reportar erro"**: chips (Score errado · Estado errado · Não deveria estar na fila · Ordem errada · Pendência incorreta · Outro) + campo de texto livre. Grava em `beta_feedback` (lead, card, tipo, texto, timestamp, snapshot do estado/score no momento). Consolidação: arquivo `BETA_FEEDBACK.md` regenerado diariamente com todos os reportes + o contexto de cada um — é a matéria-prima das rodadas de correção com o Rafael. Nenhum feedback altera nada automaticamente.

## Aceite (gabarito do Rafael — binário)

A fila só é aprovada se os 5 casos aparecerem assim:
- **Agie Pee** = topo da Camada 1, `callback_devido` (ela retornou a ligação e não foi atendida)
- **Naomi** = AUSENTE (pos_venda)
- **Robert R** = fora da discagem ativa (`aguardando_decisao_cliente` desde 9/jun — "I'll call you when I decide"), visível só como nurture na Camada 3 com o estado escrito
- **Shawn** = aparece somente na data do follow-up combinado
- **Adam Nguyen** = `aguardando_evento_externo` (Model YL, produção set.) — fora da fila diária até a janela (~setembro)
Qualquer divergência = não entregar; investigar e corrigir.

## Execução e custo

Backlog de sínteses via Batch API + caching (linhas do tempo compactas); eventos do dia em síncrono. Teto desta rodada: **$40** — estimar antes, abortar acima e reportar. Entregável final: `FILA_PRONTA.md` com o top 30 da fila (posição · estado · por quê · score com breakdown) + amostra de 10 Pendências detectadas pelo verificador (item 6) para validação do formato + confirmação de zero escritas + custo real. Depois do FILA_PRONTA: parar e aguardar.
