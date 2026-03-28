@echo off
for /f "tokens=2" %%a in ('wmic process where "CommandLine like '%%main.py%%'" get ProcessId ^| findstr [0-9]') do taskkill /f /pid %%a
