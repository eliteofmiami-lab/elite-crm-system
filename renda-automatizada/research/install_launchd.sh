#!/bin/bash
# Agenda a coleta diária no Mac (launchd) às 08:00. Rode uma vez: bash research/install_launchd.sh
# Se o Mac estiver dormindo às 08:00, o launchd roda assim que ele acordar. Para remover: bash research/install_launchd.sh remover
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.renda-automatizada.coleta"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
UID_="$(id -u)"
if [ "${1:-}" = "remover" ]; then
  launchctl bootout "gui/$UID_" "$PLIST" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"; echo "removido"; exit 0
fi
mkdir -p "$HOME/Library/LaunchAgents" "$HERE/data/logs"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$HERE/research/diario.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$HERE/data/logs/launchd.out</string>
  <key>StandardErrorPath</key><string>$HERE/data/logs/launchd.err</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string></dict>
</dict></plist>
PL
launchctl bootout "gui/$UID_" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$UID_" "$PLIST" 2>/dev/null || launchctl load "$PLIST"
echo "agendado: todo dia às 08:00 → $HERE/research/diario.sh (logs em data/logs/)"
echo "para testar agora: launchctl kickstart -k gui/$UID_/$LABEL"
