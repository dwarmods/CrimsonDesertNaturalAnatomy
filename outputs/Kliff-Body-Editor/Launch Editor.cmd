@echo off
setlocal
cd /d "%~dp0"
set "EDITOR_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%EDITOR_PYTHON%" (
  "%EDITOR_PYTHON%" editor.py
) else (
  py -3 editor.py
)
if errorlevel 1 pause
