#!/usr/bin/env bash
# Mo Imagegen Studio: terminal (Claude) o duoi + gallery anh o tren.
set -e
cd "$(dirname "$0")"
PORT="${1:-8770}"
URL="http://127.0.0.1:$PORT"

# Tu cap nhat code moi tu git moi 60s (neu la git repo). CLI tu refresh access
# token moi lan gen -> khong can vong refresh nen; chi khi refresh_token chet han
# moi phai `codex login` lai (xem login.sh).
if [ -d .git ]; then
  ./autoupdate.sh & UPD=$!
  trap 'kill "$UPD" 2>/dev/null' EXIT
fi

( sleep 1; xdg-open "$URL" >/dev/null 2>&1 || true ) &
python3 imagegen_studio.py --port "$PORT"
