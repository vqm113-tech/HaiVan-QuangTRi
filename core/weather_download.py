# ==========================================
# core/weather_download.py
# Tải dữ liệu khí tượng khí quyển THẬT (mưa, gió, tầm nhìn) từ Open-Meteo
# (https://open-meteo.com) — API thời tiết miễn phí, KHÔNG cần đăng ký/API
# key, khác với Copernicus Marine (cần tài khoản) dùng cho sóng/dòng chảy
# đại dương.
#
# Đây là nguồn dữ liệu khí tượng khí quyển ĐẦU TIÊN trong dự án — trước đây
# hệ thống hoàn toàn không có (chỉ có sóng/dòng chảy/triều), nên "Thời tiết"/
# "Tầm nhìn"/hướng gió trong bảng 1 của bản tin là suy diễn/giả định (xem
# README). Module này lấp khoảng trống đó.
# ==========================================

import json
import logging
import time

from config import DATA_DIR

logger = logging.getLogger(__name__)

WEATHER_DIR = DATA_DIR / "weather_data"
WEATHER_DIR.mkdir(parents=True, exist_ok=True)
WEATHER_FILE = WEATHER_DIR / "weather.json"

# Điểm đại diện lấy dữ liệu khí tượng cho toàn tỉnh: tọa độ trạm Cửa Việt
# (ven bờ, gần khu dân cư/tàu thuyền hoạt động chính) — xem station_config.STATIONS.
REPRESENTATIVE_LAT = 16.87
REPRESENTATIVE_LON = 107.12

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _is_fresh(path, max_age_hours):
    if not path.exists():
        return False
    age_hours = (time.time() - path.stat().st_mtime) / 3600.0
    return age_hours < max_age_hours


def download_weather_data(forecast_days=10, force=False, max_age_hours=6, timeout=15):
    """
    Tải dữ liệu mưa/gió/tầm nhìn `forecast_days` ngày tới từ Open-Meteo, tại
    điểm đại diện vùng biển Quảng Trị (Cửa Việt).

    Trả về đường dẫn file JSON đã lưu nếu thành công, None nếu thất bại (mất
    mạng, tham số API không hợp lệ, đổi định dạng phản hồi...) — hàm này
    KHÔNG raise exception để không làm gãy luồng chính của app; bên gọi tự
    quyết định dùng file cũ đang có (nếu có) hay giá trị dự phòng.

    force=False (mặc định): bỏ qua tải nếu file hiện có còn mới hơn
    `max_age_hours` giờ.
    """
    if not force and _is_fresh(WEATHER_FILE, max_age_hours):
        logger.info("Bỏ qua tải khí tượng: %s còn mới (< %sh)", WEATHER_FILE, max_age_hours)
        return WEATHER_FILE

    try:
        import requests
    except ImportError:
        logger.warning("Chưa cài đặt thư viện requests (pip install requests).")
        return None

    params = {
        "latitude": REPRESENTATIVE_LAT,
        "longitude": REPRESENTATIVE_LON,
        "hourly": "precipitation,weathercode,windspeed_10m,winddirection_10m,visibility",
        "windspeed_unit": "ms",
        "timezone": "Asia/Ho_Chi_Minh",
        "forecast_days": min(max(int(forecast_days), 1), 16),  # Open-Meteo tối đa 16 ngày
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        if "hourly" not in data or "time" not in data.get("hourly", {}):
            logger.error("Phản hồi Open-Meteo thiếu dữ liệu 'hourly': %s", data)
            return None

        WEATHER_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        logger.info("Đã tải dữ liệu khí tượng Open-Meteo -> %s", WEATHER_FILE)
        return WEATHER_FILE

    except Exception as exc:
        logger.error("Tải dữ liệu khí tượng Open-Meteo thất bại: %s", exc)
        return None
