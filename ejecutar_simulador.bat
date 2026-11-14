@echo off
title Simulador de Planificacion y Memoria - TPI SO
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py interfaz.py) else (python interfaz.py)
pause
