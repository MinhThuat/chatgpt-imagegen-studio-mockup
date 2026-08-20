#!/usr/bin/env bash
# Bam 1 cai: lan dau tu setup, sau do mo Studio (tu bat trinh duyet).
set -e
cd "$(dirname "$0")"

# Chua cai (thieu aiohttp hoac thu muc) -> chay setup 1 lan.
if ! python3 -c "import aiohttp" 2>/dev/null || [ ! -d "$HOME/imagegen_studio/out" ]; then
  ./setup.sh
fi

exec ./Studio.sh "$@"   # Studio tu mo http://127.0.0.1:8770 + tu cap nhat git 60s
