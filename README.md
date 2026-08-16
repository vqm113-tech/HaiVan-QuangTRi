# Hệ thống Dự báo Hải văn Quảng Trị

Ứng dụng Streamlit sinh **Bản tin dự báo/cảnh báo hải văn 10 ngày** (thủy triều,
sóng, dòng chảy) cho vùng biển tỉnh Quảng Trị, xuất ra file Word (`.docx`) đúng
thể thức hành chính KTTV, từ số liệu mực nước thực đo (Excel).

## Cách chạy

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tải lên file Excel số liệu mực nước theo mẫu `data/sample/solieu.xlsx`
(cột 1 = thời gian, các cột sau = mực nước từng trạm), rồi bấm "TẠO BẢN TIN".

## Cấu trúc thư mục

```
app.py                     Giao diện Streamlit — điểm vào duy nhất
config.py                  Đường dẫn thư mục, tên dataset Copernicus
station_config.py          Tọa độ + tên hiển thị 4 trạm hải văn

bulletin/
  area_data.py             Điều phối chính: QC -> mô hình triều -> đóng gói dữ liệu bản tin
  tide_model.py            Mô hình điều hòa triều chuẩn (dùng models/) — MỚI
  marine_data.py           Đọc sóng/dòng chảy thật từ .nc cho từng vùng biển — MỚI
  bulletin_generator.py    Sinh file .docx đúng thể thức từ dữ liệu trên

core/
  qc.py                    Kiểm soát chất lượng số liệu (chuẩn UNESCO/IOC) — ĐANG DÙNG
  wave_forecast.py         Đọc VHM0/VMDR từ file .nc theo trạm, gộp theo ngày — ĐANG DÙNG
  current_forecast.py      Đọc dòng chảy từ file .nc theo trạm, gộp theo ngày — ĐANG DÙNG
  weather_download.py      Tải mưa/gió/tầm nhìn từ Open-Meteo — ĐANG DÙNG (MỚI)
  weather_forecast.py      Gộp dữ liệu khí tượng theo ngày, WMO code -> tiếng Việt — ĐANG DÙNG (MỚI)
  weather_analysis.py      Sinh nhận định thời tiết biển 3 ngày — ĐANG DÙNG
  sea_weather_text.py      Sinh câu văn tổng hợp/nhận định hải văn — ĐANG DÙNG
  warning_analysis.py      Phát hiện hiện tượng nguy hiểm — ĐANG DÙNG
  longterm_analysis.py     Nhận định xu thế ngày 4–10 — ĐANG DÙNG
  wave_download.py         Tải sóng từ Copernicus Marine — ĐANG DÙNG (nút sidebar app.py)
  current_download.py      Tải dòng chảy từ Copernicus Marine — ĐANG DÙNG (nút sidebar app.py)
  interpolation.py         Nội suy nâng cao — CHƯA NỐI
  ai_forecaster.py         Bộ điều phối gốc — KHÔNG dùng trực tiếp (có lỗi phạm
                            vi dữ liệu, xem mục bên dưới); area_data.py gọi
                            thẳng 5 module con ở trên với đúng phạm vi ngày

models/                    Bộ mô hình điều hòa thủy triều đầy đủ (nodal correction,
                            Rayleigh criterion, hằng số triều, solver, extrema...)
                            — ĐANG DÙNG (qua bulletin/tide_model.py)

data/
  sample/solieu.xlsx        File mẫu để test
  wave_data/wave.nc          1 file mẫu (bản gốc có 50 file tải trùng, đã dọn)
  current_data/current.nc    1 file mẫu (bản gốc có 42 file tải trùng, đã dọn)

outputs/                    Bản tin .docx sinh ra khi chạy app (không phải mã nguồn)
```

## Trạng thái thật của luồng dữ liệu hiện tại

`app.py` → `core.qc.load_data` → `bulletin.area_data.build_area_data` →
`bulletin.bulletin_generator.create_qtri_bulletin`

Trong `build_area_data()`:
- **Thủy triều (Hx/Hm)**: tính thật từ dữ liệu Excel, đã qua **QC**
  (`core.qc.MarineQualityControl.run_pipeline` — loại giá trị ngoài khoảng vật
  lý, bước nhảy bất thường, ngoại lai Hampel, nội suy khoảng trống ngắn), sau
  đó fit bằng **bộ mô hình điều hòa triều chuẩn** (`models/` qua
  `bulletin/tide_model.py`, 8 hằng số M2/S2/N2/K2/K1/O1/P1/Q1 có hiệu chỉnh
  nodal, tự động loại hằng số không phân giải được theo tiêu chuẩn Rayleigh
  nếu chuỗi số liệu ngắn).
- **Sóng, dòng chảy**: đọc **thật** từ file `.nc` (`core/wave_forecast.py`,
  `core/current_forecast.py` qua `bulletin/marine_data.py`), gộp theo từng
  ngày lịch cho 5 vùng biển của bản tin (ánh xạ 4 trạm thật → 5 vùng, xem
  `REGION_TO_STATION` trong `marine_data.py`). Nếu chưa cài `xarray`/`netCDF4`
  hoặc chưa có file `.nc` thật, tự động dùng giá trị dự phòng an toàn, **không
  làm gãy app**.
- **Thời tiết biển tường thuật (bảng 1), cảnh báo, nhận định xu thế (mục 1-6)**:
  sinh THẬT từ dữ liệu triều/sóng/dòng chảy qua
  `bulletin.area_data.generate_narrative_texts()`. ⚠️ Nhưng xem cảnh báo giới
  hạn ngay bên dưới — không phải mọi trường đều dựa trên số liệu thật.

### ⚠️ Bảng 1 / văn bản mục 1-6 — cập nhật: đã có nguồn khí tượng thật

Trước đây hệ thống **không có bất kỳ nguồn dữ liệu khí tượng khí quyển thật
nào** — chỉ có dữ liệu sóng/dòng chảy đại dương (Copernicus) và mực nước
triều (Excel). Nay đã bổ sung `core/weather_download.py` +
`core/weather_forecast.py`, lấy **mưa, gió, tầm nhìn thật** từ **Open-Meteo**
(https://open-meteo.com — API thời tiết miễn phí, không cần đăng ký/API key,
khác với Copernicus Marine cần tài khoản), tại điểm đại diện tọa độ trạm Cửa
Việt.

Khi đã tải dữ liệu khí tượng (bấm "🔄 Tải dữ liệu mới nhất" ở sidebar), bảng 1
dùng THẬT:
- **"Thời tiết"**: suy từ mã thời tiết WMO (`weathercode`) + tổng lượng mưa
  trong ngày (`core.weather_forecast._weather_text`) — không còn ngẫu nhiên.
- **"Tầm nhìn"**: từ biến `visibility` (mét) của Open-Meteo, lấy giá trị thấp
  nhất trong ngày.
- **"Gió"**: tốc độ VÀ hướng đều lấy tại thời điểm gió mạnh nhất trong ngày
  (`windspeed_10m`, `winddirection_10m`) — không còn mặc định "Tây Bắc".
- **"Trạng thái biển"**: vẫn suy từ độ cao sóng thật (không đổi).

Nếu chưa tải dữ liệu khí tượng (file `data/weather_data/weather.json` chưa
có, hoặc tải thất bại), tự động quay lại hành vi CŨ làm dự phòng: "Thời tiết"
chọn ngẫu nhiên, "Tầm nhìn" cố định "Trên 10 km", hướng gió mặc định "Tây
Bắc", gió suy thô từ độ cao sóng (`Hs * 6`) — xem
`core.weather_analysis.generate_weather_3days(atmos_data=None)`.

**Bản gốc `core.ai_forecaster.generate_ai_forecast()` không được dùng trực
tiếp**: hàm này truyền CHUNG một bộ `(tide_data, wave_data, current_data)` cho
cả văn bản "3 ngày tới" lẫn "ngày 4-10", trong khi `generate_longterm_comment()`
cần dữ liệu đủ 10 ngày (đọc chỉ số ngày 4 và ngày 10) còn
`generate_marine_comment()`/`analyze_danger()`/`analyze_impact()` chỉ nên dùng
riêng 3 ngày đầu — dùng chung sẽ làm sai lệch phạm vi thời gian. Do đó
`bulletin/area_data.py` gọi thẳng 5 hàm con với đúng phạm vi dữ liệu (xem
`generate_narrative_texts()`).

## Đã thêm: xem trước & sửa trực tiếp Tin gió mạnh, sóng lớn trước khi xuất

Tách nút "Tạo tin" cũ (xuất thẳng) thành 2 bước, giống cách đã làm với bản
tin 10 ngày:
1. Nút "🔄 Tính dữ liệu" — tính từ gió/sóng thật, hiển thị ra để xem trước.
2. Dự báo viên sửa trực tiếp: `st.text_area` cho mục 1/2/3/5, `st.text_input`
   cho cột "Thời điểm dự báo" và cấp độ rủi ro (mục 4), `st.data_editor` cho
   bảng 3 vùng biển (đổi tên cột sang tiếng Việt, ánh xạ ngược khi ghi lại
   — đã kiểm thử độc lập: sửa 1 ô đúng ô đó đổi, ô khác giữ nguyên).
3. Nút "🚨 Xuất tin" riêng — dùng ĐÚNG nội dung đã sửa để tạo `.docx` (đã
   kiểm chứng bằng cách sửa tay `past_text`/`risk_level` rồi xuất, đọc lại
   file `.docx` xác nhận in ra đúng nội dung đã sửa, không phải nội dung
   tính toán gốc).
- Nút "↺ Bỏ tính toán" xóa hết để tính lại từ đầu.
- Khi bấm "🔄 Tính dữ liệu" lần nữa (ví dụ đổi giờ phát tin), state của các
  ô đã sửa trước đó bị xóa để hiển thị đúng giá trị mới tính, tránh giữ
  nhầm nội dung cũ đã sửa từ lần tính trước.

## Đã thêm: Tin dự báo gió mạnh, sóng lớn (bản tin hải văn nguy hiểm) — MỚI

Người dùng gửi mẫu thật `QTRI_HVNH_20260310_1600.docx` — đây là loại bản tin
KHÁC bản tin 10 ngày (khác khung, khác số lượng vùng biển: chỉ 3 vùng Bắc/
Nam/Đặc khu Cồn Cỏ thay vì 5, có thêm cấp gió Bô-pho và cấp độ rủi ro thiên
tai). Đã thêm như một tính năng riêng, độc lập với bản tin 10 ngày:

- **`core/beaufort.py` (mới)**: quy đổi tốc độ gió (m/s) sang cấp gió
  Bô-pho chuẩn quốc tế; sinh câu "cấp X, giật cấp Y" — đã sửa 1 lỗi logic
  lúc test: cấp giật ban đầu có thể ra BẰNG cấp gió trung bình (vô lý, giật
  luôn phải cao hơn) — đã ép cấp giật tối thiểu +1 so với trung bình.
- **`bulletin/warning_data.py` (mới)**: tính dữ liệu bản tin từ gió thật
  (Open-Meteo, qua `core/weather_forecast.py`) và sóng thật (Copernicus, qua
  `get_wave_daily_at`) đã có sẵn — KHÔNG cần file Excel thủy triều (bản tin
  này không có bảng triều). Cấp độ rủi ro thiên tai ước lượng theo cấp gió
  giật lớn nhất.
  ⚠️ **Cần lưu ý**: quy đổi cấp giật (~tốc độ trung bình +30%) và cấp độ rủi
  ro thiên tai là ƯỚC LƯỢNG theo hiểu biết chung (tinh thần QĐ 18/2021/QĐ-
  TTg), KHÔNG phải trích dẫn chính xác quy định hiện hành — dự báo viên bắt
  buộc phải tự kiểm tra lại trước khi ban hành chính thức.
- **`bulletin/bulletin_generator.py::create_qtri_warning_bulletin()` (mới)**:
  dựng file `.docx` đúng khung mẫu (đã render ảnh so sánh, khớp cấu trúc
  header/bảng/gộp ô/chữ ký với mẫu thật).
- **`app.py`**: thêm khu vực "🚨 Tin dự báo gió mạnh, sóng lớn" — ĐỘC LẬP với
  phần tải file Excel (đặt trước bước chọn file), vì bản tin này không cần
  số liệu triều.

## Đã sửa lỗi thật: "Độ cao sóng" chưa gộp ngang (từ lần sửa trước)

Lần sửa trước mình chỉ đổi đậm/nghiêng cho "Độ cao sóng"/"Độ cao (mét)"/
"Hướng" nhưng BỎ SÓT một lỗi có sẵn: ô "Độ cao sóng" ở hàng đầu KHÔNG được
gộp ngang với ô trống bên cạnh (`format_cell(hdr0[4], "")` — chỉ ghi rỗng
chứ không `.merge()`), khiến hiển thị thành 2 ô tách rời có viền dọc ở giữa
thay vì 1 ô rộng phủ đúng 2 cột "Độ cao (mét)"/"Hướng" bên dưới — người
dùng chụp ảnh chỉ ra đúng lỗi này. Đã sửa: `hdr0[3].merge(hdr0[4])` (giống
cách đã làm với ô "Ngày"/"Yếu tố dự báo" ở bản tin 10 ngày), và theo đúng
yêu cầu lần này **giữ chữ đậm** (không nghiêng như lần sửa trước — người
dùng đã đổi ý). Đã kiểm tra bằng `gridSpan` trong XML (đúng 1 lần gộp) và
render ảnh xác nhận khớp đúng ảnh mẫu.

## Đã sửa theo yêu cầu: khớp ảnh mẫu Tin gió mạnh, sóng lớn (tiêu đề 2 dòng, "Độ cao sóng" chữ nghiêng)

Người dùng gửi 2 ảnh chụp từ bản tin mẫu, phát hiện 2 khác biệt:
1. Tiêu đề phải xuống dòng đúng vị trí "TIN DỰ BÁO GIÓ MẠNH, SÓNG LỚN" /
   "TRÊN VÙNG BIỂN TỈNH QUẢNG TRỊ" (trước đó là 1 chuỗi dài, word-wrap tự
   động không đảm bảo đúng điểm ngắt) — đã tách rõ 2 dòng.
2. Tiêu đề nhóm cột "Độ cao sóng" / "Độ cao (mét)" / "Hướng" trong bảng dự
   báo 24h phải là CHỮ NGHIÊNG (không đậm) — trước đó đang để đậm giống các
   cột khác. Đã sửa `bold=False, italic=True` cho đúng 3 ô này, các cột
   khác ("Thời điểm dự báo", "Vùng biển ảnh hưởng", "Gió mạnh") vẫn giữ đậm
   như cũ (ảnh mẫu không có thông tin đổi các cột đó). Đã render ảnh xác
   nhận khớp đúng.

## Đã sửa theo yêu cầu: văn bản mục 1-6 cũng đổi sang mét (khớp bảng)

Lần trước mình CHỦ Ý chỉ đổi đơn vị hiển thị ở bảng, giữ cm ở văn bản mục
1-6 để tránh ảnh hưởng tới logic tính xu thế nội bộ (đang dùng cm) — nhưng
người dùng muốn văn bản cũng hiển thị mét để khớp bảng. Đã sửa đúng phạm vi
cần thiết: chỉ đổi ĐƠN VỊ HIỂN THỊ trong 4 chỗ `sec1_text`/`sec3_text`
(fallback) ghi trực tiếp số Hx/Hm ra câu chữ (`hx_1_m`, `hx_3_m`, `hm_1_m`,
`max_hx_7_m` — quy đổi bằng `_cm_to_m_str()` đã có sẵn), KHÔNG đổi biến nội
bộ `tide_dict`/`hx_1`/`hx_3`/`hm_1`/`max_hx_7` (vẫn cm) nên không ảnh hưởng
logic tính xu thế. Đã kiểm tra thêm: `core/sea_weather_text.py` và
`core/longterm_analysis.py` (sinh `sec3_text`/`sec4_text` khi có dữ liệu
sóng/dòng chảy thật) chỉ SO SÁNH Hx đầu-cuối để suy ra xu thế tăng/giảm,
KHÔNG in số cm ra câu chữ — nên không có chỗ nào khác cần sửa. Test cho ra
`sec1_text`: "Đỉnh triều cao nhất đạt 1.21m (06:59)..." — khớp đơn vị mét
với Bảng 2/3.

## Đã sửa theo yêu cầu: gạch chân header, đổi đơn vị triều sang mét

1. **Gạch chân "TỈNH QUẢNG TRỊ" và "Độc lập - Tự do - Hạnh phúc"** ở phần
   header — áp dụng cho CẢ 2 loại bản tin (`create_qtri_bulletin` và
   `create_qtri_warning_bulletin`, dùng chung cấu trúc header). Đã tách
   riêng "TỈNH QUẢNG TRỊ" thành 1 run khác với "ĐÀI KHÍ TƯỢNG THỦY VĂN" (để
   chỉ gạch chân đúng dòng đó, không gạch cả 2 dòng) — kiểm tra bằng cách
   đếm thẻ `<w:u>` trong XML (đúng 2 lần mỗi bản tin) và render ảnh xác
   nhận khớp đúng ảnh mẫu.
2. **Đổi đơn vị triều trong Bảng 2/3 từ cm sang mét, 2 số thập phân** (ví
   dụ "136" → "1.36") — đổi nhãn cột "Hx (cm)"/"Hm (cm)" thành "Hx (m)"/
   "Hm (m)". ⚠️ Chỉ đổi đơn vị HIỂN THỊ trong bảng — cố tình GIỮ NGUYÊN đơn
   vị cm cho phần TÍNH TOÁN NỘI BỘ (văn bản tường thuật mục 1-6, xu thế
   triều dùng trong `core/longterm_analysis.py`/`sea_weather_text.py`), vì
   các module đó có ngưỡng/logic đang giả định đơn vị cm — đổi luôn ở đó có
   nguy cơ làm sai xu thế/ngưỡng cảnh báo. Đã kiểm tra: bảng ra đúng mét
   ("1.25", "1.33"...), còn `sec1_text` vẫn đúng cm ("121cm") như cũ,
   không xung đột.

## Đã thêm: xuất Excel số liệu sóng/dòng chảy theo giờ — MỚI

Thêm `bulletin/excel_export.py::build_marine_excel()` — xuất file `.xlsx` 2
sheet ("Sóng (Copernicus)", "Dòng chảy (Copernicus)"), mỗi vùng trong 5 vùng
dự báo 1 cặp cột (Hs/Hướng hoặc Vận tốc/Hướng), theo ĐÚNG mốc thời gian thật
có trong file `.nc` đã tải — khác bảng 2/3 trong bản tin (chỉ có min-max mỗi
ngày). Dùng lại `get_wave_forecast_at`/`get_current_forecast_at` (đã có sẵn,
trả về chuỗi đầy đủ chưa gộp ngày) — không viết lại logic đọc `.nc`.

- Sóng lấy mẫu 3 giờ/lần, dòng chảy 1 giờ/lần (đúng tần suất gốc của dữ
  liệu Copernicus) — KHÔNG nội suy giả để ép về cùng "theo giờ", tránh tạo
  ra số liệu giả không có thật. Đã kiểm thử bằng dữ liệu giả lập: ra đúng
  8 dòng/ngày cho sóng (3h × 8 = 24h), 24 dòng/ngày cho dòng chảy, đúng 11
  cột (1 cột giờ + 5 vùng × 2).
- ⚠️ Đặt tên sheet rõ "(Copernicus)" vì đây là dữ liệu MÔ HÌNH đại dương
  (phân tích + dự báo), không phải số liệu đo đạc thực tế tại phao/trạm —
  tránh gây hiểu nhầm là "thực đo" như cách gọi ban đầu.
- `app.py`: thêm khu vực "📊 Xuất Excel số liệu sóng/dòng chảy theo giờ",
  độc lập với file Excel thủy triều (chỉ cần file `.nc` đã tải).

## Đã sửa theo yêu cầu: bỏ bản đồ khỏi giao diện, bỏ đơn vị "m" ở độ cao sóng

1. **Bỏ hẳn bản đồ khỏi `app.py`**: xóa toàn bộ khối "🗺️ Bản đồ vị trí vùng dự
   báo" (các hàm `_build_zone_polygons`, `_boundary_reference_lines`,
   `_load_map_marine_data`, layer pydeck...) — đã dọn theo các import chỉ
   phục vụ bản đồ không còn dùng nữa (`pydeck`, `FORECAST_REGIONS`,
   `get_wave_daily_at`, `get_current_daily_at`), bỏ luôn yêu cầu
   `pydeck>=0.8` và hạ lại `streamlit>=1.35` trong `requirements.txt` (bản
   1.39 trước đó chỉ cần cho tính năng bấm chuột trên bản đồ, nay không cần
   nữa). Toàn bộ phần lấy dữ liệu sóng/dòng chảy đúng tọa độ 5 vùng dự báo
   (`bulletin/marine_data.py`) và hiệu chỉnh riêng từng vùng ở mục "⚙️ Hiệu
   chỉnh dự báo sóng/dòng chảy" vẫn giữ nguyên, không bị ảnh hưởng — chỉ bỏ
   phần HIỂN THỊ bản đồ trực quan.
2. **Bỏ đơn vị "m" ở giá trị độ cao sóng** trong Bảng 2 và Bảng 3 (ví dụ
   "0.54 - 0.82m" → "0.54 - 0.82") — sửa 1 chỗ duy nhất trong
   `bulletin/marine_data.py::build_wave_current_tables()` vì cả 2 bảng dùng
   chung nguồn dữ liệu này. Cột "H (m)" trong bảng đã tự nói rõ đơn vị nên
   không cần lặp lại trong từng ô. Không đụng tới các chỗ khác vẫn dùng đơn
   vị "m" trong câu văn tường thuật (mục 1-6), vì ở đó lặp đơn vị trong câu
   là bình thường, không phải lỗi.

## Đã sửa theo yêu cầu: khớp đúng ảnh mẫu phần header (đậm/thường, cỡ chữ)

Người dùng gửi ảnh chụp phần đầu bản tin mẫu thật, phát hiện 1 lỗi: dòng
"ĐÀI KHÍ TƯỢNG THỦY VĂN TRUNG BỘ" đang bị **in đậm nhầm** — theo ảnh mẫu,
dòng này chữ THƯỜNG (không đậm), chỉ dòng "ĐÀI KHÍ TƯỢNG THỦY VĂN / TỈNH
QUẢNG TRỊ" mới in đậm. Đã sửa: tách rõ 2 dòng riêng (không dựa vào word-wrap
tự động nữa), bỏ đậm dòng đầu, giữ đậm dòng sau — đã render ảnh xác nhận
khớp đúng ảnh mẫu.

Cũng giảm cỡ chữ theo đúng yêu cầu: phần quốc hiệu/tổ chức (cả 2 bên trái-
phải + số hiệu + ngày tháng) từ 13pt xuống **12pt** (để vừa giấy, không bị
ép xuống dòng giữa chừng như bản 13pt trước), tiêu đề bản tin từ 15pt xuống
**13pt** — đã render ảnh xác nhận không còn bị tràn/ngắt dòng xấu.

## Đã sửa theo yêu cầu: thêm năm vào tiêu đề ngày (Bảng 1/2/3), xoay dọc tiêu đề ngày Bảng 3

Theo ảnh mẫu Bảng 3 người dùng gửi (7 cột ngày, tiêu đề xoay dọc đọc từ dưới
lên, có đầy đủ ngày/tháng/năm):
- `bulletin/area_data.py`: đổi định dạng ngày từ `%d/%m` (ví dụ "24/4") sang
  `%d/%m/%Y` (ví dụ "24/04/2026") cho cả `days_3` và `days_7` — dùng chung 1
  nguồn `dates_str` nên sửa 1 chỗ là áp dụng cho cả 3 bảng.
  ⚠️ Phát hiện & sửa luôn 1 lỗi phát sinh: `period_text` ("Từ ngày... đến
  ngày...") trước đó tự nối thêm `/2026` vào cuối — nay ngày đã có sẵn năm
  đầy đủ nên nối thêm sẽ bị trùng (ví dụ "12/06/2026/2026"), đã bỏ hậu tố
  thừa này.
- `bulletin/bulletin_generator.py`: thêm `format_cell_vertical()` — tiêu đề
  7 cột ngày ở Bảng 3 nay XOAY DỌC (`textDirection="btLr"`, đọc từ dưới
  lên) đúng như ảnh mẫu, để đủ chỗ hiển thị ngày/tháng/năm đầy đủ mà không
  làm bảng quá rộng. Bảng 1/2 chỉ có 3 cột ngày nên vẫn để chữ ngang bình
  thường (đủ chỗ, không cần xoay) — đã render ảnh xác nhận cả 2 cách hiển
  thị đều đúng, không bị chật hay tràn chữ.

## Đã sửa theo yêu cầu: khớp đúng ảnh mẫu (ô chia chéo gộp ngang, cỡ chữ 13), hiệu chỉnh sóng/dòng chảy riêng từng vùng

Người dùng gửi 3 ảnh chụp từ bản tin mẫu thật (Bảng 1, 2, 3), phát hiện 2 điều
cần sửa so với bản trước:

1. **Ô "Ngày"/"Yếu tố dự báo" phải GỘP NGANG với cột "Chỉ tiêu" bên cạnh** ở
   Bảng 2 và Bảng 3 (chỉ ở HÀNG TIÊU ĐỀ — 2 hàng dữ liệu bên dưới vẫn tách
   riêng nhóm yếu tố | chỉ tiêu cụ thể như cũ) để ô đủ rộng, đúng như ảnh
   mẫu — bản trước chỉ vẽ chéo trong 1 cột hẹp nên trông khác mẫu. Dùng
   `cell.merge()` ngang CHỈ cho hàng 0 trước khi áp `format_diagonal_header_
   cell()`. Đã kiểm tra: `gridSpan` xuất hiện đúng 2 lần (bảng 2, 3), dòng dữ
   liệu bên dưới vẫn tách 2 cột riêng biệt (đã render ảnh xác nhận).
2. **Bảng 1 cũng cần ô chia chéo** (trước đó chỉ có ở bảng 2/3, bảng 1 vẫn
   dùng 2 dòng chữ thường) — đã thêm, bảng 1 không cần gộp ngang vì vốn chỉ
   có 1 cột "Yếu tố dự báo" (không có cột "Chỉ tiêu" riêng).
3. **Cỡ chữ 13** cho toàn bộ bảng (trước đó 12, đã tăng theo đúng yêu cầu).

### Hiệu chỉnh sóng/dòng chảy — RIÊNG TỪNG VÙNG BIỂN

Trước đây chỉ có 1 hệ số chung áp dụng cho cả 5 vùng. Nay đổi sang hiệu
chỉnh riêng từng vùng, giống hệt cách làm hiệu chỉnh triều theo trạm:
- `bulletin/marine_data.py`: `build_wave_current_tables()` và
  `get_province_wide_daily()` nhận `wave_scale`/`current_scale` dưới dạng
  **dict `{region_key: hệ_số}`** (vẫn nhận số đơn để tương thích ngược) —
  đã kiểm thử: hiệu chỉnh đúng riêng cho vùng được chọn, vùng khác không đổi;
  văn bản tường thuật toàn tỉnh cũng phản ánh đúng giá trị đã hiệu chỉnh của
  vùng có giá trị lớn nhất trong ngày.
- `app.py`: khu vực hiệu chỉnh đổi thành chọn vùng biển (selectbox) rồi nhập
  2 hệ số cho đúng vùng đó, lưu theo `st.session_state` riêng từng vùng.

## Đã sửa theo yêu cầu: cỡ chữ/ô chia chéo, hệ số hiệu chỉnh sóng/dòng chảy, sửa trực tiếp trên bản tin

### 1. Tiêu đề, cỡ chữ, ô chia chéo Bảng 2/3

- Tăng cỡ chữ trong bảng từ 9.5pt lên **12pt** (mặc định `format_cell`/
  `merge_vertical`), tăng cỡ chữ phần quốc hiệu/tổ chức từ 11pt lên 13pt,
  tiêu đề bản tin từ 14pt lên 15pt, phần "Nơi nhận"/chữ ký cũng tăng tương ứng.
- Thêm **ô tiêu đề chia chéo** cho cột "Ngày"/"Yếu tố dự báo" ở Bảng 2 và
  Bảng 3 (`format_diagonal_header_cell()` + `set_cell_diagonal_border()`,
  dùng thuộc tính OOXML chuẩn `w:tl2br`) — "Ngày" đặt căn phải ở nửa trên,
  "Yếu tố dự báo" căn trái ở nửa dưới, có đường chéo phân cách.
  ⚠️ **Lưu ý quan trọng**: đã xác nhận qua tìm kiếm — đây là **giới hạn đã
  biết của LibreOffice** (bug documentfoundation.org #51665, LibreOffice
  Writer không hỗ trợ render đường chéo bảng dù đã hỗ trợ trong Calc), nên
  khi mình render thử bằng LibreOffice trong môi trường này, đường chéo
  KHÔNG hiện ra dù XML đã đúng chuẩn (đã đối chiếu với tài liệu OOXML chính
  thức của Microsoft, khớp 100%). Vì bản tin thật sẽ mở bằng **Microsoft
  Word** (văn bản hành chính), đường chéo sẽ hiển thị đúng ở đó. Bạn nên mở
  thử bằng Word để xác nhận.

### 2. Hệ số hiệu chỉnh sóng/dòng chảy — MỘT ô áp dụng cho TẤT CẢ ngày

Thêm khu vực "⚙️ Hiệu chỉnh dự báo sóng / dòng chảy" trong `app.py`: 2 ô
nhập hệ số nhân (mặc định 1.0) áp dụng cho toàn bộ 10 ngày và cả 5 vùng biển
cùng lúc — đúng theo ví dụ yêu cầu: H = 0.5-1.5m với hệ số 1.2 → H =
0.6-1.8m (đã kiểm thử đúng công thức này). Luồng dữ liệu:
`bulletin/marine_data.py::build_wave_current_tables()` và
`get_province_wide_daily()` thêm tham số `wave_scale`/`current_scale`, nhân
vào `hs_min`/`hs_max`/`speed_min`/`speed_max` TRƯỚC khi format thành chuỗi
hiển thị → `bulletin/area_data.py::build_area_data()` nhận và truyền xuống,
đảm bảo cả bảng 2/3 VÀ văn bản tường thuật mục 1-6 đều khớp số liệu đã
hiệu chỉnh (không bị lệch giữa bảng và văn bản).

### 3. Sửa trực tiếp trên bản tin trước khi tạo

Khu vực xem trước trước đây chỉ hiển thị (`st.write`/`st.dataframe`), nay
chuyển thành **có thể sửa trực tiếp**:
- Văn bản mục 1-6: `st.text_area` — sửa xong, bản tin xuất ra dùng đúng nội
  dung đã sửa (ghi thẳng lại vào `area_data[key]` mỗi lần chạy lại, theo
  đúng mô hình rerun của Streamlit).
- Bảng 1/2/3 từng vùng biển: `st.data_editor` (đổi tên trường sang tiếng
  Việt dễ đọc như "Đỉnh triều Hx (cm)", có ánh xạ ngược khi ghi lại) — đã
  kiểm thử độc lập việc chuyển đổi qua lại giữa dict gốc và bảng hiển thị:
  sửa 1 ô → đúng giá trị đó đổi, các ô khác giữ nguyên.
- Nút "↺ Khôi phục nội dung gốc" xóa hết chỉnh sửa trong phiên làm việc,
  quay về nội dung tính toán ban đầu.
- ⚠️ Lưu ý hành vi: nếu đổi hệ số hiệu chỉnh triều/sóng/dòng chảy hoặc tải
  file Excel khác SAU KHI đã sửa tay nội dung, phần đã sửa tay sẽ KHÔNG tự
  cập nhật theo (vẫn giữ nguyên bản đã sửa) — cần bấm "↺ Khôi phục nội dung
  gốc" trước nếu muốn xem lại nội dung tính toán mới.

⚠️ Cả 3 mục trên đều dùng widget Streamlit khá mới (`st.data_editor`,
`text_area` với key ổn định) — chưa test được tương tác thật (không cài
được Streamlit đầy đủ trong môi trường này), bạn tự mở app kiểm tra.

## Đã sửa theo yêu cầu: bản đồ đơn giản/đẹp hơn, xem lại triều trạm cửa sông, hiệu chỉnh + xem trước bản tin

### 1. Bản đồ: màu cố định + trung điểm + bấm chuột xem giá trị

Bỏ hẳn cách tô "nhiệt" theo giá trị (gradient xanh-vàng-đỏ) và đường đẳng sâu
ước lượng phức tạp ở bước trước — theo đúng yêu cầu, đơn giản hóa lại:
- **Màu cố định từng vùng** (xanh lá/xanh dương nhạt/cam/tím — phỏng theo
  đúng bảng chú giải ảnh mẫu người dùng gửi), không đổi theo dữ liệu.
- **Ranh giới ven bờ/ngoài khơi = TRUNG ĐIỂM** kinh độ giữa tọa độ chính
  thức của vùng ven bờ và vùng ngoài khơi tương ứng (đơn giản, chính xác
  theo định nghĩa, không cần ước lượng đường bờ biển như bản trước) — đã
  kiểm chứng: cả 4 tọa độ vùng dự báo đều nằm đúng trong vùng mang tên nó.
- Ranh giới Bắc-Nam vẫn tại vĩ tuyến 17.30°N (giữ nguyên từ yêu cầu trước).
- **Bấm chuột hiện giá trị** thay vì tô nhiệt: dùng tính năng
  `st.pydeck_chart(..., on_select="rerun", selection_mode="single-object")`
  của Streamlit (cần **Streamlit ≥ 1.39** — đã cập nhật `requirements.txt`).
  Bấm vào 1 vùng màu hoặc 1 chấm tròn sẽ hiện hộp thông tin sóng/dòng chảy
  ngày tương ứng ngay bên dưới bản đồ.
  ⚠️ Chưa test được thao tác bấm chuột thật (không cài được Streamlit đầy đủ
  trong môi trường này) — bạn cần đảm bảo đã nâng cấp Streamlit lên đúng
  phiên bản rồi thử bấm vào bản đồ.

### 2. Số liệu triều tại trạm cửa sông (Cửa Việt) — đã xem lại

Đúng như bạn lưu ý: **Cửa Việt là trạm đo tại cửa sông**, chịu ảnh hưởng dòng
chảy nước ngọt/hình thái lòng sông chứ không thuần túy là triều biển hở —
mô hình điều hòa triều thuần túy (chỉ dùng 8 hằng số thiên văn) không nắm
bắt được hiệu ứng này, nên có thể cho kết quả lệch so với thực tế địa
phương. Đây là hạn chế **cố hữu của phương pháp điều hòa triều nói chung**
đối với trạm cửa sông, không phải lỗi code — cách xử lý đúng trong nghiệp
vụ dự báo là cho phép dự báo viên **hiệu chỉnh thủ công theo kinh nghiệm
địa phương**, nên mình đã làm mục 3 ngay dưới đây để giải quyết trực tiếp
vấn đề này, thay vì cố "sửa" mô hình cho đúng bằng thuật toán (không khả
thi nếu không có thêm số liệu bù trừ dòng chảy sông thật).

Cũng nhân dịp này đã sửa để **offset quy đổi hải đồ (+110cm)** không còn
cố định cứng cho mọi trạm — nay có thể hiệu chỉnh riêng từng trạm qua
`chart_datum_offset_cm` (xem `forecast_tide_from_observed()`), vì mốc "0 hải
đồ" mỗi trạm có thể khác nhau, đặc biệt trạm cửa sông so với trạm ven biển
hở/đảo.

### 3. Hiệu chỉnh hệ số điều hòa (sai số) + xem trước nội dung bản tin

- **`bulletin/tide_model.py::predict_tide()`** thêm 2 tham số:
  `amplitude_scale` (hệ số nhân biên độ riêng từng hằng số triều M2/S2/N2/
  K2/K1/O1/P1/Q1) và `manual_offset_m` (hiệu chỉnh sai số hệ thống, cộng
  thẳng vào kết quả dự báo) — đã kiểm thử: offset +20cm cho ra đúng +20cm
  trên toàn chuỗi dự báo, tăng hệ số M2 làm đỉnh triều tăng đúng hướng.
- **`bulletin/area_data.py::build_area_data()`** thêm tham số
  `tide_corrections` (dict theo từng trạm) truyền hiệu chỉnh RIÊNG cho từng
  trạm (Tân Mỹ/Đồng Hới/Cửa Việt/Cồn Cỏ) — đã kiểm thử: hiệu chỉnh áp đúng
  cho trạm được chọn, các trạm khác không đổi.
- **`app.py`** thêm khu vực "⚙️ Hiệu chỉnh dự báo triều theo địa phương":
  chọn trạm, nhập số cm hiệu chỉnh, và bảng chỉnh hệ số biên độ (%) từng
  hằng số triều (dùng `st.data_editor`), lưu theo phiên làm việc
  (`st.session_state`) cho từng trạm riêng biệt.
- **"📋 Xem trước nội dung bản tin"**: sau khi xử lý dữ liệu, hiện ngay toàn
  bộ văn bản mục 1-6 và bảng 1/2/3 (theo tab từng vùng biển) ngay trên giao
  diện, để dự báo viên kiểm tra/hiệu chỉnh trước khi bấm "TẠO BẢN TIN" xuất
  file `.docx` — không phải tải file xuống mới xem được nội dung như trước.

## Đã sửa theo yêu cầu: chia vùng theo đúng logic nghiệp vụ (không dùng hình chữ nhật)

Người dùng gửi ảnh bản đồ phân vùng hải văn thực tế và yêu cầu áp dụng đúng
logic chia vùng: (1) ranh giới Bắc-Nam theo vĩ tuyến 17.30°N, (2) ranh giới
ven bờ/ngoài khơi theo đường đẳng sâu 30m (~cách bờ 20-30km) — KHÔNG dùng
kinh tuyến cố định như bản trước, vì sóng biến dạng và dòng triều ven bờ
khác rõ so với ngoài khơi khi qua vùng nước nông.

Dự án chưa có nguồn dữ liệu địa hình đáy biển (GEBCO) nên không vẽ được
đúng đường đẳng sâu 30m thật. Đã làm bước xấp xỉ hợp lý thay vì hình chữ
nhật: tính đường ranh giới bằng cách offset ra biển **~28km** từ 1 đường
bờ biển nội suy qua các điểm mốc (dùng lại tọa độ trạm THẬT đã có trong
`station_config.STATIONS` cho Đồng Hới/Cửa Việt, thêm vài điểm ước lượng
để phủ hết phạm vi bản đồ — có ghi chú rõ trong code điểm nào là thật/ước
lượng). 4 vùng dự báo giờ là polygon có 1 cạnh cong bám theo hình bờ biển,
không phải hình chữ nhật; Côn Cỏ tách riêng thành điểm đánh dấu (đúng như
bản đồ mẫu — không phải 1 trong 4 vùng màu).

**Đã kiểm chứng bằng script độc lập** (không cần Streamlit): cả 4 tọa độ
vùng dự báo chính thức (`FORECAST_REGIONS`) đều rơi ĐÚNG phía của đường
ranh giới mới (offshore_* nằm phía ngoài khơi, coastal_* nằm phía ven bờ)
— lần thử đầu tiên phát hiện `coastal_south` bị rơi sai phía do điểm mốc bờ
biển phía Nam Cửa Việt chưa đủ sát thực tế, đã chỉnh lại và xác nhận lại
đúng. Cũng đã kiểm tra 4 polygon đều khép kín và không tự cắt (đường cong
đơn điệu theo vĩ độ).

Thêm 2 đường tham chiếu hiển thị trên bản đồ (đường đỏ = 17.30°N, đường xanh
= ranh giới ven bờ/ngoài khơi) — giống mục "ĐƯỜNG CHIA VÙNG" trong bản đồ
mẫu. Giữ nguyên tính năng tô màu theo giá trị sóng/dòng chảy đã làm ở bước
trước (áp dụng cho cả 4 vùng polygon mới và điểm Côn Cỏ).

⚠️ **Đây là ước lượng, không phải đường đẳng sâu 30m đo đạc thật** — độ
chính xác phụ thuộc vào các điểm mốc bờ biển tự ước lượng (đã ghi rõ trong
code). Muốn chính xác tuyệt đối cần nguồn dữ liệu bathymetry thật (GEBCO —
đúng nguồn mà bản đồ mẫu của bạn ghi ở góc "Nguồn: GEBCO, VN2000..."), đây
sẽ là việc cần làm thêm nếu bạn cần độ chính xác cao hơn. Cũng chưa test
được hiển thị thật trên Streamlit (không cài được trong môi trường này).

## Đã sửa theo yêu cầu: bản đồ nền sáng + phân vùng, tên người ký cố định

Người dùng gửi bản tin thật đã xuất ra, phát hiện tên người ký luôn là "Đàm
Hữu Tuyến" dù mục "Dự báo viên" đã đổi sang người khác. Đã sửa:

1. **Tên người ký (`leader_name`)**: `bulletin_generator.py` đã có sẵn
   `data_dict.get('leader_name', 'Đàm Hữu Tuyến')` nhưng **không có nơi nào
   set giá trị này** nên luôn rơi về mặc định. Đã thêm ô nhập riêng "Người ký
   (Lãnh đạo duyệt)" trong `app.py` (tách khỏi "Dự báo viên" vì đây là 2 vai
   trò khác nhau — dự báo viên có thể nhiều người, người ký là 1 lãnh đạo cụ
   thể), gán vào `area_data['leader_name']` trước khi xuất bản tin. Đã kiểm
   tra: đổi tên ở ô nhập thì chữ ký trong `.docx` đổi theo đúng.

2. **Bản đồ nền sáng + chia vùng hình khối lấy tọa độ làm tâm**: thay
   `ScatterplotLayer` (chỉ chấm điểm) bằng `PolygonLayer` — mỗi vùng dự báo
   giờ là 1 ô hình chữ nhật có TÂM đúng bằng tọa độ chính thức, kích thước ô
   tính từ khoảng cách tới vùng lân cận (theo từng cặp Bắc/Nam và ven bờ/
   ngoài khơi riêng biệt, không dùng 1 giá trị trung bình chung) để 4 ô
   khớp khít cạnh nhau — đã kiểm chứng bằng script độc lập: cả 4 cạnh chung
   khớp tuyệt đối, tâm mỗi ô đúng tọa độ gốc. Côn Cỏ dùng ô nhỏ hơn (không
   phải 1 trong 4 vùng biển lớn). Nền bản đồ đổi sang **CARTO Positron**
   (nền sáng, không cần token) thay vì nền mặc định tối màu của pydeck.
   ⚠️ Chưa test được hiển thị `PolygonLayer`/nền bản đồ thật (không cài được
   Streamlit đầy đủ trong môi trường này) — bạn tự mở app kiểm tra hình dạng
   4 ô vùng biển + nền sáng hiển thị đúng.

## Đã sửa theo yêu cầu: bản đồ tô màu + hiển thị giá trị sóng/dòng chảy

Bản đồ trước đó chỉ đánh dấu vị trí + tên vùng, chưa thể hiện giá trị. Đã bổ
sung trong `app.py`:
- Chọn tô màu theo **độ cao sóng (m)** hoặc **tốc độ dòng chảy (m/s)** (radio
  button), và chọn **ngày dự báo** (1-10, slider) — dữ liệu đọc 1 lần cho cả
  10 ngày rồi cache theo thời điểm sửa đổi file `.nc`
  (`st.cache_data(ttl=300)` khóa theo `wave_mtime`/`current_mtime`) để không
  đọc lại file mỗi lần người dùng đổi lựa chọn trên giao diện.
- Màu điểm nội suy xanh lá (êm) → vàng → đỏ (dữ dội) theo giá trị lớn nhất
  trong ngày, kèm thanh chú giải gradient; kích thước điểm cũng tỉ lệ theo
  giá trị. Nhãn dưới mỗi điểm hiển thị cả tên vùng, khoảng độ cao sóng VÀ
  khoảng tốc độ dòng chảy thật (không chỉ mỗi yếu tố đang chọn tô màu).
- Đã kiểm thử độc lập (không cần Streamlit) logic nội suy màu/bán kính và
  toàn bộ vòng lặp đọc dữ liệu 5 vùng × 10 ngày — chạy đúng, không crash.
  ⚠️ Vẫn chưa test được `st.cache_data`/`pydeck_chart` hiển thị thật (không
  cài được Streamlit đầy đủ trong môi trường này) — bạn tự mở app kiểm tra.

## Đã sửa theo yêu cầu: khung bản tin chuẩn + bản đồ vùng dự báo

Người dùng cung cấp 1 bản tin mẫu thật (`QTRI_HVHV_20260424_1600.docx`) và
tọa độ chính thức 5 vùng dự báo. Đã làm:

1. **`bulletin/bulletin_generator.py` — khung bản tin chuẩn**: so sánh trực
   tiếp (render PDF từng trang) bản tin cũ với file mẫu, phát hiện khác biệt
   chính là bảng không dùng **gộp ô thật** (rowspan) cho cột "Vùng biển dự
   báo" và cột nhóm yếu tố (Thủy triều/Sóng biển/Dòng chảy) — bản cũ để các ô
   trống lặp lại, nhìn không chuẩn như văn bản hành chính thật. Đã viết lại
   toàn bộ hàm dựng bảng dùng `cell.merge()` thật, bỏ màu nền tiêu đề (mẫu
   dùng nền trắng), thêm dòng "Ngày" phía trên "Yếu tố dự báo" đúng mẫu.
   Xác nhận bằng cách xuất `.docx` thử và kiểm tra thuộc tính
   `rowspan="N"` trong XML — đúng như mẫu chuẩn.
   ⚠️ Trong lúc viết lại có gặp 1 lỗi (tự phát hiện và tự sửa ngay): gán nhầm
   cột khiến chữ bị chồng lên nhau ở Bảng 1 — đã kiểm tra lại bằng cách dump
   nội dung bảng ra text trước khi bàn giao.

2. **Tọa độ vùng dự báo + bản đồ**: người dùng cung cấp tọa độ CHÍNH THỨC
   của 4/5 vùng dự báo (thêm Cồn Cỏ dùng tọa độ trạm thật có sẵn) —
   `station_config.FORECAST_REGIONS`. Phát hiện tọa độ này **lệch khá xa**
   so với trạm triều đang dùng làm proxy lấy sóng/dòng chảy trước đó (vùng
   "ngoài khơi phía Nam" ở kinh độ ~109.01°, cách trạm Cồn Cỏ đang dùng hơn
   150km) — nên đã:
   - Tách `core/wave_forecast.py`/`current_forecast.py` thành hàm lõi nhận
     thẳng tọa độ (`get_wave_daily_at(lat, lon)`...) + hàm wrapper theo tên
     trạm cũ (`get_wave_daily(station)`) để không phá code khác đang gọi.
   - `bulletin/marine_data.py` giờ lấy sóng/dòng chảy tại ĐÚNG tọa độ chính
     thức của từng vùng dự báo, không proxy qua trạm triều nữa (triều vẫn
     giữ nguyên cách map qua trạm quan trắc — đó là đúng phương pháp, không
     đổi).
   - **Mở rộng vùng tải dữ liệu Copernicus** (`BBOX` trong `wave_download.py`/
     `current_download.py`) từ 106.5–107.5°Đ lên 106.4–109.2°Đ để bao phủ đủ
     điểm "ngoài khơi phía Nam" — nếu không mở rộng, điểm này luôn nằm ngoài
     dữ liệu tải về và luôn ra giá trị dự phòng.
   - Thêm bản đồ (`pydeck`) trong `app.py`, hiển thị ngay dưới tiêu đề, đánh
     dấu 5 vùng dự báo kèm tên khi hover.
   ⚠️ Chưa test được `pydeck` thật (không cài được trong môi trường này) —
   bạn nên tự mở app kiểm tra bản đồ hiển thị đúng, và tải lại dữ liệu
   Copernicus (vùng tải đã đổi, cần bấm "🔄 Tải dữ liệu mới nhất" lại).

## Đã sửa theo phản hồi thực tế (triều giống nhau mọi vùng, sóng/dòng chảy = 0)

Sau khi chạy thử với dữ liệu thật, phát hiện 2 lỗi:

1. **Triều giống hệt nhau ở cả 5 vùng biển trong bảng 2/3**: nguyên nhân là
   `forecast_tide_from_observed()` trước đây chỉ chọn **1 cột trạm duy nhất**
   trong Excel (ưu tiên Cửa Việt/Cồn Cỏ), rồi `build_area_data()` dùng CHUNG
   kết quả đó cho cả 5 vùng — dù Excel có tới 4 cột trạm khác nhau. Đã sửa:
   `forecast_tide_from_observed()` nay nhận tham số `station_key`, chọn đúng
   cột theo tên trạm (`STATION_COLUMN_KEYWORDS`); `build_area_data()` tính
   triều riêng cho từng trạm thật (dùng chung bảng ánh xạ `REGION_TO_STATION`
   với `marine_data.py` để nhất quán), rồi mới gán vào đúng vùng biển tương
   ứng. Đã kiểm tra: 5 vùng nay ra giá trị khác nhau (2 vùng dùng chung trạm
   Cồn Cỏ thì giống nhau — đúng vì đó là cùng 1 trạm thật).

2. **Sóng/dòng chảy = 0 ở "ngoài khơi phía Bắc" (Đồng Hới) và "ven bờ phía
   Nam" (Cửa Việt)**: nguyên nhân là `get_wave_forecast()`/`get_current_
   forecast()` khi chọn ô lưới gần tọa độ trạm nhất (`.sel(method="nearest")`)
   mà ô đó bị NaN (đất liền) thì **gán cứng về 0** thay vì tìm ô biển hợp lệ
   khác. Đồng Hới và Cửa Việt đều là điểm sát bờ/cửa sông nên rất dễ rơi
   đúng vào ô bị model đại dương coi là đất liền. Đã sửa: thêm
   `_nearest_valid_latlon()` — nếu ô gần nhất theo tọa độ bị NaN, duyệt toàn
   bộ miền dữ liệu (nhỏ, ~vài trăm ô) tìm ô biển hợp lệ GẦN NHẤT thay thế;
   các thời điểm lẻ tẻ vẫn bị thiếu dữ liệu thì bỏ qua thay vì gán 0 (tránh
   làm sai lệch `hs_min`/`speed_min` của ngày đó). Đã kiểm thử độc lập thuật
   toán tìm ô hợp lệ bằng lưới giả lập có vùng NaN — chọn đúng ô biển gần
   nhất, không còn chọn nhầm ô đất liền.
   ⚠️ Phần xarray/`.sel()` thật chưa test được với file `.nc` thật (không có
   xarray/mạng trong môi trường này) — bạn nên tự kiểm tra lại bảng 2/3 ở
   Đồng Hới/Cửa Việt sau khi tải dữ liệu Copernicus thật.

## Đã làm trong lần này (thay mô hình triều + nối dữ liệu sóng/dòng chảy)

1. **`bulletin/tide_model.py` (mới)** — thay bản fit 6 hằng số thô sơ bằng bộ
   `models/` chuẩn (trước đây `models/` không được import ở bất kỳ đâu).
   - Thêm hiệu chỉnh **mực nước trung bình cục bộ**: kiểm định chéo (hold-out
     10 ngày cuối trên dữ liệu mẫu) cho thấy nếu dùng trung bình mực nước của
     *toàn bộ* chuỗi quan trắc (thường dài cả năm) làm mốc, sai số dự báo 10
     ngày tới lên tới **RMSE ≈ 0.23m** vì mực nước thực tế trôi theo mùa/gió
     mùa. Sửa bằng cách lấy độ lệch trung bình so với tín hiệu triều thuần
     túy trong **15 ngày quan trắc gần nhất** làm mốc — RMSE giảm còn
     **≈ 0.08m**, tương quan ~0.95 (xem code trong `tide_model.py`, hằng số
     `RECENT_BIAS_WINDOW_DAYS`).
   - Đã thêm bước QC (`core.qc.MarineQualityControl`) trước khi fit — bước
     này vốn có sẵn nhưng cũng chưa từng được gọi ở đâu.
   - **Phát hiện & sửa 1 bug có sẵn trong `core/qc.py`**:
     `auto_fix_interpolation()` bị lỗi `IndexingError: Unalignable boolean
     Series` bất kỳ khi nào có khoảng trống dữ liệu dài hơn `max_gap` — do
     `invalid_mask` chỉ mang index tại các vị trí NaN (tập con) nhưng lại
     dùng để gán trực tiếp vào Series có index đầy đủ. Bug này chưa từng lộ
     ra vì trước đây không có nơi nào gọi hàm QC này cả.
2. **`core/wave_forecast.py`, `core/current_forecast.py` (sửa)** — bản trước
   chỉ lấy **10 bước thời gian đầu tiên** của file `.nc` rồi coi đó là "10
   ngày", trong khi dữ liệu sóng lấy mẫu 3 giờ/lần và dòng chảy 1 giờ/lần —
   thực chất chỉ đọc được vài giờ đến hơn 1 ngày đầu. Nay đọc toàn bộ chuỗi
   kèm mốc thời gian thật và gộp đúng theo **ngày lịch**.
3. **`bulletin/marine_data.py` (mới)** — ánh xạ 5 vùng biển trong bản tin
   sang 4 trạm thật, gọi 2 hàm trên, quy đổi hướng (độ) sang tên hướng tiếng
   Việt, trả về đúng cấu trúc bảng 2/3 cần dùng.
4. Cả hai module đọc `.nc` đều bọc `import xarray` trong try/except — nếu môi
   trường chưa cài `xarray`/`netCDF4`, ứng dụng vẫn chạy được (dùng giá trị dự
   phòng cho phần sóng/dòng chảy) thay vì crash toàn bộ app khi khởi động.

4. **`bulletin/area_data.py` — nối `core/ai_forecaster.py` (mục 1-6 + bảng 1)**:
   - Thêm `generate_narrative_texts()` gọi trực tiếp `generate_weather_3days`,
     `generate_weather_summary`, `generate_marine_comment`, `analyze_danger`,
     `analyze_impact`, `generate_longterm_comment` với đúng phạm vi ngày cho
     từng hàm (xem giải thích ở mục "Giới hạn" phía trên).
   - Thêm `bulletin/marine_data.py::get_province_wide_daily()` tổng hợp sóng/
     dòng chảy CHUNG TOÀN TỈNH (lấy giá trị lớn nhất giữa 4 trạm mỗi ngày) ở
     đúng định dạng `{"Hs":.., "Dir":..}`/`{"Speed":.., "Dir":..}` mà các hàm
     trên yêu cầu — khác với `build_wave_current_tables()` (đã format sẵn
     thành chuỗi hiển thị cho bảng 2/3).
   - **Tránh lặp lại bug cũ**: bản tin `.docx` cũ (`HVHN_QTRI_20260721_0430.docx`)
     từng in ra `dict` Python thô ở bảng 1 và tên biến dính liền ở mục 6 do
     không trích đúng field trước khi đưa vào bảng/`Document.add_run()`. Lần
     này bảng 1 được dựng bằng cách trích rõ từng field
     (`d['Thời_tiết']`, `d['Tầm_nhìn']`...) từ danh sách dict trả về, đã kiểm
     tra bằng cách mở lại file `.docx` sinh ra và đọc từng đoạn văn.

5. **Tự động hoá tải dữ liệu Copernicus** (`core/wave_download.py`,
   `core/current_download.py` + nút "🔄 Tải dữ liệu mới nhất" ở sidebar
   trong `app.py`):
   - `core/current_download.py` bản gốc **không thực sự tải gì cả** —
     `download_current_data` chỉ là alias trỏ tới một hàm rỗng
     (`process_downloaded_current_data`, trả về `None`), kèm class
     `MarineDataProcessor` gọi `self.qc.execute_pipeline(...)` — phương thức
     không tồn tại trong `core/qc.py` (chỉ có `run_pipeline`), và tham chiếu
     tới file mẫu không có thật trong dự án. Đã xác nhận (grep toàn repo)
     không nơi nào khác import các hàm/class đó nên đã thay hẳn bằng một hàm
     tải thật, đối xứng với `wave_download.py` (cùng dùng `copernicusmarine.subset()`,
     cùng vùng biển, khác dataset/biến: `uo`,`vo` thay vì `VHM0`,`VMDR`).
   - Cả 2 hàm tải: đọc tài khoản Copernicus Marine từ **biến môi trường**
     `COPERNICUSMARINE_SERVICE_USERNAME` / `_PASSWORD` (không hard-code); nếu
     không đặt biến môi trường, dùng phiên đăng nhập đã lưu qua lệnh
     `copernicusmarine login` (đúng như bản gốc đang giả định).
   - Không tải lại nếu file `.nc` hiện có mới hơn 6 giờ (tránh gọi API không
     cần thiết mỗi lần mở app) — có thể ép tải lại bằng `force=True`.
   - Không raise exception khi tải thất bại (mất mạng, chưa đăng nhập...) —
     trả về `None` và log lỗi, để app vẫn chạy được bằng file `.nc` cũ đang
     có hoặc giá trị dự phòng, thay vì crash toàn bộ.
   - `app.py`: thêm mục ở sidebar hiển thị tuổi của file `wave.nc`/`current.nc`
     hiện có + nút tải mới, có cảnh báo rõ ràng nếu tải thất bại.

6. **`core/weather_download.py`, `core/weather_forecast.py` (mới) — nguồn dữ
   liệu khí tượng khí quyển thật đầu tiên trong dự án**:
   - Tải mưa/gió/tầm nhìn 10 ngày tới từ **Open-Meteo** (miễn phí, không cần
     API key) tại điểm đại diện tọa độ trạm Cửa Việt, cùng cơ chế an toàn như
     `wave_download.py`/`current_download.py`: không tải lại nếu file còn mới
     (<6h), không raise exception khi thất bại, đọc qua biến `hourly` của
     Open-Meteo (`precipitation`, `weathercode`, `windspeed_10m`,
     `winddirection_10m`, `visibility`).
   - `get_weather_daily()` gộp theo ngày lịch, quy đổi mã thời tiết WMO +
     tổng lượng mưa sang câu tiếng Việt, đã kiểm thử bằng dữ liệu JSON giả
     lập đúng định dạng Open-Meteo thật (3 kịch bản: nắng, mưa vừa, dông) —
     cho kết quả đúng ở cả 3 trường hợp.
   - `core.weather_analysis.generate_weather_3days()` thêm tham số
     `atmos_data` tùy chọn: dùng dữ liệu thật khi có, tự quay lại hành vi cũ
     (ngẫu nhiên) khi không có — đã kiểm thử toàn bộ pipeline
     `build_area_data()` với dữ liệu khí tượng giả lập, xác nhận bảng 1 ra
     đúng 3 ngày khác nhau theo dữ liệu, không còn giống hệt nhau.
   - Thêm vào nút "🔄 Tải dữ liệu mới nhất" ở sidebar `app.py` (tải cùng lúc
     với sóng/dòng chảy).

### ⚠️ Giới hạn đã biết / cần bạn tự kiểm tra thêm

Môi trường phát triển ở đây **không có kết nối mạng** nên không cài được
`xarray`/`netCDF4` để test đọc file `.nc` thật — toàn bộ phần mô hình triều đã
được kiểm định chéo đầy đủ (hold-out validation), nhưng phần đọc `.nc`
(`get_wave_daily`/`get_current_daily`) mới chỉ được kiểm tra logic + đường dẫn
dự phòng, **chưa chạy thử với dữ liệu Copernicus thật**. Khi chạy ở máy có cài
đủ thư viện (`pip install -r requirements.txt`), bạn nên kiểm tra lại:
- `python3 -c "from bulletin.marine_data import build_wave_current_tables; print(build_wave_current_tables())"`
  → xem các giá trị `wave_height`/`current_speed` có hợp lý (không phải toàn
  giá trị dự phòng `0.25 - 0.75m` / `0.10 - 0.30`) hay không.
- Nếu vẫn ra giá trị dự phòng dù đã có `wave.nc`/`current.nc` thật, khả năng
  cao là tên biến tọa độ hoặc tên biến sóng/dòng chảy trong file khác với
  `VHM0/VMDR/uo/vo` — thêm `print(ds)` tạm thời trong `_open_dataset` để xem
  cấu trúc thật của file.
- Tương tự, chưa test được `download_wave_data()`/`download_current_data()`
  gọi API Copernicus thật (không có mạng trong môi trường phát triển này).
  Cần chạy `copernicusmarine login` một lần trên máy thật (hoặc đặt biến môi
  trường `COPERNICUSMARINE_SERVICE_USERNAME`/`_PASSWORD`), rồi bấm nút
  "🔄 Tải dữ liệu mới nhất" ở sidebar hoặc gọi trực tiếp:
  `python3 -c "from core.wave_download import download_wave_data; print(download_wave_data(force=True))"`
- `download_weather_data()` (Open-Meteo) cũng chưa gọi API thật được — môi
  trường phát triển này tự chặn domain lạ (`host_not_allowed`, không phải lỗi
  từ Open-Meteo). Đã kiểm thử kỹ phần logic xử lý (`get_weather_daily()`)
  bằng dữ liệu JSON giả lập đúng định dạng Open-Meteo thật nên tin tưởng
  logic đúng, nhưng bạn nên tự chạy 1 lần ở máy có mạng để xác nhận cấu trúc
  JSON Open-Meteo trả về khớp 100% với những gì code kỳ vọng (đặc biệt là
  tên biến `visibility` — đây là biến mình tự tin nhưng chưa xác nhận được
  bằng tài liệu chính thức do giới hạn tìm kiếm):
  `python3 -c "from core.weather_download import download_weather_data; print(download_weather_data(force=True))"`

## Roadmap gợi ý tiếp theo

1. ~~Thay bộ triều thô sơ bằng `models/`~~ ✅ đã làm
2. ~~Nối dữ liệu sóng/dòng chảy thật vào bảng 2/3~~ ✅ đã làm (cần kiểm tra lại
   theo mục "Giới hạn đã biết" ở trên với thư viện `xarray`/`netCDF4` thật)
3. ~~Nối `core/ai_forecaster.py` cho mục 1-6 + bảng 1~~ ✅ đã làm (nhưng xem
   mục "Giới hạn thật của bảng 1" — mưa/hướng gió vẫn là suy diễn vì thiếu
   nguồn dữ liệu khí tượng khí quyển thật)
4. ~~Tự động hoá tải dữ liệu Copernicus~~ ✅ đã làm (cần kiểm tra lại ở máy có
   mạng + đã `copernicusmarine login`, xem mục "Giới hạn đã biết")
5. ~~Bổ sung nguồn dữ liệu khí tượng khí quyển thật~~ ✅ đã làm (Open-Meteo —
   cần kiểm tra lại ở máy có mạng, xem mục "Giới hạn đã biết")

Mỗi bước nên viết kèm 1-2 test nhỏ (so sánh output với 1 bộ input mẫu cố định,
hoặc hold-out validation như đã làm với `tide_model.py`) trước khi coi là
"xong", để tránh lặp lại tình trạng có code nhưng không chắc đã chạy đúng.

## Đã thêm: Bản tin THÁNG (HV1T), Bản tin MÙA (HVHM) + Hồ sơ dự báo (HS_) — MỚI

Trước lần này app chỉ sinh được 2/4 loại bản tin thật sự dùng ở đài (bản tin
10 ngày HVHV và tin nguy hiểm HVNH). Đối chiếu với 8 file mẫu thật trong
`bản_tin_hải_văn.zip` (`QTRI_HV1T_...`, `QTRI_HVHM_...`, và các file hồ sơ
`HS_QTRI_...` đi kèm), đã bổ sung:

- **`bulletin/monthly_data.py`** + **`create_qtri_monthly_bulletin()`** —
  bản tin **thời hạn THÁNG**. Bảng thủy triều chia 3 kỳ trong tháng
  (01-10/11-20/21-cuối tháng), tính THẬT bằng đúng mô hình điều hòa triều
  sẵn có (`bulletin/tide_model.py`) — mô hình thiên văn nên ngoại suy hết cả
  tháng vẫn hợp lệ. Sóng biển chỉ có nguồn thật (Copernicus, qua
  `marine_data.py`) cho khoảng 10 ngày đầu tháng; phần còn lại + các đoạn
  văn bản nhận định (mục 1-4) không có nguồn dữ liệu khí hậu/lịch sử nào
  trong dự án nên để giá trị khởi điểm rõ ràng, sửa được trực tiếp trên
  giao diện trước khi xuất — đúng nguyên tắc "không giả vờ có số liệu thật"
  đã áp dụng xuyên suốt dự án.
- **`bulletin/seasonal_data.py`** + **`create_qtri_seasonal_bulletin()`** —
  bản tin **thời hạn MÙA** (3 tháng dự báo chi tiết + 3 tháng xu thế, đúng
  cấu trúc mẫu — phần xu thế KHÔNG có bảng, chỉ văn bản, giống bản gốc).
  Bảng 1 (hồi cứu 2 tháng qua) lấy TRỰC TIẾP từ số liệu Excel thực đo người
  dùng tải lên (không qua mô hình — đây là số liệu quan trắc thật). Bảng 2
  (thủy triều Nước lớn/Nước ròng 3 tháng tới, cả 5 vùng) tính thật bằng mô
  hình điều hòa triều ngoại suy ~90 ngày. Sóng biển hồi cứu + toàn bộ nhận
  định khí hậu/XTNĐ không có nguồn nào trong dự án — để placeholder biên
  tập được.
- **`bulletin/dossier_generator.py`** — sinh **"Hồ sơ dự báo" (HS_)**, đúng
  khung hành chính 8 mục dùng chung cho cả 3 loại bản tin có mẫu thật (thu
  thập số liệu / phân tích hiện trạng / phương án dự báo / thảo luận / xây
  dựng bản tin / cung cấp bản tin / cập nhật / đánh giá chất lượng bản tin
  trước) + trang 2 "Phần ghi thảo luận dự báo". Có 3 hàm chuyển dữ liệu
  riêng từng loại (`build_warning_dossier_data`, `build_monthly_dossier_data`,
  `build_seasonal_dossier_data`) tái dùng lại đúng nội dung đã tính cho bản
  tin tương ứng — không tính lại từ đầu.
- Tách `_add_letterhead()` / `_add_footer_meta_and_signature()` trong
  `bulletin_generator.py` (trước đây 2 hàm gốc `create_qtri_bulletin` /
  `create_qtri_warning_bulletin` mỗi hàm tự dựng lại phần quốc hiệu/chữ ký,
  ~60 dòng lặp lại) để 2 bản tin mới không phải chép lại.
- **`core/beaufort.py`**: bổ sung bảng "Độ cao sóng trung bình" + "Mức độ
  nguy hại" chính thức theo file **`BẢNG_CẤP_GIÓ_VÀ_SÓNG.docx`** (Phòng
  QLMLT, Đài KTTV khu vực Trung Trung Bộ) người dùng cung cấp — thêm hàm
  `wave_height_to_beaufort()`, `sea_state_text()`, `hazard_text_for_force()`.
  Áp dụng để thay ngưỡng "Biển động/Biển động mạnh..." tự đặt trước đây
  trong `bulletin/warning_data.py` (dòng `sea_state = lambda wmax: ...`)
  bằng đúng bảng gốc — giờ toàn dự án dùng CHUNG 1 nguồn tham chiếu cho
  cách mô tả trạng thái biển, thay vì mỗi chỗ tự đặt ngưỡng khác nhau.
- `app.py`: thêm 2 expander mới **"📅 Bản tin hải văn thời hạn THÁNG"** và
  **"🌤️ Bản tin hải văn thời hạn MÙA"** (cùng luồng tính → xem trước → sửa
  trực tiếp → xuất `.docx` như 2 bản tin cũ), mỗi bản tin có thêm nút
  **"📁 Xuất hồ sơ dự báo (HS_) đi kèm"**; tin nguy hiểm (HVNH) cũng được bổ
  sung nút xuất hồ sơ tương tự. Thêm ô nhập **"Trưởng ca dự báo"** (khác với
  "Người ký" — đúng theo mẫu hồ sơ thật có 2 vai trò riêng biệt).

### Đã kiểm thử thật (không chỉ viết xong là xong)

- Chạy trực tiếp `build_monthly_data()` / `build_seasonal_data()` /
  `build_warning_dossier_data()` với `data/sample/solieu.xlsx` thật, sinh
  `.docx`, convert sang PDF bằng `libreoffice --headless` và xem ảnh từng
  trang — bảng thủy triều theo vùng/kỳ và khung hồ sơ 8 mục lên đúng cấu
  trúc mong muốn.
- Phát hiện và sửa 1 lỗi thật khi test: nếu mốc dữ liệu Excel tải lên kết
  thúc khá xa trước đầu tháng/kỳ dự báo, số ngày dự báo cố định trước đó
  không đủ phủ tới hết kỳ (kỳ 21-cuối tháng ra toàn "-") — đã sửa để tính
  số ngày dự báo cần thiết dựa trên khoảng cách thật giữa mốc dữ liệu cuối
  và cuối kỳ dự báo, không phải một số cố định.
- Chạy `app.py` qua `streamlit run` (boot sạch, không lỗi import) và qua
  `streamlit.testing.v1.AppTest` (không có exception ở lần chạy đầu) để
  xác nhận phần giao diện mới không phá app hiện có; đã rà tay toàn bộ
  `key=` của widget mới để đảm bảo không trùng với widget cũ.
- **CHƯA** test được việc bấm nút thật trong trình duyệt (môi trường phát
  triển không có UI) và **CHƯA** so khớp trực quan từng dòng với ảnh mẫu
  gốc (`QTRI_HV1T_...`, `QTRI_HVHM_...`, `HS_QTRI_...`) — chỉ so khớp cấu
  trúc mục/bảng, không so khớp chính xác từng câu chữ hành chính (số điện
  thoại, tên phòng ban nhận tin...). Bạn nên tự mở app, tải file mẫu, bấm
  thử cả 4 loại bản tin + hồ sơ trước khi dùng thật.

### Giới hạn đã biết (bản tin THÁNG/MÙA)

- Sóng biển ngoài ~10 ngày đầu tháng (bản tin tháng) hoặc toàn bộ (bản tin
  mùa) **không có nguồn dữ liệu thật nào trong dự án** (không có mô hình
  khí hậu sóng hạn dài) — luôn là giá trị khởi điểm cần dự báo viên tự
  điền theo kinh nghiệm/số liệu tham khảo riêng trước khi phát hành.
- Các đoạn văn bản nhận định synop/khí hậu (xu thế XTNĐ, triều cường dự
  kiến, tác động...) hoàn toàn thuộc nhận định nghiệp vụ — không có mô
  hình nào trong dự án tạo ra được, luôn cần dự báo viên biên tập lại.
- Hồ sơ (HS_) mới dựng đúng KHUNG bảng biểu hành chính; các trường đòi hỏi
  đánh giá riêng (nguồn ảnh mây/rada tham khảo, đánh giá chất lượng bản
  tin đã phát TRƯỚC ĐÓ) để trống/placeholder, không tự suy diễn.

## Đã sửa theo yêu cầu: quy đổi TẤT CẢ giá trị thủy triều sang mét (m)

Trước đó Bảng 2/3 của bản tin 10 ngày (HVHV) đã hiển thị mét, nhưng 2 bản
tin mới (HV1T, HVHM) vẫn còn hiển thị cm ("Hx (cm)", "Hmax (cm)"...) — đã
đồng bộ lại toàn bộ:

- `bulletin/monthly_data.py`: Hx/Hm bảng 1 (3 kỳ/tháng) đổi sang mét, 2 số
  thập phân, dùng lại đúng helper `_cm_to_m_str()` đã có sẵn trong
  `area_data.py` (không viết lại logic quy đổi).
- `bulletin/bulletin_generator.py`: Bảng 1 (HV1T), Bảng 1 + Bảng 2 (HVHM)
  đổi nhãn cột "Hx (cm)"/"Hmax (cm)"/"Hmin (cm)" → "(m)", giá trị đổi sang
  mét ngay khi render (dữ liệu nội bộ trong `*_data.py` vẫn giữ cm, đúng
  quy ước cũ của dự án — chỉ đổi đơn vị HIỂN THỊ).
- `app.py`: 2 bảng xem trước (`st.dataframe`) của bản tin MÙA cũng đổi
  sang mét, để đúng những gì dự báo viên thấy trên giao diện khớp với file
  `.docx` xuất ra.
- **Phát hiện thêm khi đối chiếu bản tin mẫu thật (`QTRI_HVHM_...`)**:
  Bảng 2 (thủy triều 3 tháng tới) có tới 18-19 cột dữ liệu (3 tháng × 6 cột
  Hx/Thời gian/Ngày/Hm/Thời gian/Ngày) — trên khổ A4 đứng, cột quá hẹp làm
  chữ ("Vùng biển ngoài khơi phía Bắc"...) bị vỡ từng ký tự một khi xuất
  PDF. Đã gộp "Thời gian" + "Ngày" thành 1 cột dạng "13h59/14" (giống cách
  Bảng 1 của bản tin THÁNG đã làm) để giảm còn 4 cột/tháng (Hx, Thời gian,
  Hm, Thời gian) và set độ rộng cột cố định (`Inches(...)`, không để
  Word/LibreOffice tự co) — đã render PDF lại và xác nhận vừa đúng khổ
  trang, không còn vỡ chữ.

## Đã sửa theo yêu cầu: căn chỉnh header + thụt đầu dòng + chia lại bảng cho khớp mẫu thật

Đối chiếu trực tiếp bằng python-docx với các file mẫu thật (`QTRI_HV1T_...`,
`QTRI_HVHM_...`, `HS_QTRI_*...`) — không đoán cấu trúc — phát hiện và sửa:

- **Header "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" không thẳng hàng với "ĐÀI
  KHÍ TƯỢNG THỦY VĂN"**: nguyên nhân là code cũ dùng 1 hàng bảng +
  `vertical_alignment=BOTTOM`, đẩy quốc hiệu xuống ngang dòng "TỈNH QUẢNG
  TRỊ" thay vì dòng đầu. Cấu trúc ĐÚNG (theo file mẫu thật) là bảng **2
  hàng x 2 cột** — hàng 1 chứa tên đơn vị/quốc hiệu (2 ô tự nhiên top-align
  theo hàng), hàng 2 chứa "Số:"/"Quảng Trị, ngày...". Đã sửa `_add_letterhead()`
  dùng chung cho CẢ 4 loại bản tin (kể cả HVHV vốn có cùng lỗi từ trước, dù
  không được nhắc riêng). Cũng bỏ gạch chân "TỈNH QUẢNG TRỊ"/"Độc lập - Tự
  do - Hạnh phúc" vì bản mẫu thật không gạch chân.
- **Thụt đầu dòng mục 3, 4 (bản tin THÁNG) và toàn bộ mục 1, 2, 3 (bản tin
  MÙA)**: các đoạn này trước đây gộp chung tiêu đề in đậm + nội dung trong
  1 paragraph nên không set được `first_line_indent` riêng cho phần nội
  dung — đã tách thành 2 paragraph (tiêu đề / nội dung thụt `Cm(1)`), đồng
  bộ với cách mục 1, 2 của bản tin THÁNG đã làm đúng từ trước.
- **Bảng 1 của bản tin MÙA chỉ có 2 tháng thay vì 3 kỳ**: mẫu thật
  (`QTRI_HVHM_20260615_1700.docx`, phát hành 15/6) có 3 cột "Tháng 4/2026",
  "Tháng 5/2026", "Từ 01-15/6/2026" — tức 2 tháng tròn liền trước + phần
  đầu THÁNG PHÁT TIN tính đến đúng ngày phát hành, không phải 2 tháng tròn
  như bản trước đây tính nhầm. Đã sửa `build_seasonal_data()` tính đúng 3
  kỳ này (thêm tham số `issue_day`, tự suy ra từ mốc cuối dữ liệu Excel nếu
  không truyền).
- **Bảng 2 của bản tin MÙA vỡ chữ / lệch cấu trúc**: mẫu thật có 6 cột con
  mỗi tháng (Hx, Thời gian, Ngày, Hm, Thời gian, Ngày — TÁCH RIÊNG "Thời
  gian" và "Ngày", không gộp như bản trước đây tự đơn giản hóa sai). Với
  5 vùng x 3 tháng x 6 cột = 19 cột, không thể vừa khổ A4 đứng. Thay vì
  tiếp tục làm sai lệch cấu trúc, đã **chuyển riêng trang chứa Bảng 2 sang
  khổ NGANG (landscape)** rồi chuyển lại khổ đứng ngay sau — đúng kỹ thuật
  phổ biến với bảng rộng trong văn bản hành chính, giữ nguyên đúng 6 cột
  con/tháng theo mẫu thật mà không vỡ chữ. Tách thành hàm dùng chung
  `_add_seasonal_tide_table()`.
- **Hồ sơ dự báo (HS_) của bản tin THÁNG và MÙA dùng sai cấu trúc bảng**:
  đối chiếu 3 file `HS_QTRI_*` mẫu thật phát hiện có **2 kiểu khác nhau**:
  HVNH dùng bảng 4 cột kiểu "Hoàn thành trước giờ phát tin X'" + hàng "Kết
  luận" (đúng như bản cũ đã làm); còn HV1T và HVHM dùng bảng **3 cột** với
  mã a/b/c/d, KHÔNG có hàng "Kết luận" riêng, mục 3 nhóm theo "Phương án
  1/2" (HV1T) hoặc "Dự báo sóng, dòng chảy"/"Dự báo thuỷ triều" (HVHM).
  Viết lại `dossier_generator.py` hỗ trợ cả 2 kiểu qua tham số `style`
  ('detailed' cho HVNH, 'simple' cho HV1T/HVHM), cập nhật
  `build_monthly_dossier_data()`/`build_seasonal_dossier_data()` theo đúng
  nội dung mục thật (mã a/b/c, mục 4 có thêm mục con a/b/c cho HV1T).
- **Trang 2 hồ sơ ("Phần ghi thảo luận dự báo") trước đây dùng bảng gió/
  sóng chung chung**: cả 3 file mẫu thật đều NHÚNG LẠI nguyên bảng vùng
  biển của chính bản tin (Bảng 1 cho HV1T, Bảng 2 cho HVHM) chứ không phải
  bảng khác. Đã tách `_add_monthly_zone_table()`/`_add_seasonal_tide_table()`
  thành hàm dùng chung giữa bản tin chính và hồ sơ, để trang 2 hồ sơ nhúng
  đúng bảng thật (kể cả phần chuyển khổ ngang cho Bảng 2 mùa).

### Đã kiểm thử thật

Render toàn bộ 4 loại bản tin + 3 loại hồ sơ ra PDF bằng LibreOffice và xem
từng trang: xác nhận header thẳng hàng đúng ở cả 4 bản tin, mục 3/4 (tháng)
và mục 1-3 (mùa) đã thụt đầu dòng, Bảng 1 mùa hiện đúng 3 kỳ, Bảng 2 mùa
hiện đủ 6 cột/tháng không vỡ chữ trên trang ngang rồi quay lại đúng khổ
đứng, hồ sơ HV1T/HVHM lên đúng bảng 3 cột mã a/b/c và trang 2 nhúng đúng
bảng vùng biển thật. `app.py` chạy lại qua `AppTest`, không phát sinh lỗi.

## Đã sửa theo yêu cầu: gộp ô trống hồ sơ tin nguy hiểm + thêm Phụ lục 1/2 hồ sơ mùa

- **Hồ sơ tin gió mạnh, sóng lớn (HVNH) — "nhiều ô trống chưa gộp lại"**:
  đối chiếu lại bằng python-docx phát hiện bảng 4 cột thật sự gộp cột 1+2
  làm MỘT ô nhãn rộng hơn ở mọi hàng thường, và gộp cả cột 0+1+2 ở hàng
  "Kết luận"/tiêu đề mục — code cũ chỉ điền cột 1, để cột 2 trống tách biệt
  chạy dọc suốt bảng. Đã sửa `_add_row()` (gộp cột 1+2) và thêm
  `_add_conclusion_row()` (gộp cột 0+1+2 cho hàng "Kết luận"), cả 3 tiêu đề
  mục 1/2/3 cũng gộp đủ 4 cột thay vì để trống 3 ô bên cạnh.
- **Hồ sơ mùa (HVHM) — thiếu Phụ lục 1 & Phụ lục 2**: đối chiếu ảnh mẫu
  thật người dùng cung cấp + file `HS_QTRI_HVHM_...` phát hiện trang thảo
  luận phải có thêm 2 bảng phụ lục thủy triều 3 tháng — **"Phụ lục 1: Kết
  quả dự báo theo phương pháp phân tích hàm điều hòa"** và **"Phụ lục 2:
  Chọn kết quả dự báo"** — dùng đơn vị **cm** (không phải mét như Bảng 2
  của bản tin chính, đúng ghi chú gốc "(cm)"), cấu trúc giống Bảng 2 nhưng
  lặp lại 2 lần. Đã thêm `_add_seasonal_appendix_tables()` (dùng chung khổ
  ngang + hàm dựng bảng `_render_tide_zone_table()` mới tách ra để tái sử
  dụng giữa Bảng 2 mét và Phụ lục cm), và câu dẫn "Sau khi thảo luận,
  trưởng ca dự báo chốt trị số ... theo phụ lục 2." trước bảng, đúng mẫu.
  Vì dự án chỉ có 1 phương pháp tính triều thật (mô hình điều hòa), Phụ lục
  2 dùng lại đúng kết quả của Phụ lục 1 — không bịa thêm phương án "mô hình
  số trị" không tồn tại trong dự án.

### Đã kiểm thử thật
Render lại cả 2 hồ sơ (HVNH, HVHM) ra PDF và xem từng trang: bảng HVNH
không còn cột trống tách biệt, tiêu đề mục gộp đủ 4 cột; hồ sơ HVHM có
thêm trang khổ ngang chứa đúng Phụ lục 1 + Phụ lục 2 (đơn vị cm, đúng ghi
chú), quay lại đúng khổ đứng sau đó. Chạy lại toàn bộ 4 bản tin + 3 hồ sơ
và `app.py` qua `AppTest` — không lỗi.

## Đã sửa theo yêu cầu: gạch chân "TỈNH QUẢNG TRỊ" / "Độc lập - Tự do - Hạnh phúc"

Theo ảnh mẫu người dùng cung cấp, 2 dòng "TỈNH QUẢNG TRỊ" (đơn vị) và "Độc
lập - Tự do - Hạnh phúc" (quốc hiệu) cần in đậm VÀ gạch chân — đã thêm lại
`underline=True` cho 2 run này trong `_add_letterhead()` (dùng chung cho cả
4 loại bản tin, nên áp dụng đồng bộ ngay). Lưu ý: lần kiểm tra trước đó
bằng python-docx trên 1 file mẫu thô không thấy `<w:u>` nên đã bỏ gạch
chân — lần này ưu tiên theo xác nhận trực tiếp của người dùng (khả năng
file mẫu gốc có nhiều phiên bản/đơn vị soạn khác nhau).
