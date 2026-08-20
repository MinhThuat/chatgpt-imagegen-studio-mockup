#!/usr/bin/env bash
# Setup Imagegen Studio (ban Seed-pro). Chay 1 lan.
# KHONG can sudo: cai vao ~/.local. Cai gi da co san thi bo qua.
#
# Kien truc: bang Seed-pro (BytePlus Ark) viet prompt -> gen bang CLI
# chatgpt-imagegen (backend codex). KHONG con Claude terminal.
set -e
cd "$(dirname "$0")"

BIN="$HOME/.local/bin"; mkdir -p "$BIN"
export PATH="$BIN:$PATH"
# nho PATH cho lan sau
grep -qs '.local/bin' "$HOME/.bashrc" 2>/dev/null \
  || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

dl() {  # dl <url> -> stdout (curl hoac wget)
  if   command -v curl >/dev/null 2>&1; then curl -fsSL "$1"
  elif command -v wget >/dev/null 2>&1; then wget -qO- "$1"
  else echo "!! Can curl hoac wget de tai. Cai 1 trong 2 roi chay lai." >&2; return 1; fi
}

echo "== 1. python3 =="
if command -v python3 >/dev/null 2>&1; then
  echo "  da co: $(python3 --version 2>&1)"
else
  echo "  chua co -> tai python ban prebuilt (standalone) vao ~/.local (khong can sudo)"
  PY_TAG="20241206"; PY_VER="3.12.8"
  case "$(uname -m)" in
    x86_64)        PA=x86_64 ;;
    aarch64|arm64) PA=aarch64 ;;
    *) echo "!! CPU $(uname -m) khong ro ban python — cai python3 tay roi chay lai."; exit 1 ;;
  esac
  dl "https://github.com/astral-sh/python-build-standalone/releases/download/$PY_TAG/cpython-$PY_VER+$PY_TAG-$PA-unknown-linux-gnu-install_only.tar.gz" \
    | tar -xz -C "$HOME/.local" --strip-components=1
  echo "  python $(python3 --version 2>&1) da cai vao ~/.local"
fi

echo "== 2. node + npm (can de cai codex) =="
if command -v codex >/dev/null 2>&1; then
  echo "  bo qua (codex da co)"
elif command -v npm >/dev/null 2>&1; then
  echo "  da co: npm $(npm --version)"
else
  echo "  chua co -> tai node ban prebuilt vao ~/.local (khong can sudo)"
  NODE_VER="v22.11.0"
  case "$(uname -m)" in
    x86_64)        A=x64 ;;
    aarch64|arm64) A=arm64 ;;
    *) echo "!! CPU $(uname -m) khong ro ban node — cai node tay roi chay lai."; exit 1 ;;
  esac
  dl "https://nodejs.org/dist/$NODE_VER/node-$NODE_VER-linux-$A.tar.xz" \
    | tar -xJ -C "$HOME/.local" --strip-components=1
  echo "  node $(node --version) da cai vao ~/.local"
fi
# global install -> vao ~/.local (khong dung sudo)
npm config set prefix "$HOME/.local" >/dev/null 2>&1 || true

echo "== 3. codex (backend gen anh) =="
command -v codex >/dev/null 2>&1 && echo "  da co: $(command -v codex)" \
  || npm install -g @openai/codex

echo "== 4. aiohttp (server Studio) =="
python3 -c "import aiohttp" 2>/dev/null && echo "  da co" \
  || python3 -m pip install --user --break-system-packages "aiohttp>=3.9"

echo "== 5. Pillow (tuy chon — shrink anh cho re token khi viet prompt) =="
python3 -c "import PIL" 2>/dev/null && echo "  da co" \
  || echo "  chua co (KHONG bat buoc). Muon: python3 -m pip install --user --break-system-packages Pillow"

echo "== 6. Thu muc output/refs (o HOME, tranh o NTFS hay xoa) =="
mkdir -p "$HOME/imagegen_studio/out" "$HOME/imagegen_studio/refs"
echo "  out : $HOME/imagegen_studio/out"
echo "  refs: $HOME/imagegen_studio/refs"

echo "== 7. chmod +x =="
chmod +x Studio.sh start.sh login.sh autoupdate.sh imagegen_studio.py chatgpt-imagegen 2>/dev/null || true

echo "== 8. ARK_KEY (Seed-pro viet prompt) =="
if [ -f .env ] && grep -q '^ARK_KEY=' .env; then
  echo "  OK: da co ARK_KEY trong .env"
elif [ -t 0 ]; then
  echo "  Chua co ARK_KEY. Lay key: https://console.byteplus.com/ark"
  printf '  >> Paste ARK_KEY vao day roi Enter (bo trong de bo qua): '
  read -r _ARK
  _ARK="$(printf '%s' "$_ARK" | tr -d '[:space:]')"   # bo khoang trang thua
  _ARK="${_ARK#ARK_KEY=}"                              # lo paste ca dong "ARK_KEY=..." -> cat tien to
  if [ -n "$_ARK" ]; then
    printf '\nARK_KEY=%s\n' "$_ARK" >> .env            # nao truoc da chac chua co ARK_KEY -> chi them
    echo "  Da luu ARK_KEY vao .env (file nay nam trong .gitignore)."
  else
    echo "  Bo qua — nho tao .env voi ARK_KEY truoc khi gen."
  fi
else
  echo "  !! CHUA co ARK_KEY. Tao file .env trong thu muc nay, 1 dong:"
  echo "         ARK_KEY=ark-...(key BytePlus Ark cua ban)..."
  echo "     Lay key: https://console.byteplus.com/ark   (file .env da nam trong .gitignore)"
fi

echo "== 9. Dang nhap ChatGPT (codex) =="
if [ -f "$HOME/.codex/auth.json" ]; then
  echo "  OK: da co $HOME/.codex/auth.json"
else
  echo "  Chua dang nhap — chay: codex login   (hoac ./login.sh)"
fi

echo
echo "XONG. Chay:  ./start.sh   (mo http://127.0.0.1:8770)"
echo "  Can: (1) ARK_KEY trong .env  (2) codex da login."
