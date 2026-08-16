@echo off
REM ==========================================
REM desktop\run_app.bat
REM Cach NHANH NHAT de co "ung dung desktop" ma KHONG can build .exe:
REM tao shortcut tro toi file nay ngoai Desktop, double-click la chay -
REM khong can PyInstaller, khong can dong goi, chi can may da cai Python
REM va cac thu vien trong requirements.txt.
REM ==========================================

cd /d "%~dp0\.."
echo Dang khoi dong He thong Du bao Hai van Quang Tri...
streamlit run app.py
pause
