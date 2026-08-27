@echo off
REM Lance import_upcoming_matches.py depuis ce dossier, quel que soit
REM l'endroit où ce fichier est copié (%~dp0 = dossier de ce .bat lui-même).
REM Toute la sortie (y compris les erreurs) part dans logs\auto_run.log,
REM pour pouvoir vérifier après coup que ça a bien tourné.
cd /d "%~dp0"
if not exist logs mkdir logs
echo ---------------------------------------------- >> logs\auto_run.log
echo %date% %time% >> logs\auto_run.log

REM Utilise explicitement le python de la venv (celui qui a xgboost/pymysql
REM installes) plutot que "python" tout court : le Planificateur de taches
REM Windows execute ce .bat avec un environnement minimal qui ne reprend pas
REM forcement le PATH modifie par l'activation manuelle de la venv dans un
REM terminal - sans ce chemin explicite, la tache planifiee risquerait de
REM tourner avec un python different (ou absent), voir AUTOMATISATION.md.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" import_upcoming_matches.py >> logs\auto_run.log 2>&1
) else (
    echo ATTENTION : .venv\Scripts\python.exe introuvable, repli sur "python" du PATH. >> logs\auto_run.log
    python import_upcoming_matches.py >> logs\auto_run.log 2>&1
)