#!/usr/bin/env python3
"""Proactively refresh ~/.codex/auth.json tokens before they expire.
Run every ~20-30 minutes (Linux: cron/systemd timer; Windows: Task Scheduler).
"""
import json, os, shutil, sys, time, subprocess, urllib.parse, urllib.request, urllib.error
from pathlib import Path


def notify(title: str, message: str):
    """Best-effort desktop notification. No extra deps, never raises."""
    try:
        if sys.platform.startswith("win"):
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms;"
                "$n = New-Object System.Windows.Forms.NotifyIcon;"
                "$n.Icon = [System.Drawing.SystemIcons]::Information;"
                "$n.Visible = $true;"
                f"$n.ShowBalloonTip(10000, '{title}', '{message}', "
                "[System.Windows.Forms.ToolTipIcon]::Warning);"
                "Start-Sleep -Seconds 12; $n.Dispose()"
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
        elif sys.platform == "darwin" and shutil.which("osascript"):
            subprocess.Popen(
                ["osascript", "-e",
                 f'display notification "{message}" with title "{title}"'])
        elif shutil.which("notify-send"):  # Linux desktops
            subprocess.Popen(["notify-send", "-u", "critical", title, message])
        # No GUI (headless server / cron) -> the print() below is the notice.
    except Exception:
        pass

AUTH_PATH = Path.home() / ".codex" / "auth.json"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
TOKEN_URL = "https://auth.openai.com/oauth/token"


def load_auth():
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def save_auth(auth):
    tmp = AUTH_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(auth, indent=2), encoding="utf-8")
    os.replace(tmp, AUTH_PATH)


def refresh(refresh_token):
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "openid profile email",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    if not AUTH_PATH.exists():
        print("ERROR: ~/.codex/auth.json not found. Run `codex login` first.")
        return 1

    auth = load_auth()
    tokens = auth.get("tokens", {})
    rt = tokens.get("refresh_token")

    if not rt:
        print("ERROR: No refresh_token found. Run `codex login`.")
        return 1

    try:
        result = refresh(rt)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if "invalid_grant" in body or "refresh_token_invalidated" in body:
            msg = "Phien lam viec da ket thuc. Mo terminal va chay: codex login"
            print(f"ERROR: refresh_token het han -- {msg}")
            notify("chatgpt-imagegen: Can dang nhap lai", msg)
        else:
            print(f"ERROR: HTTP {e.code} -- {body[:200]}")
        return 1

    if result.get("access_token"):
        tokens["access_token"] = result["access_token"]
    if result.get("refresh_token"):
        tokens["refresh_token"] = result["refresh_token"]
    if result.get("id_token"):
        tokens["id_token"] = result["id_token"]
    auth["tokens"] = tokens
    auth["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_auth(auth)
    print(f"OK: tokens refreshed at {auth['last_refresh']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
