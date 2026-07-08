# MISSÃO: Análise total — scores completos, fila em ordem real e baseline de tracking

## Objetivo

Processar as gravações de toda a base ativa para completar Momento (0–25) e Intenção (0–15) de cada lead, regenerar a fila em ordem de importância real, e estabelecer o baseline do tracking diário. **Nenhuma escrita no GHL nesta rodada** — tudo vai para o Supabase (o painel ordena a partir dele); o write-back ao GHL acontece em lote após a aprovação do G2.

## Escopo (nesta ordem — não processar tudo indiscriminadamente)

**P1 — Oportunidades abertas no New Pipeline** (fora Win/Lost/delete): para cada lead, transcrever e analisar **apenas a última call atendida** (duração > 20s). Calls anteriores do mesmo lead: ignorar (agregam pouco e custam).
**P2 — Quote Sent e Appointment Booked:** além da última call atendida, capturar o sentimento sobre preço/quote (alimenta os cards de follow-up de quote e o anti-no-show).
**P3 — Lost recuperável e legado (cold list): NÃO processar agora.** Análise lazy: transcrever a última call atendida somente quando o card entrar no top 20 da Camada 3. Marcar esses leads como `analise_pendente`.
Leads sem nenhuma call atendida: mantêm o score v2 (carro + engajamento + proxy how_soon) — sem custo.

## Execução

1. **Custo primeiro:** estimar minutos e nº de calls do escopo P1+P2 e reportar ANTES de rodar (esperado: ~$25–40 total; abortar e consultar o Rafael se a projeção passar de $80). Usar Batch API da Anthropic (50% off) + prompt caching no system prompt; Deepgram Nova pré-gravado. Logar custo real em `cost_log`.
2. Pipeline: baixar gravação → Deepgram (diarização) → análise Claude (JSON completo do plano M2 2.2, incluindo advice_en/advice_pt) → gravar em Supabase (`transcripts`, `analyses`).
3. **Score v3 por lead** = Carro + Engajamento (v2) + Momento e Intenção da transcrição (intenção da call SOBRESCREVE o proxy how_soon). Guardar breakdown + evidência de cada componente.
4. **Regenerar a fila completa** com as 3 camadas sobre os scores v3, aplicando todas as regras vigentes (elegibilidade A7.4, New Leads parados no topo da Camada 2, cadência, wrap-ups pendentes, cold ranking com motivo recuperável).
5. **Baseline de tracking:** criar tabela `daily_snapshots` e gravar o snapshot de hoje (distribuição de scores, contagens por stage e camada, pendências) — é a régua dos comparativos diários do M4.

## Entregáveis para o Rafael

1. `ANALISE_TOTAL_REPORT.md` — volumes processados, custo real vs. estimado, distribuição de scores antes/depois, quantos leads mudaram de faixa (subiram/desceram), e os 10 maiores movimentos com o porquê.
2. `RESCORE_TOP50.md` — os 50 primeiros da fila nova, cada um com: posição, score v3 com breakdown e evidência da transcrição (1 linha por componente), camada, ação recomendada e link GHL. É a validação humana do Rafael.
3. `G2_DEMO.md` — desta mesma rodada, as 5 melhores calls no formato do gate G2 (o que seria gravado onde no GHL).

## Após aprovação do Rafael (gate único)

Write-back em lote no GHL: scores v3 nos custom fields de oportunidade + nota estruturada por lead analisado (resumo, evidências, sentimento) — tudo no write_log. Em seguida, ativar o incremental: o worker passa a processar só calls novas a cada ciclo, mantendo scores, fila e snapshots diários atualizados automaticamente. A partir daí o tracking diário do M4 roda sobre base completa e consistente.

---

## ADENDO — Execução em ondas (DEADLINE: fila funcional amanhã 9:00 AM ET)

**Regra de ouro:** a fila das 9:00 NÃO depende da análise completa. Ela sempre renderiza com o melhor score disponível por lead — v3 (call-verified) onde já analisado, v2 (parcial) no restante — e a ordem se refina automaticamente conforme as ondas processam. Cards exibem o selo do score: `call-verified` quando Momento/Intenção vêm de transcrição, `partial` caso contrário.

**ONDA 0 — hoje à noite, API SÍNCRONA (não usar Batch nesta onda — prazo vale mais que o desconto).**
Processar a última call atendida (>20s) apenas de:
1. Leads com resposta de SMS ou pedido de ligação nos últimos 14 dias
2. `Quote Sent` (todos)
3. `Appointment Booked` com appointment nos próximos 3 dias
4. Top ~120 por score v2 entre as demais opps abertas que têm call atendida

(New Lead/HOT LEADS sem nenhuma call atendida: nada a transcrever — já prontos com v2.)

Execução: estimar volume e custo da Onda 0, reportar, e **rodar AGORA como script local contínuo** (não esperar o cron de 5 min), com concorrência controlada (ex.: 5 transcrições em paralelo, respeitando rate limits de Deepgram e Anthropic; retry com backoff). Progresso a cada 25 leads + ETA. Meta: Onda 0 concluída esta noite.

**ONDA 1 — a partir de amanhã, via Batch API (50% off):** demais opps abertas com call atendida (Follow Up, Contact 1/2 AM-PM...), em lotes noturnos até esgotar a base ativa.

**ONDA 2 — lazy (como já definido):** Lost recuperável e legado só quando o card entrar no top 20 da Camada 3.

**Às 8:45 AM ET:** gerar automaticamente a fila do dia e o `RESCORE_TOP50.md` refletindo o estado real do momento, indicando por lead se o score é call-verified ou partial. A validação do Rafael sobre o TOP50 gateia apenas o write-back ao GHL — a fila do painel funciona desde já, pois lê do Supabase.

---

## ADENDO 2 — Lista de prioridades da análise (VERSÃO FINAL — substitui o escopo das Ondas 0 e 1)

**Janela geral:** leads criados OU com qualquer atividade nos últimos **90 dias** (inclui os migrados do ELITE ADS que se enquadrem).
**Pré-filtro de elegibilidade:** opp fora de Win/delete · não é lost terminal · sem tag teste-interno · **tem pelo menos uma call atendida > 20s** (sem call atendida = nada a transcrever; o lead segue com score v2 e entra na fila normalmente).

### FAIXA A — obrigatórios na Onda 0 (concluir até 9:00 AM, síncrono, nesta ordem)
A situação exige o conteúdo da conversa para a próxima ação:
1. **Quote Sent** (todos) — o sentimento da call decide a abordagem do rescue
2. **Appointment nos próximos 3 dias** — confirmação com contexto (anti-no-show)
3. **Respondeu SMS ou pediu ligação nos últimos 14 dias** — interrupções de amanhã
4. **Inbound calls nos últimos 30 dias** — quem ligou direto (intenção máxima)
5. **No-shows sem reagendamento** (status noshow no GHL, últimos 90 dias) — intenção provada, resgate de alto valor

### FAIXA B — pontos de análise (ordena todo o restante elegível; processa em ordem decrescente — o que couber na Onda 0 entra síncrono, o resto vira Onda 1 via Batch)
- **Carro** (maior aplicável, não soma): exótico **+30** · premium **+25** · qualquer 2026 **+20**
- **Serviço declarado:** Both — PPF & Coatings **+20** · PPF **+15** · só Coatings **+8** · "not sure / need help choosing" **+5**
- **Urgência (how_soon):** As soon as possible **+15** · Within 2 weeks **+12** · Within a month **+6**
- **Engajamento histórico:** inbound antiga (>30d) **+10** · respondeu SMS há mais de 14 dias **+8**
- **Recência (criação ou última atividade):** ≤30 dias **+10** · 31–60 **+5** · 61–90 **+2**

Registrar `analysis_priority` (0–100) por lead no Supabase para auditoria da ordem.

### FAIXA C — lazy (inalterada)
Lost recuperável e legado fora da janela de 90 dias: analisar somente quando o card entrar no top 20 da Camada 3.

**Nota de execução:** se a Faixa A sozinha estourar a janela da noite, reportar imediatamente com ETA e custo — a Faixa A não pode ficar pela metade às 9:00. A Faixa B pode transbordar para a Onda 1 sem prejuízo (a fila renderiza com v2 + selo partial até lá).
