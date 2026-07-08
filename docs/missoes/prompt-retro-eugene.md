# MISSÃO: Estudo retrospectivo — por que perdemos leads (diagnóstico para orientar o Eugene)

## Objetivo

Analisar calls históricas COM DESFECHO CONHECIDO (Win vs Lost) para identificar os padrões que separam venda de perda, e transformar isso em: (1) diagnóstico concreto de orientação do Eugene, (2) calibragem do motor de advice, (3) dados de onde o funil morre. **Rodar somente APÓS a Onda 0 da análise total concluir** (sem competir com o deadline das 9h). Via Batch API (50% off) — não há urgência de latência. Somente leitura no GHL; resultados no Supabase e em arquivos.

## Amostra (não transcrever tudo — o insight vem do contraste)

**Janela:** últimos 120 dias. **Pré-filtro:** call atendida > 60s, sem tag teste-interno.

**Grupo WIN (referência do que funciona):** todos os leads que chegaram a `Win` no período — para cada um, a call decisiva (a última atendida antes do appointment que virou venda; fallback: a mais longa).

**Grupo LOST (estratificado, nesta ordem, até o cap):**
1. Perdas de alto valor: leads com carro exótico/premium/2026 que morreram — a perda mais cara e mais instrutiva
2. Quote enviada e morreu sem resposta
3. Appointment marcado → no-show → nunca recuperado
4. Atendeu call(s) e sumiu (respondia antes, silêncio depois)
5. Lost com motivo "price" registrado

**Cap total: 250 calls** (estimar custo antes: esperado ~$15–30 no Batch; abortar acima de $50 e consultar). Se o Grupo Win for pequeno, incluir todas as calls atendidas dos Wins (mais material de referência).

## Análise por call (JSON do M2 estendido com campos retrospectivos)

Além do JSON padrão: `desfecho_conhecido` (win/lost + motivo se houver) · `ponto_de_morte` (onde a conversa/lead morreu: preço apresentado sem defesa / sem próximo passo definido / visita nunca proposta / follow-up prometido e não feito / objeção não tratada / cliente esfriou sem causa na call) · `visita_proposta` (bool + como) · `preco_antes_da_motivacao` (bool) · `extras_empurrados` (bool) · `resposta_tecnica_improvisada` (bool) · `talk_ratio` (Eugene vs cliente, da diarização) · `proximo_passo_definido` (bool + qual) · `classificacao_da_perda`: **controlável** (algo na condução poderia mudar o desfecho) vs **incontrolável** (price shopper declarado, spam, mudou de cidade, comprou antes de qualquer chance) — com justificativa · `nota_da_call` (0–10, critérios: abertura, descoberta, apresentação de preço, fechamento de visita, próximo passo).

## Síntese (o entregável que importa)

Após o batch, UMA análise agregada (Sonnet, contexto longo) gerando:

1. **`DIAGNOSTICO_EUGENE.md`** — tom construtivo, orientado a dinheiro (mais conversão = mais comissão dele):
   - O que ele faz BEM (padrões presentes nos Wins — manter e reforçar)
   - Top 5 erros ranqueados por frequência × impacto, SÓ das perdas controláveis, cada um com: 2–3 trechos reais anonimizados (call dele como material de aula), o que dizer no lugar, e a regra prática
   - Comparativo Win vs Lost nas métricas: % de visita proposta, % com próximo passo definido, cobertura do script, preço-antes-da-motivação, talk ratio, tempo médio até falar preço
   - As 5 regras de mudança imediata (curtas, memorizáveis)
2. **`PERDAS_REPORT.md`** (para o Rafael): distribuição controlável vs incontrolável · pontos de morte do funil com % · perdas de alto valor caso a caso (o que aconteceu com cada exótico/premium perdido) · estimativa de receita recuperável se os top 3 erros controláveis caírem 50%
3. **`PERGUNTAS_DOS_CLIENTES.md`** — inventário de TODAS as perguntas de clientes encontradas nas calls analisadas, agrupadas por tema, com frequência e marcação sugerida: `lane do Eugene` (com resposta-modelo extraída das melhores respostas dele nos Wins) vs. `transferir ao master tech`. O Rafael valida a marcação — isso vira (a) a taxonomia oficial do classificador de pergunta técnica (A11.1) e (b) a cheat sheet de respostas do Eugene (as perguntas mais comuns com a melhor resposta que ele mesmo já deu).
4. **Calibragem do advice:** transformar os padrões achados em regras do motor de advice (ex.: "visita não proposta" detectada → advice prioritário) — atualizar o prompt de análise do M2 com a checklist derivada dos dados reais. Documentar o diff.

## Regras

- Anonimizar trechos no DIAGNOSTICO (primeiro nome só). Nada disso vira falha grave retroativa — período pré-sistema não conta para bônus.
- O DIAGNOSTICO vai primeiro para o Rafael decidir como conduzir com o Eugene.
