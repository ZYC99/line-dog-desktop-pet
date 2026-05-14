@echo off
setlocal

set "PYTHON=.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Missing local virtual environment: %PYTHON%
    echo This script is only for maintainers with a prepared .venv.
    echo End users should download LineDogPet.exe from GitHub Releases.
    exit /b 1
)

"%PYTHON%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo PyInstaller is not installed in .venv.
    echo This script does not install dependencies. Use GitHub Actions for release builds.
    exit /b 1
)

"%PYTHON%" -m PyInstaller --onefile --noconsole ^
    --name "LineDogPet" ^
    --add-data "assets;assets" ^
    main.py

if errorlevel 1 exit /b %errorlevel%

echo Build done: dist\LineDogPet.exe
