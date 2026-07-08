# RUNBOOK — o que fazer quando algo falhar

## O painel não abre / não loga
1. Teste https://elite-crm-panel.vercel.app em aba anônima.
2. Vercel → elite-crm-panel → Deployments: o último deploy está "Ready"? Se "Error", clique nele → "Redeploy" no anterior que funcionava.
3. Login inválido: Supabase → Authentication → Users → reset de senha do usuário.

## O robô parou (fila não atualiza, chamadas sem análise)
1. github.com/eliteofmiami-lab/elite-crm-system → aba **Actions**: os runs "elite-brain" estão verdes a cada 5 min?
2. Run vermelho → abra e leia a última linha do erro. Reexecutar: botão "Re-run jobs".
3. Rodar manualmente: Actions → elite-brain → "Run workflow".
4. Lembre: ele só roda seg–sáb, 8h–19h ET — fora disso, silêncio é normal.

## PAUSAR o cérebro (emergência)
GitHub → Actions → elite-brain → botão "…" → **Disable workflow** (religa no mesmo lugar). Isso congela tudo: análises, cards, CAPI. O painel continua no ar (só para de atualizar).

## Transcrição falhando
- 1 chamada sem análise: o robô tenta 3 ciclos e marca a flag — normal quando o GHL demora a disponibilizar o áudio.
- Todas falhando: saldo/chave do Deepgram (console.deepgram.com) ou da Anthropic (console.anthropic.com → workspace elite-crm). Recarregou/trocou a chave? Atualize o secret no GitHub (Settings → Secrets → Actions → DEEPGRAM_API_KEY / ANTHROPIC_API_KEY) e o `.env` local.

## Editar PREÇOS (fonte única)
Arquivo `config/prices.json` no repo (pode editar direto no GitHub: abrir arquivo → lápis → commit). Em até 5 min o robô sincroniza e o painel mostra. Nunca editar preço só "de cabeça" no card.

## Editar critérios de FALHA GRAVE / bônus
Hoje os 6 critérios estão no código (`worker/brain/eod_report.py`, função `detect_critical_misses`) e no card "The rules" do painel. Mudança de critério = pedir no chat (mexe em pagamento — sempre com sua aprovação).

## Limpar dados de teste
Painel (como Rafael) → Diagnostics → "🧹 Clear test data". Só apaga do painel; o GHL não é tocado. Contatos precisam ter a tag `teste-interno` no GHL.

## Custos de IA
Relatório diário traz o acumulado do mês; alerta automático acima de $150. Detalhe por chamada: tabela `cost_log` no Supabase. Projeção atual: ~$8/mês.

## Quem faz o quê
- **Código/robô/painel**: o Claude (este chat) — descreva o problema com print.
- **Chaves e contas** (GHL, Meta, Deepgram, Anthropic, Supabase, Vercel, GitHub): Rafael.
- **Aprovações de escrita (gates)**: sempre Rafael, no chat.
