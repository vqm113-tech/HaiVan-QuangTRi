# Đóng gói thành ứng dụng Desktop / file .exe

⚠️ **Quan trọng**: Toàn bộ file trong thư mục này được viết trong môi trường
Linux không cài được Streamlit/PyInstaller/pywebview để test trực tiếp —
logic đã được viết cẩn thận theo đúng cách làm chuẩn (rất phổ biến, nhiều
người đã dùng cách này), nhưng **bạn cần tự thử trên máy Windows thật**
trước khi dùng chính thức. Có 2 cách, từ dễ đến khó:

## Cách 1 (khuyên dùng trước): Shortcut chạy nhanh — không cần build gì cả

Không tạo ra file `.exe` thật, nhưng cho trải nghiệm "double-click để mở
ứng dụng" giống hệt — và chắc chắn chạy được nếu `streamlit run app.py`
bình thường đã chạy được trên máy bạn.

1. Đảm bảo đã cài Python + `pip install -r requirements.txt` (như bình thường).
2. Double-click `desktop/create_shortcut.ps1` → chọn "Run with PowerShell".
   (Nếu Windows chặn chạy script: mở PowerShell, gõ
   `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`, rồi thử lại.)
3. Sẽ có shortcut **"Hệ thống Dự báo Hải văn Quảng Trị"** ngoài Desktop —
   double-click để mở (tự mở trình duyệt tới ứng dụng).

## Cách 2: Build thành file .exe thật (cửa sổ desktop riêng, không qua trình duyệt)

1. Mở PowerShell/cmd tại thư mục gốc dự án (`HaiVan/`).
2. Chạy:
   ```
   cd desktop
   build_exe.bat
   ```
3. Đợi 2-5 phút. File `.exe` nằm tại `desktop/dist/HaiVanQuangTri/HaiVanQuangTri.exe`.
4. Chạy thử file `.exe` đó — sẽ tự mở 1 cửa sổ ứng dụng riêng (nhờ
   `pywebview`), không phải tab trình duyệt.
5. Muốn có shortcut ngoài Desktop: chạy lại `create_shortcut.ps1` (bước ở
   Cách 1) — script tự nhận ra đã có `.exe` và trỏ shortcut tới đó.

### Lưu ý khi build .exe

- **Copy cả thư mục `dist/HaiVanQuangTri/`** khi chuyển sang máy khác,
  không chỉ copy mỗi file `.exe` — PyInstaller đóng gói kèm nhiều file phụ
  trợ trong cùng thư mục.
- Nếu build lỗi hoặc chạy `.exe` xong bị crash ngay, mở
  `desktop/HaiVan.spec`, đổi `console=False` thành `console=True`, build
  lại — sẽ hiện cửa sổ đen (terminal) cho thấy lỗi cụ thể để debug.
- File `.exe` build ra khá nặng (~200-400MB) vì đóng gói cả Python +
  Streamlit + toàn bộ thư viện — đây là đặc điểm bình thường của
  PyInstaller, không phải lỗi.
- Máy build và máy chạy `.exe` nên cùng kiến trúc (64-bit) — PyInstaller
  không cross-compile được (không build .exe Windows từ máy Mac/Linux).

## Kiểm tra trước khi đóng gói

Trước khi build `.exe`, nên chạy thử `desktop/launcher.py` trực tiếp bằng
Python để chắc chắn logic đúng, dễ debug hơn build .exe rồi mới phát hiện lỗi:

```
pip install -r requirements.txt
pip install -r desktop/requirements-desktop.txt
python desktop/launcher.py
```

Nếu bước này chạy ra đúng 1 cửa sổ ứng dụng thì build `.exe` gần như chắc
chắn cũng chạy được.

## Vẫn cần dữ liệu Copernicus/Open-Meteo như bình thường

Đóng gói thành `.exe` KHÔNG làm thay đổi việc app cần tải dữ liệu sóng/
dòng chảy/khí tượng — vẫn cần bấm "🔄 Tải dữ liệu mới nhất" trong app, và
máy chạy `.exe` vẫn cần kết nối Internet + đã đăng nhập Copernicus Marine
(`copernicusmarine login`) như hướng dẫn trong README.md chính.
