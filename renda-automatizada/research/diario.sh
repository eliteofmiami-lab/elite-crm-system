#!/bin/bash
# Rotina diária (chamada pelo launchd às 08:00): continua a coleta do YouTube dentro da quota e envia os dados.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$HERE/data/logs"
LOG="$HERE/data/logs/diario_$(date '+%Y-%m-%d').log"
{
  echo "=== $(date) ==="
  cd "$HERE" || exit 1
  /usr/bin/python3 research/fase1_coleta.py tudo
  bash research/sync.sh
} >> "$LOG" 2>&1
