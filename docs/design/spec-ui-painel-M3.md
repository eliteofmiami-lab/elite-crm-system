# SPEC DE UI — Painel Elite CRM (ajustar o painel no ar para o design aprovado)

## Contexto e fonte da verdade

O painel está no ar em elite-crm-panel.vercel.app. Esta missão é ajustá-lo para ficar **idêntico ao design aprovado pelo Rafael**. A fonte canônica são dois arquivos de mockup que o Rafael vai colocar em `docs/design/`:

- `mockup-eugene-workspace-v4.html` — vista do operador (Eugene)
- `mockup-rafael-owner-view-v4.html` — vista do dono (Rafael)

**Copie os valores de CSS literalmente desses arquivos** (cores, raios, sombras, espaçamentos, tamanhos de fonte). Este spec resume e adiciona os comportamentos; em conflito visual, o mockup vence. O logo oficial (PNG preto com fundo transparente, `elite-logo.png`) também vai em `docs/design/` — usar direto sobre fundo claro, altura 36–38px, **sem placa escura atrás**.

## Design tokens

- Fundo de página `#F4F6FA` · cards `#FFFFFF` com borda `#E4E7EC` e sombra `0 1px 2px rgba(16,24,40,.06), 0 1px 3px rgba(16,24,40,.08)` · raio 12–14px em cards, 8px em botões, 999px em pills e chips
- Texto: primário `#101828`, secundário `#475467`, apagado `#98A2B3`
- Azul de ação `#2970FF` (hover ligeiramente mais escuro), azul profundo `#1D4ED8`, azul suave `#EFF4FF`, borda azul `#B2CCFF`
- Verde `#12B76A` / fundo `#ECFDF3` / borda `#ABEFC6` / texto `#067647`
- Âmbar `#F79009` / fundo `#FFFAEB` / borda `#FEDF89` / texto `#B54708`
- Vermelho `#F04438` / fundo `#FEF3F2` / texto `#B42318`
- Roxo `#7A5AF8` / fundo `#F4F0FF` / texto `#5925DC` · Ciano `#06AED4`
- Fonte: **Inter** (400/500/600/700), tamanhos conforme mockup

## Vista do Eugene (idioma: inglês)

**Estrutura vertical:** topbar → KPIs (4) → cartão de comissões → banner de inatividade (condicional) → Task queue → aprovações pendentes → advice do dia → cartão de regras → footnote.

1. **Topbar:** logo + título "Work queue" + data/hora · à direita: pill verde de clock-in com cronômetro do turno ("Clocked in 9:04 AM · 2h 48m"), pill azul "$ Today +$X", botões `Start break` e `Clock out` (este com texto/borda em vermelho suave). **Antes do clock-in, a fila fica bloqueada** — tela com botão grande "Clock in" e resumo do dia que espera (N tasks, appointments a confirmar).
2. **KPIs:** Calls today (x / ~100) · In queue · Quotes pending · Avg response (min).
3. **Cartão de comissões (estilo verde-dinheiro):** "My commissions — July" · valor grande **confirmed** · potential · awaiting sale · booked today · **"$50 rule bonus · on track X/14"** · nota: "$10 per booked appointment that closes · +$50 every 2 weeks with zero critical misses". Estados do bônus: `on track` (verde) e `lost this period` (cinza/vermelho, com motivo + data + quando o próximo período começa).
4. **Banner de inatividade:** aos 10 min sem evento → banner âmbar ("10 min without activity — N leads waiting"); aos 15 min → mesmo banner em vermelho (`#FEF3F2`/`#B42318`) + SMS disparado; aos 20 min → registra bloco (sem mudança visual adicional, vermelho persiste até novo evento). Some com qualquer evento novo. Pausa declarada suspende o contador.
5. **Task queue:** card único, header "Task queue · N" + caption "Auto-sorted by priority — always take task 1". Linhas numeradas com círculo (cinza; azul preenchido na task 1). **Task 1 sempre expandida** (fundo `#EFF4FF`, borda esquerda azul 3px) com: título da ação, meta (veículo + contexto), chips, score, seções "Why now" e "How to play it" em sub-cards brancos, exhibit da quote (verde, quando houver), e ações: `Open in GHL ↗` (primário azul), `Call script`, `Can't do now`, telefone à direita. Chips por tipo: Hot (vermelho suave) · New lead (azul suave) · Quote (verde suave) · Appointment (roxo suave) · Cold (cinza) · Snoozed (cinza, linha com opacidade ~0.62, numeração vira ↷, meta mostra motivo e horário de retorno).
6. **Snooze ("Can't do now"):** painel tracejado com chips de motivo rápido (Client asked for later / Waiting on info / Line busy / Other) + input livre + `Send & reschedule`. Comportamento no backend: motivo com horário/evento → reagenda e retorna à fila 5 min antes; motivo de bloqueio → pausa a task e alerta o Rafael se persistir; motivo vago/repetitivo → aceita e registra; 3+ motivos rejeitados na quinzena = falha grave.
7. **Aprovações:** card "Approve & send: Nice to talk to you — {nome}" com preview de 1 linha, botões `Edit` e `Approve & send` (envio via API do GHL ao aprovar).
8. **Advice from today's calls:** card com as recomendações do dia (mesmo conteúdo que o Rafael vê, em inglês), atualizado em tempo real a cada call processada. Cada item: tag azul `Advice` + texto + link "View lead ↗" (deep-link GHL/card). Rodapé fixo: advice nunca afeta o pagamento e cada nota reaparece no card do lead na próxima call.
9. **Cartão de regras (fixo no fim):** título "The rules — read once, live by them", duas colunas — **How you earn** (verde) e **Critical misses — these cost the $50** (vermelho, as 6 falhas graves) — e rodapé: deslizes menores não tiram o bônus; falha grave avisa no mesmo dia; a próxima quinzena sempre começa limpa. Texto exato do mockup.
10. **Footnote:** "Tasks complete themselves when the call or text is detected in GHL — nothing to mark as done."

## Vista do Rafael (idioma: português)

**Estrutura:** topbar → KPIs (4) → grid 2×2 (Funil · Metas / Atividade · Alertas) → footnote.

1. **Topbar:** logo + "Visão do dono" + data · pill de status do Eugene (verde "ativo · clock-in 9:04 · última ação há X min"; cinza quando fora do turno; âmbar quando em bloco de inatividade).
2. **KPIs:** Ligações (x/~100) · Quotes enviadas · Appointments · **Comissão Eugene · mês** (card destacado azul-suave, com linha do bônus: "Bônus quinzena $50 · em curso — X/14 dias, 0 falhas graves" ou o estado de perda).
3. **Funil de hoje:** 6 barras horizontais arredondadas (Leads novos → Contatados → Qualificados → Quotes → Appointments → Win) na progressão de cor azul → azul claro → roxo → roxo claro → ciano → verde, com contagens.
4. **Metas de hoje — auditadas:** 6 linhas com círculo ✓ (verde) / ✕ (vermelho) + fração/porcentagem à direita.
5. **Atividade por hora:** barras azuis por hora do turno, blocos de inatividade em âmbar, legenda, e nota com os blocos registrados e o total fora de pausas.
6. **Alertas e recomendações:** linhas com tag colorida — `Alerta` (vermelho: regra quebrada, ex. voicemail não deixado), `Advice` (azul: recomendação de venda extraída da transcrição), `Atenção` (âmbar: lead esfriando/80+ chegando no limite), `Reporte` (azul: snooze do Eugene com motivo e validação).
7. **Footnote:** "Relatório completo do dia gerado às 18:30 · comissões conciliáveis com as vendas no fechamento do mês."

## Comportamentos globais

- **Advice bilíngue e compartilhado:** cada análise de call gera `advice_en` (para o Eugene) e `advice_pt` (para o Rafael) — mesmo insight, dois idiomas, exibido em tempo real nas duas vistas. O advice do lead também é injetado na seção "How to play it" do próximo card daquele lead (insight vira ação). Advice NUNCA entra em metas/bônus — deixar isso explícito na UI. Terminologia: nenhuma ocorrência de "COACHING" na interface (a versão no ar ainda exibe — corrigir).
- **Bonus guard (lembretes proativos):** o sistema trabalha A FAVOR do bônus do Eugene — antes de qualquer item virar falha grave, o painel lembra com tempo de corrigir: quote do dia não enviada (lembrete às 15:00, card urgente às 16:30), appointment de amanhã não confirmado (lembrete às 10:15), lead 80+ se aproximando das 24h órfão (card urgente 4h antes do limite). Exibido como linha "Bonus guard" no cartão de comissões (âmbar com o item pendente; verde "all clear — nothing threatens your bonus today" quando limpo) e como interrupção da Camada 1 na fila quando urgente
- Fila recalculada em tempo real nas 3 camadas (interrupções > dia planejado > cold calls); quando o evento correspondente é detectado no GHL, a task some e a seguinte vira a nº 1 já expandida — sem clique de "concluir"
- Clock out dispara a geração do relatório do dia; clock-in obrigatório para liberar a fila
- Idioma fixo por usuário: Eugene = EN, Rafael = PT
- Responsivo: grids colapsam para 1 coluna nos breakpoints do mockup (~640–720px)

## Checklist de aceite (verificar item a item contra o painel no ar)

- [ ] Logo oficial preto sobre fundo claro, sem placa escura
- [ ] Tokens (cores/raios/sombras/Inter) idênticos ao mockup
- [ ] Clock in bloqueia/libera a fila; cronômetro de turno; Start break; Clock out
- [ ] Cartão de comissões com confirmed/potential/awaiting/booked today + status do bônus (2 estados) + linha Bonus guard (âmbar/verde)
- [ ] Banner de inatividade com escalada 10 (âmbar) / 15 (vermelho + SMS) / 20 (registro)
- [ ] Task 1 expandida com Why now / How to play it / exhibit / 3 botões; chips por tipo; estado snoozed
- [ ] Painel de snooze com chips + texto livre + análise de motivo no backend
- [ ] Card de aprovação do nice-to-talk-to-you funcional (envia via GHL)
- [ ] Card "Advice from today's calls" na vista do Eugene (tempo real, EN, link pro lead, rodapé de não-punição)
- [ ] Zero ocorrências de "COACHING" na UI — tags renomeadas para Advice
- [ ] Cartão de regras fixo com as duas colunas e o rodapé
- [ ] Vista do dono: 4 KPIs, funil 6 barras, metas ✓/✕, atividade por hora com inatividade, alertas com 4 tipos de tag
- [ ] Idiomas fixos por papel; responsivo; footnotes
