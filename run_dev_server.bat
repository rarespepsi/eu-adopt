@echo off
title EU-Adopt Django dev
cd /d "%~dp0"
echo.
echo === EU-Adopt: server local ===
echo Browser: http://127.0.0.1:8000/
echo Din alt PC in retea: http://IP-ul-acestui-PC:8000/
echo (opresti cu Ctrl+C)
echo.
python manage.py runserver 0.0.0.0:8000
pause
