@echo off
REM Setup Imagegen Studio cho Windows. Chay 1 lan. KHONG can admin:
REM tu tai Python + Node + Git (Git Bash) ban portable vao %USERPROFILE%\imagegen_studio\tools.
REM Can Windows 10 1803+ (co san curl.exe + tar.exe). CPU x64.
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "TOOLS=%USERPROFILE%\imagegen_studio\tools"
if not exist "%TOOLS%" mkdir "%TOOLS%"
call "%~dp0_env.bat"

REM --- kiem tra dieu kien tien quyet cua chinh script setup ---
where tar  >nul 2>&1 || echo   !! Thieu tar.exe  - can Windows 10 1803+ (chay Windows Update).
where curl >nul 2>&1 || echo   !! Thieu curl.exe - can Windows 10 1803+ (chay Windows Update).
if /I not "%PROCESSOR_ARCHITECTURE%"=="AMD64" echo   !! CPU khong phai x64 - phan tu tai chi ho tro x64, hay cai python/node/git tay.

echo == 1. Python 3 ==
where python >nul 2>&1 && (echo   da co: & python --version) || call :getpython

echo == 2. Node + npm ==
where npm >nul 2>&1 && (echo   da co npm) || call :getnode

echo == 3. Git + Git Bash ==
where bash >nul 2>&1 && (echo   da co bash) || call :getgit

REM nap lai PATH voi tools vua tai
call "%~dp0_env.bat"

echo == 4. pip: aiohttp (server) ==
python -m pip install "aiohttp>=3.9" || python -m pip install --user "aiohttp>=3.9"

echo == 5. codex (npm global) ==
where codex >nul 2>&1 && echo   da co codex || npm install -g @openai/codex

echo == 6. Thu muc output/refs ==
if not exist "%USERPROFILE%\imagegen_studio\out"  mkdir "%USERPROFILE%\imagegen_studio\out"
if not exist "%USERPROFILE%\imagegen_studio\refs" mkdir "%USERPROFILE%\imagegen_studio\refs"
echo   out : %USERPROFILE%\imagegen_studio\out
echo   refs: %USERPROFILE%\imagegen_studio\refs

echo == 7. ARK_KEY (.env) cho Seed-pro ==
if not exist "%~dp0.env" (
  echo   !! Chua co .env - Seed-pro can ARK_KEY. Tao file .env trong thu muc nay voi dong:  ARK_KEY=ark-...
) else (
  findstr /b /c:"ARK_KEY=" "%~dp0.env" >nul 2>&1 && (echo   OK: co ARK_KEY) || (echo   !! .env chua co dong ARK_KEY=...)
)

echo == 8. Dang nhap ChatGPT (codex) ==
if exist "%USERPROFILE%\.codex\auth.json" (echo   OK: da co auth.json) else (echo   Chua dang nhap - chay: codex login)

echo.
echo XONG. Chay:  Studio.bat
goto :eof


:getpython
echo   tai Python standalone (portable, khong can admin)...
call :download "https://github.com/astral-sh/python-build-standalone/releases/download/20241206/cpython-3.12.8+20241206-x86_64-pc-windows-msvc-install_only.tar.gz" "%TEMP%\imgstudio_py.tar.gz" || (echo   !! tai Python that bai & goto :eof)
tar -xf "%TEMP%\imgstudio_py.tar.gz" -C "%TOOLS%"
del "%TEMP%\imgstudio_py.tar.gz" 2>nul
REM tao alias python3.exe -> de script gen (dung `python3`) chay duoc trong Git Bash
if exist "%TOOLS%\python\python.exe" copy /y "%TOOLS%\python\python.exe" "%TOOLS%\python\python3.exe" >nul
echo   Python -^> %TOOLS%\python
goto :eof


:getnode
echo   tai Node (portable, khong can admin)...
call :download "https://nodejs.org/dist/v22.11.0/node-v22.11.0-win-x64.zip" "%TEMP%\imgstudio_node.zip" || (echo   !! tai Node that bai & goto :eof)
tar -xf "%TEMP%\imgstudio_node.zip" -C "%TOOLS%"
del "%TEMP%\imgstudio_node.zip" 2>nul
if exist "%TOOLS%\node" rmdir /s /q "%TOOLS%\node"
move "%TOOLS%\node-v22.11.0-win-x64" "%TOOLS%\node" >nul
REM npm global -> vao chinh thu muc node (khong can admin)
"%TOOLS%\node\npm.cmd" config set prefix "%TOOLS%\node" >nul 2>&1
echo   Node -^> %TOOLS%\node
goto :eof


:getgit
echo   tai PortableGit (Git Bash: bash/xargs/find, khong can admin)...
call :download "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/PortableGit-2.47.1-64-bit.7z.exe" "%TEMP%\imgstudio_git.exe" || (echo   !! tai Git that bai & goto :eof)
"%TEMP%\imgstudio_git.exe" -o"%TOOLS%\git" -y >nul
del "%TEMP%\imgstudio_git.exe" 2>nul
echo   Git -^> %TOOLS%\git
goto :eof


:download
REM %1=url  %2=file dich. Thu curl truoc, roi PowerShell. exit /b 0 neu OK.
curl -fL "%~1" -o "%~2" 2>nul && exit /b 0
powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol='Tls12';Invoke-WebRequest -Uri '%~1' -OutFile '%~2'}catch{exit 1}" && exit /b 0
exit /b 1
