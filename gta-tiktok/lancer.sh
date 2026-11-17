#!/usr/bin/env bash
# Lance le pilote automatique (à programmer chaque matin avec crontab -e, voir LISEZMOI.md)
cd "$(dirname "$0")" || exit 1
mkdir -p journaux
python3 automate.py >> "journaux/$(date +%Y-%m-%d).txt" 2>&1
