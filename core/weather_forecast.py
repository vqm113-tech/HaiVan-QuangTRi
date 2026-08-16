# ==========================================
# core/weather_forecast.py
# Đọc dữ liệu khí tượng đã tải (core/weather_download.py) và gộp theo TỪNG
# NGÀY lịch: lượng mưa, gió, tầm nhìn, mã thời tiết WMO -> câu tiếng Việt.
# ==========================================

import json
import logging

import pandas as pd

from core.weather_download import WEATHER_FILE

logger = logging.getLogger(__name__)

_DIRECTION_LABELS = [
    "Bắc", "Đông Bắc", "Đông", "Đông Nam",
    "Nam", "Tây Nam", "Tây", "Tây Bắc",
]


def _degrees_to_text(deg):
    if deg is None or deg != deg:  # None hoặc NaN
        return "Đông Bắc"
    idx = int(((deg % 360) + 22.5) // 45) % 8
    return _DIRECTION_LABELS[idx]


_VISIBILITY_LEVELS = ["Dưới 1 km", "1 - 4 km", "4 - 10 km", "Trên 10 km"]


def _visibility_text(vis_m):
    """vis_m: tầm nhìn (mét) — lấy giá trị THẤP NHẤT trong ngày (bảo thủ).

    Sau khi xác định đúng cấp tầm nhìn theo số đo thật, CỘNG THÊM 1 CẤP
    trước khi hiển thị trong bản tin (theo yêu cầu nghiệp vụ — dự báo tầm
    nhìn xa hơn 1 bậc so với cấp đo được, ví dụ đo được "1 - 4 km" thì bản
    tin ghi "4 - 10 km"). Cấp cao nhất ("Trên 10 km") giữ nguyên, không có
    cấp nào cao hơn để cộng thêm.
    """
    if vis_m is None or vis_m != vis_m:
        return _VISIBILITY_LEVELS[-1]

    vis_km = vis_m / 1000.0
    if vis_km < 1:
        level = 0
    elif vis_km < 4:
        level = 1
    elif vis_km < 10:
        level = 2
    else:
        level = 3

    level = min(level + 1, len(_VISIBILITY_LEVELS) - 1)
    return _VISIBILITY_LEVELS[level]


def _weather_text(weathercode, precip_sum_mm):
    """
    Quy đổi mã thời tiết WMO (weathercode, theo bảng chuẩn của Open-Meteo:
    https://open-meteo.com/en/docs mục weathercode) + tổng lượng mưa trong
    ngày sang câu mô tả tiếng Việt.
    """
    try:
        code = int(weathercode) if weathercode == weathercode else 0
    except (TypeError, ValueError):
        code = 0

    is_thunder = code in (95, 96, 99)
    is_rain_code = code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82)
    is_fog = code in (45, 48)
    is_rain = is_rain_code or precip_sum_mm >= 1.0

    if is_thunder:
        return "Có mưa rào và dông"
    if is_fog:
        return "Sương mù, tầm nhìn hạn chế"
    if is_rain and precip_sum_mm >= 20:
        return "Mưa vừa đến mưa to"
    if is_rain:
        return "Có mưa rào rải rác"
    if code in (1, 2, 3):
        return "Mây thay đổi, không mưa"
    return "Trời quang, không mưa"


def get_weather_daily(days=10):
    """
    Đọc file JSON khí tượng đã tải, gộp theo từng ngày lịch.

    Trả về list[dict] độ dài `days`, mỗi phần tử:
        {"date": date, "Thời_tiết": str, "Tầm_nhìn": str,
         "wind_speed_ms": float, "wind_dir_text": str}

    Trả về None nếu chưa tải dữ liệu hoặc đọc lỗi — bên gọi
    (core/weather_analysis.py) tự dùng phương án dự phòng (ngẫu nhiên như
    bản gốc) khi đó.
    """
    if not WEATHER_FILE.exists():
        return None

    try:
        raw = json.loads(WEATHER_FILE.read_text(encoding="utf-8"))
        hourly = raw["hourly"]
        n = len(hourly["time"])
        df = pd.DataFrame({
            "time": pd.to_datetime(hourly["time"]),
            "precip": hourly.get("precipitation", [None] * n),
            "code": hourly.get("weathercode", [None] * n),
            "wind_speed": hourly.get("windspeed_10m", [None] * n),
            "wind_dir": hourly.get("winddirection_10m", [None] * n),
            "visibility": hourly.get("visibility", [None] * n),
        })
    except Exception as exc:
        logger.error("Đọc dữ liệu khí tượng đã tải thất bại: %s", exc)
        return None

    if df.empty:
        return None

    df["date"] = df["time"].dt.date
    result = []
    for d, g in df.groupby("date", sort=True):
        precip_sum = float(pd.to_numeric(g["precip"], errors="coerce").sum())
        wind_speed_series = pd.to_numeric(g["wind_speed"], errors="coerce")
        wind_speed_max = float(wind_speed_series.max()) if wind_speed_series.notna().any() else 0.0

        wind_dir_series = pd.to_numeric(g["wind_dir"], errors="coerce")
        if wind_speed_series.notna().any() and wind_dir_series.notna().any():
            wind_dir_deg = float(wind_dir_series.loc[wind_speed_series.idxmax()])
        else:
            wind_dir_deg = None

        vis_series = pd.to_numeric(g["visibility"], errors="coerce")
        vis_min = float(vis_series.min()) if vis_series.notna().any() else None

        code_series = pd.to_numeric(g["code"], errors="coerce").dropna()
        code = float(code_series.mode().iloc[0]) if not code_series.empty else 0.0

        result.append({
            "date": d,
            "Thời_tiết": _weather_text(code, precip_sum),
            "Tầm_nhìn": _visibility_text(vis_min),
            "wind_speed_ms": wind_speed_max,
            "wind_dir_text": _degrees_to_text(wind_dir_deg),
        })
        if len(result) >= days:
            break

    if not result:
        return None

    while len(result) < days:
        result.append(result[-1])

    return result
