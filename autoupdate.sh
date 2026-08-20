#!/usr/bin/env bash
# Tu cap nhat code moi tu git remote moi 60s (Studio.sh chay nen file nay).
# Recipient chi la user, khong sua code -> hard reset ve dung remote, khong ket conflict.
# Anh output nam ngoai repo (~/imagegen_studio/) nen reset an toan.
#   ./autoupdate.sh          # vong lap moi 60s
#   ./autoupdate.sh --once   # kiem tra + update 1 lan roi thoat (de test)
set -u
cd "$(dirname "$0")"

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || {
  echo "[autoupdate] khong phai git repo — bo qua."; exit 0; }

update_once() {
  git fetch -q origin "$BRANCH" 2>/dev/null || return 0   # mat mang -> thu lai sau
  local local_h remote_h
  local_h="$(git rev-parse HEAD)"
  remote_h="$(git rev-parse "origin/$BRANCH" 2>/dev/null)" || return 0
  [ "$local_h" = "$remote_h" ] && return 0
  git reset --hard -q "origin/$BRANCH" \
    && echo "[autoupdate] da cap nhat code moi (${remote_h:0:7}) — chay lai Studio de ap dung."
}

[ "${1:-}" = "--once" ] && { update_once; exit 0; }

while true; do
  update_once
  sleep 60
done
