@echo off
setlocal
cd /d "%~dp0"
title Instalar Rastro Analitico de Velocidade

echo ======================================================
echo  INSTALACAO DO RASTRO ANALITICO DE VELOCIDADE
echo ======================================================
echo.

where py >nul 2>&1
if errorlevel 1 goto testar_python
py --version >nul 2>&1
if not errorlevel 1 goto usar_py

:testar_python
where python >nul 2>&1
if errorlevel 1 goto instalar_python
python --version >nul 2>&1
if not errorlevel 1 goto usar_python

:instalar_python
echo Python nao encontrado. Tentando instalar...
where winget >nul 2>&1
if errorlevel 1 goto sem_winget
winget install --id Python.Python.3.13 -e --source winget --accept-source-agreements --accept-package-agreements

set "PATH=%LocalAppData%\Programs\Python\Python313;%LocalAppData%\Programs\Python\Python313\Scripts;%PATH%"
where py >nul 2>&1
if errorlevel 1 goto retestar_python
py --version >nul 2>&1
if not errorlevel 1 goto usar_py
:retestar_python
where python >nul 2>&1
if errorlevel 1 goto reiniciar_instalador
python --version >nul 2>&1
if not errorlevel 1 goto usar_python

:reiniciar_instalador
echo.
echo O Python foi instalado, mas o Windows ainda nao atualizou o caminho.
echo Feche esta janela e execute INSTALAR.bat novamente.
pause
exit /b 1

:usar_py
set "PYTHON_CMD=py"
goto python_pronto

:usar_python
set "PYTHON_CMD=python"
goto python_pronto

:sem_winget
echo O instalador do Windows winget nao foi encontrado.
echo Instale o Python em https://www.python.org/downloads/windows/
pause
exit /b 1

:python_pronto
echo Instalando biblioteca de imagem...
%PYTHON_CMD% -m pip install --upgrade Pillow
if errorlevel 1 goto erro_pillow

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" goto concluido
where tesseract >nul 2>&1
if not errorlevel 1 goto concluido

echo Instalando leitor de texto Tesseract OCR...
where winget >nul 2>&1
if errorlevel 1 goto erro_tesseract
winget install --id UB-Mannheim.TesseractOCR -e --source winget --accept-source-agreements --accept-package-agreements

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" goto concluido
where tesseract >nul 2>&1
if not errorlevel 1 goto concluido
goto erro_tesseract

:erro_pillow
echo.
echo Nao foi possivel instalar a biblioteca Pillow.
pause
exit /b 1

:erro_tesseract
echo.
echo O Tesseract OCR nao foi localizado.
echo Instale o Tesseract OCR e execute este instalador novamente.
pause
exit /b 1

:concluido
echo.
echo ======================================================
echo  INSTALACAO CONCLUIDA
echo ======================================================
echo Agora abra o arquivo ABRIR_PROGRAMA.bat
pause
exit /b 0
