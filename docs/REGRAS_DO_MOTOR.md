# REGRAS DO MOTOR — Fila, Score e Orientação (Elite Premium Detailing)
### Documento de validação do dono · v1.0 · para revisão do Rafael

Este documento é a regra completa que decide: (1) a ORDEM dos cards na fila do assistente, (2) a URGÊNCIA de cada um, (3) a ORIENTAÇÃO exibida. É também o núcleo replicável do modelo — o que um novo assistente (ou um novo shop) precisa pra operar.

---

## 1. O princípio

**Posição na fila = CAMADA → GATILHO → SCORE → antiguidade.**
- A **camada** responde "o que está acontecendo agora exige ação?" (urgência situacional)
- O **gatilho** ordena dentro da camada (o quê aconteceu e quando)
- O **score** desempata (quem é o lead — valor)
- Persistindo empate: o que espera há mais tempo vem primeiro

A fila é **viva**: recalcula a cada evento novo (call, SMS, quote, appointment, análise de transcrição, mudança de stage). Cards fecham por evidência detectada no GHL — nunca por declaração.

## 2. Camada 1 — Interrupções (furam tudo)

Ordem interna fixa:
1. **Bonus guard crítico** — item prestes a virar falha grave: quote de call de hoje não enviada (lembrete 15:00, urgente 16:30) · appointment de amanhã não confirmado (lembrete 10:15) · lead 80+ a 4h do limite de 24h
2. **Lead novo em horário comercial** — SLA 15 min, relógio visível
3. **Inbound perdida** — callback imediato
4. **Respondeu SMS ou pediu ligação** — mais recente primeiro
5. **Lead 80+ sem contato há quase 24h** (sem task futura e sem evento aguardado)

Dentro do mesmo gatilho: score decrescente → mais antigo primeiro.

## 3. Camada 2 — Dia planejado

1. **Bloco da manhã (até 11:00):** confirmação personalizada dos appointments dos próximos 2 dias
2. **New Leads / HOT LEADS sem NENHUMA tentativa de contato** — independente de idade — por score decrescente (lead sem primeiro contato é dinheiro parado; fura follow-up agendado)
3. **Follow-ups com hora marcada:** entram na fila NA SUA HORA (task de 12:30 aparece 12:30)
4. **Quotes pendentes** de revisar/enviar no Urable (prazo: mesmo dia) e **wrap-ups pendentes** (nice-to-talk-to-you da primeira call atendida)
5. **Retries de no-answer:** call não atendida volta automaticamente em período diferente (AM→PM), seguindo a cadência de stages existente

## 4. Camada 3 — Cold calls (só quando 1 e 2 estão vazias)

`rank = score_original × fator_recência × ponto_de_morte × motivo_de_perda`
- **Ponto de morte** (quanto mais perto do fim do funil, maior a chance de resgate): no-show sem reagendamento > quote sem resposta > respondeu e sumiu > nunca respondeu
- **Motivo de perda:** recuperável (preço, timing) entra COM o contexto no card; terminal (comprou em outro lugar, vendeu o carro, spam, número errado) fica fora para sempre
- Refresh semanal; qualquer resposta do lead o puxa de volta para a Camada 1 na hora
- Análise lazy: a transcrição só é processada quando o lead entra no top 20 da camada

## 5. Elegibilidade (regra dura)

- `Win` NUNCA gera card; Win no meio do dia fecha todos os cards do lead (e confirma a comissão do appointment vinculado)
- `delete`/spam: nunca · `teste-interno`: fora de score, CAPI, relatórios e comissões · `Lost`: só na Camada 3
- Contato com opps duplicadas: vale a mais avançada

## 6. Score — quem o lead é (0–100)

| Componente | Pontos | Critério |
|---|---|---|
| **Carro** | 0–35 | Exótico ou premium = 35 · qualquer 2025/2026 = 25 · demais = 10 (vale o maior, não soma) |
| **Momento** | 0–25 | Chegando/recém-entregue = 25 · <3 meses = 20 · 3–6m = 15 · 6–12m = 10 · >1 ano = 5 |
| **Engajamento** | 0–25 | Ligou pra nós OU pediu ligação = 25 · respondeu SMS = 15 · atendeu call = 10 · nada = 0 |
| **Intenção** | 0–15 | **Visitou a loja** (showed ou tag `visitou-loja`) OU pediu quote/discutiu preço = 15 · interessado indeciso = 10 · só pesquisando = 5 · sem call: proxy `how_soon` (ASAP 15 · 2 sem 12 · mês 8 · explorando 3) |

**Honestidade obrigatória:** componente sem dado = `?` (nunca zero silencioso) · exibição sempre `conhecido/máximo-apurável` + selo **call-verified** (Momento/Intenção vindos de transcrição) ou **partial**.
**Faixas de ação:** 80+ = visita/quote no mesmo dia · 60–79 = follow-up agendado com contexto · 40–59 = nurture · <40 = fila fria.

## 7. Flags de ouro — DEFINIDAS PELO RAFAEL

| Sinal | Regra final |
|---|---|
| **Depósito pago** | Depósito é não-reembolsável = venda. O Rafael marca a opp como **Win com o valor da venda** (ação manual dele, atalho no Appointments Board). O Win dispara: fechamento de todos os cards do lead + confirmação da comissão. A receita do fechamento mensal lê o valor monetário das opps em Win. |
| **Visitou a loja** | Comprovada pelo **Appointments Board** (visão do Rafael): toque em `Showed` = visita confirmada → flag persistente + Intenção 15. `visita_provavel` detectada em transcrição continua existindo para visitas fora de appointment, confirmável em um clique. |
| **Falou com o Rafael** | NÃO pontua por si só — o que vale é a **resolução da call** (`resolucao_da_call`: qualificou / avançou / desqualificou / pendente), extraída pela análise. Desqualificação derruba o score. Transferências seguem como métrica. |
| **Cliente repetido / indicação** | **Fora da fila de venda.** Cliente com Win anterior que agenda de novo não gera cards — aparece só no Appointments Board e no briefing (com histórico de serviços). Indicação idem quando vem direto; se entrar como lead novo pelo funil, é lead normal. |

## 8. Orientação por tipo de card (o que o assistente vê)

| Tipo | Conteúdo obrigatório |
|---|---|
| New lead | Script de pré-qualificação (9 passos + frases exatas) · Log call details |
| Follow-up | Resumo da última conversa (3 linhas) + gancho pessoal + como abrir |
| Quote-sent | **A quote real** (serviço, valor, data, link Urable) + sentimento da call + alçada de desconto: cupom de $200 para fechar AGENDAMENTO é do assistente (registrar sempre); além disso, só o Rafael |
| Appointment | Mensagem de confirmação sugerida com o gancho pessoal |
| Inbound perdida | Callback imediato + contexto do que se sabe |
| Cold | Ângulo de reabertura + onde a conversa morreu |
| Wrap-up | Rascunho do nice-to-talk-to-you — card só conclui com o SMS detectado |

**Regras transversais (valem para TODOS):** o fechamento é sempre a VISITA à loja · preços exibidos = serviço de interesse (`interesse_atual`, atualizado a cada call) no tier do carro, sempre como starting price · add-ons only-if-asked · advice apenas com evidência literal da transcrição e alavanca de conversão (silêncio é válido; crítico automático barra filler) · cupom de $200: ferramenta do assistente para fechar a visita — todo uso é registrado, aparece no briefing e nos relatórios · pergunta técnica de julgamento → master tech (marca/pacote/preço = lane do assistente).

## 9. O que mantém a fila confiável

- Detecção por evidência (nada de auto-declaração) · snooze com motivo analisado · modo observação para toda classificação nova · write_log de toda escrita · relatório diário audita as 6 metas + bônus quinzenal

---
*Validação: o Rafael revisa cada seção e marca OK ou ajusta. Ajustes viram config (pesos, prazos, faixas) — a estrutura não muda. Este documento, validado, é a base do playbook de replicação para novos assistentes e novos shops.*
