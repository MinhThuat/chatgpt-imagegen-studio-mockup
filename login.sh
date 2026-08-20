#!/usr/bin/env bash
# Chay khi thay bao "run codex login again" / "token refresh failed"
# (refresh_token het han han -> CLI khong tu cuu duoc, phai dang nhap lai).
set -e
cd "$(dirname "$0")"

command -v codex >/dev/null 2>&1 || {
  echo "!! Chua co 'codex' tren PATH. Cai: npm i -g @openai/codex"
  exit 1
}

echo "== Dang nhap lai ChatGPT (codex) — se mo trinh duyet =="
codex login
echo "OK: da dang nhap lai. Quay lai Studio gen tiep binh thuong."
