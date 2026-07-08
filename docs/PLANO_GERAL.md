# PLANO GERAL — como o sistema fica agora (para validação do Rafael)

## A visão em um parágrafo

Nenhum contato entra sem resposta imediata (automações nativas do GHL cobrem o fora-de-horário) e nenhum contato fica sem desfecho (o painel cobra resolução de tudo que está na janela viva). O que envelheceu não some nem afoga o presente: vira ração diária do Warm up até zerar. O bônus do Eugene paga exatamente por manter esse ciclo limpo. Datas deixam de ser bagunça porque **cada coluna tem uma janela**, e o que sai da janela tem destino definido.

---

## A. Janelas de data (o corte entre "hoje" e "resgate") — números propostos, você ajusta

| Coluna | Janela viva (vira card do dia) | Envelheceu → destino |
|---|---|---|
| Retornar / Responder / Hot | Inbound perdida e SMS sem resposta dos últimos **3 dias** | Vai pro **Warm up** com a origem marcada ("inbound perdida 12/jun") |
| New Leads — Call ASAP | Stage New Lead até **7 dias** | Warm up (lead que ninguém ligou em 7 dias é resgate, não urgência) |
| Tasks & Quote follow-ups | Tasks de hoje + vencidas até **7 dias** (marcadas "overdue") · Urable sem resposta até **14 dias** | Warm up |
| Pipeline follow-ups | Stages Contact 1/2 e Follow Up com atividade nos últimos **30 dias** | Warm up |
| Confirmar appointments | Próximos 2 dias (naturalmente datado) | — |
| Warm up | Ração de **20/dia**: tudo que envelheceu acima + Lost recuperável + parados 30d+ | Trabalhado → resolução; sem interesse → **Lost terminal** (sai pra sempre) |

**Princípio: nada é deletado e nada é esquecido — só muda de coluna.** A chamada perdida de 3+ dias que hoje se perde passa a ter endereço: a ração do Warm up, que processa o passivo em ordem (mais recente primeiro) sem sufocar o dia.

## B. Faxina de dia zero (uma vez, antes do go-live)

O passivo atual (não categorizados do mês passado, perdidas antigas) não pode abrir o painel com 500 cards. Plano:
1. O sistema gera **`FAXINA_DIA_ZERO.md`**: inventário por categoria com contagens e listas — inbound perdidas >3d · SMS sem resposta >3d · New Leads >7d · stages parados >30d · tasks vencidas · leads sem categorização.
2. **Você decide o corte de arquivamento em massa** (proposta: "never answered / sem categoria com 90+ dias → Lost 'no response'"). A execução é pelo **bulk action nativo do GHL** (o sistema entrega a lista pronta com links; você ou o Eugene selecionam e movem em massa em minutos — o painel continua sem escrever nada).
3. O que sobrar do passivo entra na fila do Warm up. Com ração de 20/dia, um passivo de ~300 zera em ~3 semanas — enquanto o presente já roda 100% limpo desde o dia 1.

## C. O dia-a-dia (como fica na prática)

**9:00** — Eugene clock-in. Coluna 1 primeiro (retornos de perdidas da noite, SMS pendentes, HOT). **Até 11:00** — confirmações dos próximos 2 dias. **Durante o dia** — New Leads conforme entram (o card nasce em ≤5 min), tasks na hora marcada, pipeline follow-ups, e Warm up preenchendo os vazios. **Toda call terminada** — resolução em até 15 min ou o card fica vermelho na faixa. **Fim do turno** — clock-out com quadro limpo = dia limpo = bônus andando. **Sua rotina** — 2 minutos na aba Controle: sem-resolução, cards de 2+ dias, turno do Eugene. O resto é exceção, não vigilância.

## D. Fora de horário — automações NATIVAS do GHL (a criar; guia passo a passo vem com o painel)

Horário comercial proposto: **seg–sáb, 9:00–17:00 ET** (config). Quatro workflows nativos (Settings → Workflows — zero custo, zero IA, e é o GHL enviando, não o nosso painel):

1. **Chamada perdida FORA do horário** → SMS imediato: *"Hi! This is Elite Premium Detailing — we're closed right now, but you're first in line tomorrow. Reply with your car and what you're looking for, and we'll call you at 9 AM sharp."* → às 9:00 o card já está na coluna 1 esperando o Eugene.
2. **Lead novo (form/Meta) FORA do horário** → SMS imediato de boas-vindas + expectativa: *"Thanks for reaching out to Elite Premium Detailing! We'll call you first thing at 9 AM. Meanwhile: what car is it, and are you thinking PPF, ceramic, or a wrap?"* — muitos respondem de noite, e o Eugene abre o dia com contexto.
3. **SMS recebido FORA do horário** → auto-reply (1x por conversa): *"We're closed at the moment — back at 9 AM and you'll hear from us first thing."*
4. **Chamada perdida DENTRO do horário** → já existe (validar o texto atual e padronizar).

Resultado: o lead das 22h nunca mais espera 11 horas em silêncio — recebe resposta em segundos, e a manhã do Eugene começa com a fila já contextualizada.

## E. O que preciso de você para fechar

1. As **janelas** da tabela A estão boas? (3d / 7d / 14d / 30d / ração 20)
2. O **corte da faxina**: 90+ dias sem resposta → Lost em massa, ok? Outro número?
3. **Horário comercial** para as automações: seg–sáb 9–17 ET confirma?
4. Os **textos** dos 3 SMS fora de horário — ajusta algo?
