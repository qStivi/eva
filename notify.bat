@echo off
REM Simple notification - call from anywhere
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\steph\notify-simple.ps1" -Message "%*"
