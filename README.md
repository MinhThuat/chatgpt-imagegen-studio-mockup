# Imagegen Studio

Gen ảnh mockup sản phẩm hàng loạt bằng AI (ChatGPT image gen), UI web + terminal Claude. Nền tảng **Linux**.

## Dùng (bấm 1 cái)

```bash
git clone <URL-REPO> imagegen-studio
cd imagegen-studio
./start.sh          # lần đầu tự setup, sau đó tự mở http://127.0.0.1:8770
```

`start.sh` lần đầu chạy `setup.sh`: tự cài **python3, node/npm, claude, codex, aiohttp** vào `~/.local`
(**không cần sudo** — dùng bản prebuilt standalone), cái nào có sẵn thì bỏ qua. Rồi mở Studio.

Máy chỉ cần có `git` + `curl` (hoặc `wget`) và kết nối mạng.
Sau khi cài xong, đăng nhập ChatGPT một lần: `codex login` (hoặc `./login.sh`).

## Tự cập nhật

Studio tự chạy `autoupdate.sh` ở nền: mỗi 60s `git fetch` + `git reset --hard` về đúng remote.
Có code mới sẽ in `[autoupdate] ...` — chạy lại `./Studio.sh` để áp dụng.

> Repo chỉ chứa code; ảnh gen nằm ở `~/imagegen_studio/` (ngoài repo) nên hard-reset không mất ảnh.
> **Đừng sửa file trong repo** — sẽ bị auto-update ghi đè.
