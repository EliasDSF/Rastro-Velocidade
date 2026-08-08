@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Instalar Rastro Analitico de Velocidade

echo 
echo  INSTALACAO DO RASTRO ANALITICO DE VELOCIDADE
echo 
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

echo.
echo Verificando o Tesseract OCR...
call :localizar_tesseract
if defined TESSERACT_EXE goto concluido

echo Tesseract OCR nao encontrado. Tentando instalar...
echo.

where winget >nul 2>&1
if errorlevel 1 goto erro_tesseract

winget install --id UB-Mannheim.TesseractOCR -e --source winget --accept-source-agreements --accept-package-agreements

echo.
echo Aguardando conclusao da instalacao...
timeout /t 5 /nobreak >nul 2>&1

for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "PATH=%%b;!PATH!"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "PATH=%%b;!PATH!"

echo Verificando novamente o Tesseract OCR...
call :localizar_tesseract
if defined TESSERACT_EXE goto concluido
goto erro_tesseract

:localizar_tesseract
set "TESSERACT_EXE="

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    set "TESSERACT_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe"
    goto :eof
)

if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    set "TESSERACT_EXE=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    goto :eof
)

if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (
    set "TESSERACT_EXE=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
    goto :eof
)

if exist "C:\Tesseract-OCR\tesseract.exe" (
    set "TESSERACT_EXE=C:\Tesseract-OCR\tesseract.exe"
    goto :eof
)

where tesseract >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%T in ('where tesseract 2^>nul') do (
        if exist "%%T" (
            set "TESSERACT_EXE=%%T"
            goto :eof
        )
    )
)

goto :eof

:erro_pillow
echo.
echo Nao foi possivel instalar a biblioteca Pillow.
pause
exit /b 1

:erro_tesseract
echo.
echo O Tesseract OCR nao foi localizado.
echo.
echo Verifique manualmente se algum destes arquivos existe:
echo   C:\Program Files\Tesseract-OCR\tesseract.exe
echo   C:\Program Files (x86)\Tesseract-OCR\tesseract.exe
echo   %LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe
echo   C:\Tesseract-OCR\tesseract.exe
echo.
echo Se existir, execute novamente este instalador.
pause
exit /b 1

:concluido
echo.
echo Tesseract OCR encontrado em:
echo %TESSERACT_EXE%
echo.

"%TESSERACT_EXE%" --version

echo.
echo 
echo  INSTALACAO CONCLUIDA
echo 
echo Agora abra o arquivo ABRIR_PROGRAMA.bat
pause
exit /b 0
