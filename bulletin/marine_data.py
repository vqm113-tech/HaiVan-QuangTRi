# ==========================================
# bulletin/marine_data.py
# Nối dữ liệu sóng & dòng chảy THẬT (Copernicus .nc) vào các bảng của bản tin,
# thay cho số liệu cố định trước đây trong area_data.py.
# ==========================================

from __future__ import annotations

from config import WAVE_FILE, CURRENT_FILE
from core.wave_forecast import get_wave_daily_at, _floor_to_005, _ceil_to_005
from core.current_forecast import get_current_daily_at
from station_config import FORECAST_REGIONS

# REGION_TO_STATION dùng RIÊNG cho THỦY TRIỀU (bulletin/area_data.py): mỗi
# vùng dự báo được gán về trạm đo triều thực tế gần nhất trong 4 trạm hiện
# có (tan_my, dong_hoi, cua_viet, con_co) — đây là phương pháp đúng vì triều
# là số liệu quan trắc tại trạm, không có ở ngoài khơi.
# "offshore_south" và "con_co" cùng dùng trạm Cồn Cỏ vì đây là trạm duy nhất
# ở phía Nam ngoài khơi hiện có.
REGION_TO_STATION = {
    "offshore_north": "dong_hoi",   # Đồng Hới -> vùng "ngoại khơi phía Bắc"
    "offshore_south": "con_co",     # Cồn Cỏ   -> vùng "ngoài khơi phía Nam"
    "coastal_north": "tan_my",      # Tân Mỹ   -> vùng "ven bờ phía Bắc"
    "coastal_south": "cua_viet",    # Cửa Việt -> vùng "ven bờ phía Nam"
    "con_co": "con_co",             # Cồn Cỏ (đúng trạm)
}

# SÓNG/DÒNG CHẢY thì dùng THẲNG tọa độ chính thức của từng vùng dự báo
# (FORECAST_REGIONS, station_config.py) — không cần proxy qua trạm triều vì
# đây là dữ liệu mô hình đại dương (Copernicus) tại tọa độ ngoài khơi, không
# gắn với vị trí trạm đo triều ven bờ. Trước đây có dùng trạm triều làm proxy
# nhưng tọa độ lệch khá xa (ví dụ "ngoài khơi phía Nam" cách trạm Cồn Cỏ hơn
# 150km) nên đã bỏ cách proxy này.

_DIRECTION_LABELS = [
    "Bắc", "Đông Bắc", "Đông", "Đông Nam",
    "Nam", "Tây Nam", "Tây", "Tây Bắc",
]


def degrees_to_text(deg) -> str:
    """Quy đổi hướng (độ, 0-360) sang tên hướng 8 điểm tiếng Việt."""
    if deg is None:
        return "-"
    try:
        deg = float(deg)
    except (TypeError, ValueError):
        return "-"
    if deg != deg:  # NaN
        return "-"
    idx = int(((deg % 360) + 22.5) // 45) % 8
    return _DIRECTION_LABELS[idx]


def _scale_for(scale, region_key):
    """Lấy hệ số hiệu chỉnh cho đúng vùng `region_key`. `scale` có thể là:
    - None hoặc số (float/int): áp dụng CHUNG cho mọi vùng (tương thích ngược).
    - dict {region_key: hệ_số}: áp dụng RIÊNG từng vùng, vùng không có trong
      dict giữ nguyên 1.0 (không đổi)."""
    if scale is None:
        return 1.0
    if isinstance(scale, dict):
        return float(scale.get(region_key, 1.0))
    return float(scale)


def build_wave_current_tables(forecast_days: int = 10, wave_scale=1.0, current_scale=1.0) -> dict:
    """
    Đọc file .nc sóng/dòng chảy thật tại đúng TỌA ĐỘ CHÍNH THỨC của từng
    vùng biển dự báo (FORECAST_REGIONS) trong bản tin.

    wave_scale, current_scale : hệ số nhân do dự báo viên tự hiệu chỉnh —
        RIÊNG cho từng vùng biển. Có thể truyền:
        - 1 số (float): áp dụng chung cho mọi vùng (ví dụ 1.2 cho tất cả).
        - dict {region_key: hệ_số}: áp dụng riêng từng vùng, ví dụ
          {"offshore_north": 1.2, "coastal_south": 0.9} — các vùng không có
          trong dict giữ nguyên (hệ số 1.0).
        Ví dụ: dự báo gốc H = 0.5 - 1.5m, hệ số 1.2 -> hiển thị H =
        0.6 - 1.8m. Mặc định 1.0 = không đổi.

    Trả về:
        {
          region_key: {
            "wave_height": ["0.25 - 0.75m", ...]   (độ dài forecast_days)
            "wave_dir":    ["Đông Bắc", ...]
            "current_speed": ["0.10 - 0.30", ...]
            "current_dir":   ["Nam", ...]
          },
          ...
        }

    Nếu không đọc được file .nc thật (thiếu thư viện xarray/netCDF4, chưa tải
    dữ liệu Copernicus, tọa độ ngoài phạm vi dataset đã tải về...), các hàm
    con get_wave_daily_at()/get_current_daily_at() tự trả về giá trị dự
    phòng an toàn nên hàm này luôn trả về đủ cấu trúc, không bao giờ raise.
    """
    tables = {}

    for region_key, region in FORECAST_REGIONS.items():
        lat, lon = region["lat"], region["lon"]
        w_scale = _scale_for(wave_scale, region_key)
        c_scale = _scale_for(current_scale, region_key)

        wave_daily = get_wave_daily_at(str(WAVE_FILE), lat, lon, days=forecast_days)
        current_daily = get_current_daily_at(str(CURRENT_FILE), lat, lon, days=forecast_days)

        wave_height, wave_dir = [], []
        for w in wave_daily:
            # Làm tròn về bậc 0.05m SAU KHI đã nhân hệ số hiệu chỉnh
            # (w_scale) -- hệ số hiệu chỉnh có thể làm lệch khỏi bậc 0.05
            # dù giá trị gốc đã tròn, nên phải tròn lại ở bước cuối này.
            # hs_min làm tròn XUỐNG, hs_max làm tròn LÊN (mở rộng khoảng dự
            # báo ra 2 phía, đúng tinh thần "phổ biến từ ... đến ...").
            hs_min = _floor_to_005(w['hs_min'] * w_scale)
            hs_max = _ceil_to_005(w['hs_max'] * w_scale)
            wave_height.append(f"{hs_min:.2f} - {hs_max:.2f}")
            wave_dir.append(degrees_to_text(w["dir_deg"]))

        current_speed, current_dir = [], []
        for c in current_daily:
            speed_min = c['speed_min'] * c_scale
            speed_max = c['speed_max'] * c_scale
            current_speed.append(f"{speed_min:.2f} - {speed_max:.2f}")
            current_dir.append(degrees_to_text(c["dir_deg"]))

        tables[region_key] = {
            "wave_height": wave_height,
            "wave_dir": wave_dir,
            "current_speed": current_speed,
            "current_dir": current_dir,
        }

    return tables


def get_province_wide_daily(forecast_days: int = 10, wave_scale=1.0, current_scale=1.0):
    """
    Tổng hợp dữ liệu sóng/dòng chảy CHUNG TOÀN TỈNH (không tách theo vùng
    biển như build_wave_current_tables), dùng để cấp cho các hàm sinh văn
    bản tường thuật mục 1-6 trong core/ai_forecaster.py — các hàm đó cần
    đúng định dạng [{"Hs": .., "Dir": ..}, ...] / [{"Speed": .., "Dir": ..}, ...]
    (khác với build_wave_current_tables() vốn trả về chuỗi đã format sẵn).

    wave_scale, current_scale : hệ số nhân hiệu chỉnh — xem giải thích trong
        build_wave_current_tables() (chấp nhận số đơn hoặc dict theo vùng).
        Áp dụng cho TỪNG VÙNG trước khi chọn giá trị lớn nhất giữa các vùng,
        để văn bản tường thuật phản ánh đúng hiệu chỉnh riêng từng nơi.

    Mỗi ngày lấy giá trị LỚN NHẤT giữa 5 vùng dự báo (FORECAST_REGIONS) sau
    khi đã hiệu chỉnh — theo hướng an toàn/cảnh báo cho văn bản tường thuật
    chung, phù hợp tinh thần "phổ biến ... cao nhất" của bản tin.

    Trả về (wave_list, current_list), độ dài forecast_days mỗi cái:
        wave_list:    [{"Hs": hs_max, "Hs_min": hs_min, "Dir": dir_deg}, ...]
        current_list: [{"Speed": speed_max, "Dir": dir_deg}, ...]
    """
    per_region_wave = {
        key: get_wave_daily_at(str(WAVE_FILE), r["lat"], r["lon"], days=forecast_days)
        for key, r in FORECAST_REGIONS.items()
    }
    per_region_current = {
        key: get_current_daily_at(str(CURRENT_FILE), r["lat"], r["lon"], days=forecast_days)
        for key, r in FORECAST_REGIONS.items()
    }

    wave_list, current_list = [], []
    for i in range(forecast_days):
        day_w = [
            {**per_region_wave[k][i],
             # Làm tròn về bậc 0.05m NGAY TẠI ĐÂY để mọi văn bản tường
             # thuật lấy từ get_province_wide_daily() (mục 1-6, "wave_today"
             # dùng trong sec1_text...) đều nhất quán với Bảng 2/3 -- xem
             # giải thích chi tiết trong build_wave_current_tables() ở trên.
             "hs_min": _floor_to_005(per_region_wave[k][i]["hs_min"] * _scale_for(wave_scale, k)),
             "hs_max": _ceil_to_005(per_region_wave[k][i]["hs_max"] * _scale_for(wave_scale, k))}
            for k in FORECAST_REGIONS
        ]
        best_w = max(day_w, key=lambda d: d["hs_max"])
        wave_list.append({
            "Hs": best_w["hs_max"],
            "Hs_min": min(d["hs_min"] for d in day_w),
            "Dir": best_w["dir_deg"],
        })

        day_c = [
            {**per_region_current[k][i],
             "speed_min": per_region_current[k][i]["speed_min"] * _scale_for(current_scale, k),
             "speed_max": per_region_current[k][i]["speed_max"] * _scale_for(current_scale, k)}
            for k in FORECAST_REGIONS
        ]
        best_c = max(day_c, key=lambda d: d["speed_max"])
        current_list.append({
            "Speed": best_c["speed_max"],
            "Dir": best_c["dir_deg"],
        })

    return wave_list, current_list
