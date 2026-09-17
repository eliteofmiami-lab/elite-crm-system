#!/bin/bash
# DIA 1 — roda tudo de uma vez. Uso: bash research/rodar.sh   (dentro de renda-automatizada/)
HERE="$(cd "$(dirname "$0")/.." && pwd)"; cd "$HERE" || exit 1
mkdir -p data/logs; LOG="data/logs/rodar_$(date '+%Y-%m-%d_%H%M').log"
run() { echo; echo "### $1"; shift; "$@" 2>&1 | tee -a "$LOG"; echo "exit=${PIPESTATUS[0]}" | tee -a "$LOG"; }
[ -f .env ] || { echo "Falta o arquivo .env com a YOUTUBE_API_KEY. Veja research/GUIA_YOUTUBE_API.md"; exit 1; }
run "1/7 Páginas oficiais de política"         python3 research/fetch_policies.py
run "2/7 Teste da chave (1 unidade)"           python3 research/test_key.py
run "3/7 YouTube: descoberta + snapshots"      python3 research/fase1_coleta.py tudo
run "4/7 Evidências de receita (marketplaces)" python3 research/evidencias_coleta.py
run "5/7 Enviar dados para o repositório"      bash research/sync.sh
run "6/7 Amazon KDP (demora ~1h30; pode deixar rodando ou parar com Ctrl+C)" python3 research/kdp_coleta.py
run "7/7 Enviar dados KDP"                     bash research/sync.sh
echo; echo "Pronto. Log completo em $LOG. Agora rode: bash research/install_launchd.sh  (agenda a coleta diária)"
echo "Depois me diga no chat: 'rodou'."
