@echo off
REM 先装依赖（如果还没装）
call .venv\Scripts\activate
pip install PySide6 pyinstaller -q
REM 打包
pyinstaller --onefile --noconsole ^
    --name "LineDogPet" ^
    --add-data "assets;assets" ^
    --icon "assets/icon.ico" ^
    main.py
echo Build done: dist\LineDogPet.exe
pause
