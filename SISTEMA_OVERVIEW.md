# SISTEMA ELITE — como funciona (explicado sem tecniquês)

## As 4 peças

**1. O Painel** — https://elite-crm-panel.vercel.app
A tela de trabalho. O Eugene (e você) batem o ponto e trabalham a fila de cima pra baixo. Cada card diz o quê fazer, por quê e como — com preços, advice das chamadas e botão direto pro GHL. Roda na Vercel (projeto `elite-crm-panel`).

**2. O Robô (cérebro)** — roda sozinho na nuvem (GitHub Actions), a cada 5 minutos, seg–sáb 8h–19h ET
A cada ciclo ele: vigia as conversas do GHL → nova chamada? baixa o áudio, transcreve (Deepgram) e entende (Claude: veículo, momento, intenção, preços falados, advice) → atualiza scores → gera/fecha os cards da fila (fechamento por evidência: ligou/mandou SMS = card some sozinho) → expurga inelegíveis (Win/Lost/spam) → vigia o bônus do Eugene (lembretes proativos) → avisa o Meta (QualifiedLead) → mantém a fila abastecida com cold calls ranqueadas. Às 18h30 ET gera os dois relatórios do dia.

**3. O Banco (Supabase, projeto elite-crm)** — a memória
Fila de cards, turnos/pausas, análises das chamadas, comissões, custos de IA, relatórios, pagamentos da quinzena. O painel lê daqui; o robô escreve aqui.

**4. As integrações**
- **GHL**: fonte da verdade dos leads. O robô LÊ sempre; ESCREVE só o que foi aprovado em gate.
- **Meta (CAPI direto)**: eventos de qualidade (QualifiedLead) — Purchase continua vindo do seu workflow GHL (para não duplicar).
- **Urable**: leitura; quote continua manual (a API deles não cria quote).
- **Deepgram + Claude**: ouvido e cérebro. Custo real registrado por chamada (projeção: ~$8/mês).

## O que é automático × o que pede aprovação
| Automático (já roda) | Só com gate aprovado |
|---|---|
| Transcrever/analisar chamadas, advice | Mover stage no GHL (cadência, HOT LEADS) |
| Gerar/fechar/expurgar cards da fila | Criar tasks e notas automáticas |
| Score em tempo real NO PAINEL | Score em tempo real NO GHL (G-SCORE-FIX) |
| QualifiedLead pro Meta | Enviar SMS (alerta de missed call, nice-to-talk) |
| Bonus guard, relatórios, custos | Tudo do G2_DEMO.md |

**Regras de ferro:** todo gate = dry-run → aprovação do Rafael no chat → execução → registro no write_log. Nunca deletar nada no GHL/Urable. Entrada manual vence a IA. Tag `teste-interno` fica fora de score/Meta/relatórios/comissões. Terminologia: Advice/Alert (nunca "coaching").

## Dinheiro do Eugene (como o sistema conta)
$10 por appointment que vira venda (potencial ao agendar → confirmado no Win → expira em no-show sem remarcação/Lost). +$50 por quinzena limpa (zero falhas graves — os 6 critérios estão no card "The rules" do painel). O robô detecta as falhas no fim de cada dia, lembra ANTES de virarem falha (bonus guard), e grava o pagamento da quinzena nos dias 15 e último do mês (tabela `payouts`).
