#!/bin/bash
# Envia os dados coletados para o repositório (branch do projeto) para o Claude ler e responder no chat.
# Nunca envia .env, cache da API nem HTML bruto (estão no .gitignore).
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"          # renda-automatizada/
REPO="$(cd "$HERE/.." && pwd)"                    # raiz do repositório
BRANCH="claude/renda-automatizada-50k-w63bt3"
cd "$REPO" || exit 1
git add renda-automatizada/data renda-automatizada/reports renda-automatizada/research/policies_raw 2>/dev/null
if git diff --cached --quiet; then
  echo "[sync] nada novo para enviar"; exit 0
fi
git commit -q -m "coleta $(date '+%Y-%m-%d %H:%M')" || exit 1
for i in 1 2 3 4; do
  if git pull -q --rebase origin "$BRANCH" && git push -q origin "$BRANCH"; then
    echo "[sync] enviado para $BRANCH"; exit 0
  fi
  echo "[sync] falhou (tentativa $i), esperando..."; sleep $((2**i))
done
echo "[sync] NÃO conseguiu enviar. Me mande esta mensagem e o resultado de: git status"
exit 1
