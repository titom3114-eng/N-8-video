@echo off
REM Lance le pilote automatique (à programmer chaque matin dans le Planificateur de tâches Windows)
cd /d "%~dp0"
if not exist journaux mkdir journaux
python automate.py >> "journaux\%date:~-4%-%date:~3,2%-%date:~0,2%.txt" 2>&1
