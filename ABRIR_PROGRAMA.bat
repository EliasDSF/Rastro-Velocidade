@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 goto testar_python
py --version >nul 2>&1
if not errorlevel 1 goto abrir_py

:testar_python
where python >nul 2>&1
if errorlevel 1 goto nao_instalado
python --version >nul 2>&1
if not errorlevel 1 goto abrir_python

:nao_instalado
echo Execute primeiro o arquivo INSTALAR.bat
pause
exit /b 1

:abrir_py
py programa.py
goto terminou

:abrir_python
python programa.py

:terminou
if errorlevel 1 pause
exit /b
