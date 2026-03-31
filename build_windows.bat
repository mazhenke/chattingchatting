@echo off
echo === Building Anonymous Chat Desktop Client for Windows ===

pip install pywebview pyinstaller

pyinstaller --onefile --windowed --name anonchat ^
    desktop.py

echo.
echo Build complete! Binary at: dist\anonchat.exe
echo Run with: dist\anonchat.exe
echo Reconfigure server: dist\anonchat.exe --reconfigure
