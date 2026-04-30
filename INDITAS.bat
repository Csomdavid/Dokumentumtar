@echo off
echo A Dokumentumtar inditasa...

if not exist .\.venv\Scripts\python.exe (
    echo HIBA: A virtualis kornyezet nem talalhato!
    echo Kerem, eloszor futtassa a TELEPITES.bat fajlt a rendszer inicializalasahoz.
    pause
    exit /b
)

start http://127.0.0.1:8000

.\.venv\Scripts\python.exe manage.py runserver
pause