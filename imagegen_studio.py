#!/usr/bin/env python3
"""Studio UI: gallery anh output o tren + bang dieu khien Seed-pro o duoi.

Seed-pro (BytePlus Ark) doc anh san pham + anh phu tro -> viet prompt mockup ->
gen thang bang CLI chatgpt-imagegen (codex). Khong con terminal/Claude.

  python3 imagegen_studio.py            # mo http://127.0.0.1:8770
  python3 imagegen_studio.py --port 9000 --out ~/anh_gen

Anh gen ra thu muc OUT se tu hien len gallery (poll moi 2s).
"""
import argparse
import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import glob
import sys
import time
import urllib.parse

from aiohttp import web

import seedprompt

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, "studio.html")
HOME = os.path.expanduser("~")

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif"}
IMG_EXT = set(MIME)

# source code cua Studio -> phat hien khi code doi de nhac restart
SRC = [os.path.join(ROOT, f) for f in ("imagegen_studio.py", "studio.html")]


def _src_mtime():
    return max((os.path.getmtime(f) for f in SRC if os.path.exists(f)), default=0)


async def index(request):
    return web.FileResponse(HTML)


async def media(request):
    """Phuc vu anh theo duong dan tuyet doi, chi trong cac ROOT cho phep."""
    p = os.path.realpath(urllib.parse.unquote(request.query.get("p", "")))
    if not any(p == r or p.startswith(r + os.sep) for r in request.app["ROOTS"]) \
            or not os.path.isfile(p):
        return web.Response(status=404, text="not found")
    ext = os.path.splitext(p)[1].lower()
    return web.FileResponse(p, headers={"Content-Type": MIME.get(ext, "application/octet-stream")})


async def reveal(request):
    """Mo thu muc chua anh bang file manager (xdg-open), chi trong ROOT cho phep."""
    p = os.path.realpath(urllib.parse.unquote(request.query.get("p", "")))
    if not any(p == r or p.startswith(r + os.sep) for r in request.app["ROOTS"]) \
            or not os.path.isfile(p):
        return web.Response(status=404, text="not found")
    d = os.path.dirname(p)
    if sys.platform == "win32":
        os.startfile(d)                       # noqa: S606 (Windows Explorer)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", d])
    return web.Response(text="ok")


async def delete(request):
    """Chuyen anh vao thung rac (.trash) thay vi xoa han -> Ctrl+Z khoi phuc duoc.
    Ghi log LIFO (trashpath<TAB>origpath) de /undo pop nguoc lai."""
    p = os.path.realpath(urllib.parse.unquote(request.query.get("p", "")))
    if not any(p == r or p.startswith(r + os.sep) for r in request.app["ROOTS"]) \
            or not os.path.isfile(p):
        return web.Response(status=404, text="not found")
    trash = request.app["TRASH"]
    os.makedirs(trash, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(p))
    dst = os.path.join(trash, stem + ext)
    n = 1
    while os.path.exists(dst):
        dst = os.path.join(trash, "%s_%d%s" % (stem, n, ext))
        n += 1
    shutil.move(p, dst)                       # shutil.move: chiu duoc khac o dia (NTFS->HOME)
    if os.path.exists(p + ".txt"):
        shutil.move(p + ".txt", dst + ".txt")  # dem prompt sidecar theo
    with open(request.app["TRASHLOG"], "a", encoding="utf-8") as f:
        f.write(dst + "\t" + p + "\n")
    return web.Response(text="ok")


async def undo(request):
    """Khoi phuc anh vua chuyen vao thung rac (LIFO)."""
    log = request.app["TRASHLOG"]
    try:
        with open(log, encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
    except OSError:
        lines = []
    while lines:
        dst, orig = lines.pop().split("\t", 1)
        if not os.path.exists(dst):
            continue                          # da bi don tay -> bo qua, thu cai truoc do
        try:
            os.makedirs(os.path.dirname(orig), exist_ok=True)
            shutil.move(dst, orig)
            if os.path.exists(dst + ".txt"):
                shutil.move(dst + ".txt", orig + ".txt")
        except OSError as e:
            return web.json_response({"restored": None, "err": str(e)})
        with open(log, "w", encoding="utf-8") as f:
            f.write("".join(l + "\n" for l in lines))
        return web.json_response({"restored": orig})
    with open(log, "w", encoding="utf-8") as f:  # het -> don sach log
        f.write("")
    return web.json_response({"restored": None})


async def version(request):
    """Bao cho UI biet code da doi so voi luc server khoi dong -> can restart."""
    return web.json_response({"stale": _src_mtime() > request.app["SRC_MTIME"]})


async def restart(request):
    """Khoi dong lai server (re-exec) de nap code moi."""
    async def _go():
        await asyncio.sleep(0.3)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    asyncio.ensure_future(_go())
    return web.Response(text="restarting")


def _gallery_roots(app):
    # ca thu muc studio (bat moi out*/ Claude tao) + out_*/output trong project
    studio_base = os.path.dirname(app["OUT"])
    return ([studio_base] + sorted(glob.glob(os.path.join(ROOT, "out*")))
            + [os.path.join(ROOT, "output")])


async def gallery(request):
    """Liet ke anh gen (de quy), moi nhat truoc. Bo qua thu muc refs (anh input)."""
    refs = os.path.realpath(request.app["REFS"])
    trash = os.path.realpath(request.app["TRASH"])
    seen, items = set(), []
    for root in _gallery_roots(request.app):
        if not os.path.isdir(root):
            continue
        for dp, dirs, files in os.walk(root):
            rp = os.path.realpath(dp)
            # anh keo vao (refs) va anh da xoa (.trash) khong hien tren gallery
            if rp == refs or rp.startswith(refs + os.sep) \
                    or rp == trash or rp.startswith(trash + os.sep):
                dirs[:] = []
                continue
            for fn in files:
                if os.path.splitext(fn)[1].lower() not in IMG_EXT:
                    continue
                fp = os.path.join(dp, fn)
                if fp in seen:
                    continue
                seen.add(fp)
                prompt = ""
                try:
                    with open(fp + ".txt", encoding="utf-8") as pf:
                        prompt = pf.read(2000).strip()
                except OSError:
                    pass
                try:
                    items.append({"name": fn, "mtime": os.path.getmtime(fp),
                                  "prompt": prompt,
                                  "url": "/media?p=" + urllib.parse.quote(fp)})
                except OSError:
                    pass
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return web.json_response(items[:300])


# ---------- Seed-pro viet prompt + gen anh (thay Claude) ----------
GEN_SEM = asyncio.Semaphore(4)   # codex backend gioi han 4 request song song


def _b64(s):
    return base64.b64decode(s.split(",")[-1])


def _write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def _next_set(base):
    """Ten set tang dan (seed_0001, 0002...) dua tren cac set da co trong base."""
    os.makedirs(base, exist_ok=True)
    nums = [int(m.group(1)) for d in os.listdir(base) if (m := re.match(r"seed_(\d+)$", d))]
    return "seed_%04d" % (1 + max(nums, default=0))


async def api_prompt(request):
    """body {main_b64, ref_b64s[], ref_labels[], request, count}
    -> luu anh vao refs/<set>/, goi Seed-pro, tra {prompts[], img_paths[], set, model, seconds, tokens}."""
    d = await request.json()
    if not d.get("main_b64"):
        return web.json_response({"error": "Chua chon anh san pham."}, status=400)
    main = _b64(d["main_b64"])
    refs = [_b64(s) for s in d.get("ref_b64s", [])]
    labels = d.get("ref_labels", [])
    req = (d.get("request") or "").strip()
    count = max(1, min(20, int(d.get("count", 6))))

    setname = _next_set(request.app["REFS"])
    sdir = os.path.join(request.app["REFS"], setname)
    os.makedirs(sdir, exist_ok=True)
    paths = [os.path.join(sdir, "01_product.png")]
    _write(paths[0], main)
    for i, b in enumerate(refs):
        p = os.path.join(sdir, "%02d_ref.png" % (i + 2))
        _write(p, b)
        paths.append(p)

    t0 = time.monotonic()
    try:
        prompts, model, tok = await seedprompt.write_prompts(main, refs, req, count, ref_labels=labels)
    except Exception as e:
        return web.json_response({"error": str(e)[:400]}, status=502)
    if not prompts:
        return web.json_response({"error": "Seed-pro khong tra ve prompt nao."}, status=502)
    return web.json_response({"prompts": prompts, "img_paths": paths, "set": setname,
                              "model": model, "seconds": round(time.monotonic() - t0, 1), "tokens": tok})


async def _gen_one(prompt, img_paths, out_path):
    args = [sys.executable, os.path.join(ROOT, "chatgpt-imagegen"), prompt]
    for p in img_paths[:10]:
        args += ["-i", p]
    args += ["-o", out_path, "--size", "1024x1024", "--backend", "codex", "--quiet"]
    async with GEN_SEM:
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await proc.communicate()
    fname = os.path.basename(out_path)
    if proc.returncode == 0 and os.path.isfile(out_path):
        _write(out_path + ".txt", prompt.encode("utf-8"))   # sidecar -> gallery hien prompt duoi anh
        return {"ok": True, "file": fname}
    err = (out or b"").decode("utf-8", "replace")[-300:]
    print("[gen] FAIL %s: %s" % (fname, err.replace("\n", " ")[-200:]), flush=True)
    return {"ok": False, "file": fname, "error": err}


async def _warm_codex_token():
    """Refresh/xoay token codex MOT LAN truoc batch song song. Tra None neu OK, hoac chuoi loi.

    Vi sao: CLI chi refresh khi gap 401. Neu access token het han, N tien trinh gen song song
    cung 401 -> cung goi refresh voi CUNG refresh_token. OAuth OpenAI xoay refresh_token (dung 1 lan)
    -> chi 1 tien trinh doi duoc, con lai 'refresh_token no longer valid' -> fail. Refresh truoc 1 lan
    (ghi access token moi vao auth.json) thi ca batch dung token con han, khong ai phai refresh nua.
    """
    proc = await asyncio.create_subprocess_exec(
        sys.executable, os.path.join(ROOT, "refresh_token.py"),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await proc.communicate()
    if proc.returncode != 0:
        return (out or b"").decode("utf-8", "replace").strip()[-200:]
    return None


_LOGIN_PROC = None   # tien trinh `codex login` dang chay (da mo trinh duyet) -> tranh mo trung


async def _codex_login():
    """Chay `codex login` khi refresh_token chet han: no tu mo trinh duyet cho user dang nhap lai.
    Fire-and-forget — khong doi login xong; user dang nhap tren browser roi bam Tao lai.
    Tra None neu da khoi dong (hoac dang chay), hoac chuoi loi neu khong tim thay codex."""
    global _LOGIN_PROC
    if _LOGIN_PROC is not None and _LOGIN_PROC.returncode is None:
        return None                                   # da co 1 login dang mo -> khong mo them
    codex = shutil.which("codex")                     # resolve dung .cmd tren Windows
    if not codex:
        return "khong tim thay 'codex' tren PATH (cai: npm i -g @openai/codex)"
    _LOGIN_PROC = await asyncio.create_subprocess_exec(
        codex, "login",
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    return None


AUTH_PATH = os.path.join(HOME, ".codex", "auth.json")


def _codex_status():
    """Han cua access token codex: decode claim 'exp' trong JWT (khong tra token ra ngoai).
    Tra {ok, remaining_min, expired, exp, last_refresh} hoac {ok:False, error}."""
    try:
        with open(AUTH_PATH, encoding="utf-8") as f:
            auth = json.load(f)
    except OSError:
        return {"ok": False, "error": "chua co ~/.codex/auth.json (chua codex login)"}
    except (ValueError, TypeError):
        return {"ok": False, "error": "auth.json hong"}
    tok = (auth.get("tokens") or {}).get("access_token") or ""
    exp = None
    parts = tok.split(".")
    if len(parts) == 3:   # JWT header.payload.signature
        try:
            pad = parts[1] + "=" * (-len(parts[1]) % 4)
            exp = json.loads(base64.urlsafe_b64decode(pad)).get("exp")
        except Exception:
            exp = None
    now = time.time()
    remaining = int((exp - now) // 60) if exp else None
    return {"ok": True, "exp": exp, "remaining_min": remaining,
            "expired": exp is not None and exp <= now, "last_refresh": auth.get("last_refresh")}


async def api_codex_status(request):
    return web.json_response(_codex_status())


async def api_codex_refresh(request):
    err = await _warm_codex_token()   # xoay token ngay (dung chung ham warm cua batch gen)
    st = _codex_status()
    if err:
        st["refresh_error"] = err
    return web.json_response(st)


async def api_gen(request):
    """body {prompts[], img_paths[], set} -> chay chatgpt-imagegen (codex) tung prompt, toi da 4 song song.
    Anh ghi vao OUT/<set>/NN.png (+ sidecar .txt) -> gallery tu hien. Tra tong ket ok/fail."""
    d = await request.json()
    prompts = [p.strip() for p in d.get("prompts", []) if p and p.strip()]
    img_paths = [p for p in d.get("img_paths", []) if os.path.isfile(p)]
    setname = os.path.basename((d.get("set") or "seedset").strip()) or "seedset"
    if not prompts:
        return web.json_response({"error": "Chua co prompt de gen."}, status=400)

    warm_err = await _warm_codex_token()   # xoay token 1 lan -> tranh dua nhau refresh khi song song
    if warm_err:
        login_err = await _codex_login()   # token chet han -> tu mo trinh duyet dang nhap lai
        if login_err:
            msg = "Token codex het han va khong tu mo dang nhap duoc (%s). Chay: codex login" % login_err
        else:
            msg = ("Token codex het han. Da mo trinh duyet de dang nhap lai — "
                   "dang nhap xong roi bam ✨ Tao bo anh lai.")
        return web.json_response({"error": msg}, status=502)

    out_dir = os.path.join(request.app["OUT"], setname)
    os.makedirs(out_dir, exist_ok=True)
    start = len(glob.glob(os.path.join(out_dir, "[0-9]*.png")))
    tasks = [_gen_one(p, img_paths, os.path.join(out_dir, "%02d.png" % (start + k + 1)))
             for k, p in enumerate(prompts)]
    results = await asyncio.gather(*tasks)
    ok = [r for r in results if r["ok"]]
    fail = [r for r in results if not r["ok"]]
    return web.json_response({"out_dir": out_dir, "ok": len(ok), "fail": len(fail),
                              "count": len(results), "failed": fail[:20]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--out", default=os.path.join(HOME, "imagegen_studio", "out"))
    ap.add_argument("--refs", default=os.path.join(HOME, "imagegen_studio", "refs"))
    a = ap.parse_args()

    out = os.path.abspath(os.path.expanduser(a.out))
    refs = os.path.abspath(os.path.expanduser(a.refs))
    os.makedirs(out, exist_ok=True)
    os.makedirs(refs, exist_ok=True)

    # anh mockup that thuong 1-8MB, base64 phinh them 33% -> noi gioi han body.
    app = web.Application(client_max_size=100 * 1024 * 1024)
    app["OUT"], app["REFS"] = out, refs
    app["TRASH"] = os.path.join(os.path.dirname(out), ".trash")
    app["TRASHLOG"] = os.path.join(app["TRASH"], "undo_log.tsv")
    app["SRC_MTIME"] = _src_mtime()
    # cac goc duoc phep phuc vu anh: ca thu muc studio (chua out*/refs) + project
    app["ROOTS"] = [os.path.realpath(p) for p in (os.path.dirname(out), ROOT)]
    app.add_routes([
        web.get("/", index),
        web.get("/gallery", gallery),
        web.post("/prompt", api_prompt),
        web.post("/gen", api_gen),
        web.get("/codex_status", api_codex_status),
        web.post("/codex_refresh", api_codex_refresh),
        web.get("/media", media),
        web.get("/reveal", reveal),
        web.get("/delete", delete),
        web.post("/undo", undo),
        web.get("/version", version),
        web.post("/restart", restart),
    ])
    print("Studio: http://127.0.0.1:%d   (out=%s)" % (a.port, out))
    web.run_app(app, host="127.0.0.1", port=a.port, print=None)


if __name__ == "__main__":
    main()
