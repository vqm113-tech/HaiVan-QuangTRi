@echo off
REM ==========================================
REM desktop\build_exe.bat
REM Đóng gói ứng dụng thành file .exe — CHẠY TRÊN WINDOWS, từ thư mục desktop\
REM ==========================================

echo === Cai thu vien can thiet ===
pip install -r ..\requirements.txt
pip install -r requirements-desktop.txt

echo.
echo === Dong goi thanh .exe (co the mat 2-5 phut) ===
pyinstaller HaiVan.spec --noconfirm

echo.
echo === XONG ===
echo File .exe nam tai: desktop\dist\HaiVanQuangTri\HaiVanQuangTri.exe
echo Copy toan bo thu muc "dist\HaiVanQuangTri" sang may khac neu can (KHONG chi copy rieng file .exe).
pause
