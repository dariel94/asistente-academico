@echo off
start "" "%ProgramFiles%\Git\bin\bash.exe" -c "cd '%~dp0' && ./start.sh; read -p 'Presiona Enter para cerrar...'"
