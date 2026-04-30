@echo off
setlocal enabledelayedexpansion

echo [1/6] Virtualis kornyezet ellenorzese...
if not exist .venv (
    python -m venv .venv
)

echo [2/6] .env fajl ellenorzese es biztonsagi kulcs generalasa...
if not exist .env (
    for /f "delims=" %%a in ('powershell -Command "[Guid]::NewGuid().ToString()"') do set "RND_KEY=%%a"
    echo SECRET_KEY=!RND_KEY! > .env
    echo APP_ENV=dev >> .env
    echo --- Uj .env fajl letrehozva egyedi, biztonsagos kulccsal. ---
) else (
    echo --- A .env fajl mar letezik, nem modositjuk. ---
)

echo [3/6] Csomagok telepitese (ez eltarthat egy ideig)...
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

echo [4/6] Adatbazis es Felhasznalok beallitasa...
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe init_db.py

echo [5/6] Apache konfiguracio automatikus generalasa...
set "CURRENT_DIR=%~dp0"
set "CURRENT_DIR=%CURRENT_DIR:\=/%"
set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"

powershell -Command "(Get-Content '%~dp0deployment\dokumentumtar_apache.conf.template') -replace '{PROJECT_ROOT}', '%CURRENT_DIR%' | Set-Content '%~dp0deployment\dokumentumtar.conf'"

echo [6/6] KESZ! A telepites sikeres.
echo -------------------------------------------------------
echo A rendszer felismerte az utvonalat: %CURRENT_DIR%
echo Az Apache konfiguracio elkeszult: deployment/dokumentumtar.conf
echo A tesztfiokok (root_admin, admin_tamas, szabo_anna) elerhetoek.
echo -------------------------------------------------------
echo Most mar futtathatja az INDITAS.bat fajlt.
pause