# Imagegen Studio — bản standalone

## Đây là gì
Bộ công cụ tạo ảnh mockup sản phẩm hàng loạt bằng AI (ChatGPT image generation), có **giao diện web Studio** thay cho terminal trần. Người dùng mô tả bằng tiếng Việt → bạn (Claude) hỏi lại cho rõ → viết prompt tiếng Anh → chạy CLI `chatgpt-imagegen` để gen.

> **Nền tảng: Linux.** Chỉ viết script **bash (`.sh`)**, KHÔNG viết PowerShell/`.bat`.
> **`python3`** chứ không phải `python` (máy này không có alias `python`).

## Giao diện Studio hoạt động ra sao
Chạy `./Studio.sh` → mở `http://127.0.0.1:8770`. Trang chia 2 phần:
- **Trên = gallery**: ảnh gen ra tự hiện lên (poll mỗi 2s), mới nhất trước. Nút **＋ New** ẩn ảnh cũ (chỉ ẩn khỏi giao diện, KHÔNG xoá file; mốc lưu trong trình duyệt).
- **Dưới = bảng Seed-pro** (thay cho terminal Claude cũ): nạp **Ảnh sản phẩm** + **Ảnh phụ trợ** (kéo-thả / dán Ctrl+V / bấm chọn) → gõ yêu cầu tiếng Việt + số lượng → bấm **✨ Tạo bộ ảnh**. Seed-pro (BytePlus Ark, model `seed-2-0-pro-260328`) tự đọc ảnh + viết N prompt tiếng Anh đa dạng rồi gen thẳng bằng CLI `chatgpt-imagegen` (codex). **Không còn terminal/Claude trong Studio.**
- **Nạp ảnh reference**: kéo-thả ảnh/folder, hoặc dán (Ctrl+V, kể cả "Copy image" từ web) vào ô "Ảnh sản phẩm" (1 ảnh chính) hoặc "Ảnh phụ trợ" (logo/màu vải…, nhiều ảnh). Ctrl+Z khôi phục ảnh vừa xoá khỏi gallery.

## ⚡ QUAN TRỌNG NHẤT: xuất ảnh gen vào đâu
Khi chạy trong Studio, biến môi trường **`$IMAGEGEN_OUT`** được set sẵn (mặc định `~/imagegen_studio/out`).

**LUÔN xuất ảnh gen vào `$IMAGEGEN_OUT` hoặc thư mục con của nó** — ví dụ `$IMAGEGEN_OUT/ten_set/` — để ảnh **tự hiện lên gallery**. Gallery theo dõi cả thư mục `~/imagegen_studio/` (mọi folder `out*` trong đó, TRỪ `refs/`). Nếu xuất ra chỗ khác (vd thư mục project), ảnh sẽ KHÔNG hiện.

```bash
OUT="${IMAGEGEN_OUT:-$HOME/imagegen_studio/out}/ornament_set1"
mkdir -p "$OUT"
```

Không xuất ảnh ra thư mục chứa code này (ổ `/mnt/...` NTFS hay tự xoá file). Dùng `$IMAGEGEN_OUT` (nằm ở HOME, an toàn).

## Mẫu chuẩn script gen ảnh (bash)
Chạy song song **tối đa 4** request (`xargs -P 4` — giới hạn của codex backend). Mỗi ảnh mất ~60-150 giây.

```bash
#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"

CLI="./chatgpt-imagegen"
SRC="$HOME/imagegen_studio/refs/ten_folder_ref"      # folder ref user kéo vào
OUT="${IMAGEGEN_OUT:-$HOME/imagegen_studio/out}/ten_set"
mkdir -p "$OUT"

PROMPT="Mo ta anh can gen bang tieng Anh, chi tiet..."

gen_one() {
  local in="$1"
  local dst="$OUT/$(basename "$in")"
  echo "start: $(basename "$in")"
  python3 "$CLI" "$PROMPT" -i "$in" -o "$dst" \
    --size 1024x1024 --backend codex --quiet \
    && printf '%s\n' "$PROMPT" > "$dst.txt"   # sidecar -> gallery hien prompt duoi anh
}
export -f gen_one
export PROMPT OUT CLI

find "$SRC" -maxdepth 1 -name '*.png' -print0 \
  | xargs -0 -P 4 -I {} bash -c 'gen_one "$@"' _ {}

echo "done -> $OUT"
```

Sau khi tạo: `chmod +x run_xxx.sh` rồi chạy `bash run_xxx.sh` (auto mode nên không cần bấm duyệt).

## Tham số CLI hay dùng
```
python3 ./chatgpt-imagegen "prompt" -i ref.png -o out.png --size 1024x1024 --backend codex --quiet
```
- `-i` : ảnh tham chiếu (lặp lại nhiều lần được)
- `-o` : file output
- `--size` : `1024x1024` (khuyến nghị)
- `--backend codex` : dùng session ChatGPT đã đăng nhập
- `--quiet` : ít log

CLI chỉ dùng thư viện chuẩn Python — không cần cài gì.

## Backend & auth
- Dùng **codex backend** (session ChatGPT đã login). File auth: `~/.codex/auth.json` (dùng chung toàn máy).
- CLI **tự refresh access token mỗi lần gen** (dùng `refresh_token` trong `auth.json`) — không cần cron/vòng nền.
- Chỉ khi `refresh_token` **chết hẳn** CLI mới báo `run codex login again` / `token refresh failed`. Lúc đó bảo người dùng bấm chạy **`./login.sh`** (nó check codex đã cài + chạy `codex login`), rồi gen lại.
- Ảnh có thể ra 1254×1254 thay vì 2048 → giới hạn subscription, không đổi được.

## Quy trình dùng (trên bảng Seed-pro, không cần Claude)
1. Nạp **Ảnh sản phẩm** (bắt buộc) + **Ảnh phụ trợ** (tuỳ chọn) vào 2 ô — kéo-thả / dán / bấm chọn.
2. Gõ **Yêu cầu** tiếng Việt (vd "bộ mockup cốc sứ in hình thú cưng, phòng studio sạch") + **Số lượng**.
3. Bấm **✨ Tạo bộ ảnh**: Seed-pro viết N prompt tiếng Anh đa dạng → gen thẳng (tối đa 4 song song). Prompt hiện read-only, KHÔNG sửa tay.
4. Ảnh lưu vào `~/imagegen_studio/out/seed_NNNN/` (kèm sidecar `.txt` chứa prompt) và tự hiện lên gallery.

Logic viết prompt nằm ở `seedprompt.py` (khung `MOCKUP_TASK`); server gọi CLI `chatgpt-imagegen` để gen. Key `ARK_KEY` đặt trong `.env` ở thư mục này.

## File trong folder này
- `imagegen_studio.py` — server Studio (terminal↔web + gallery + upload). Không sửa trừ khi cần.
- `studio.html` — giao diện.
- `Studio.sh` — chạy Studio.
- `chatgpt-imagegen` — CLI gen ảnh (Python, không sửa).
- `refresh_token.py` — tự refresh token codex.
- `setup.sh` — cài đặt 1 lần (aiohttp + thư mục + chmod).
- `requirements.txt` — chỉ `aiohttp` cần cho Studio (phần Trello không dùng ở đây).

## Cài lần đầu
```
./setup.sh      # cài aiohttp, tạo ~/imagegen_studio/{out,refs}
./Studio.sh     # mở http://127.0.0.1:8770
```
