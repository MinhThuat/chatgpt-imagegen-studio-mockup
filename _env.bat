@echo off
REM Nap tools portable da tai (neu co) vao PATH cho phien hien tai.
REM Duoc `call` tu setup.bat va Studio.bat. Neu may da co san python/node/git
REM tren PATH thi cac dong duoi khong lam gi (thu muc tools khong ton tai).
set "TOOLS=%USERPROFILE%\imagegen_studio\tools"
if exist "%TOOLS%\python\python.exe" set "PATH=%TOOLS%\python;%TOOLS%\python\Scripts;%PATH%"
if exist "%TOOLS%\node\node.exe"     set "PATH=%TOOLS%\node;%PATH%"
if exist "%TOOLS%\git\cmd\git.exe"   set "PATH=%TOOLS%\git\cmd;%TOOLS%\git\bin;%TOOLS%\git\usr\bin;%TOOLS%\git\mingw64\bin;%PATH%"
