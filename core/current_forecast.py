import os
import math

import numpy as np
import pandas as pd

from station_config import STATIONS

try:
    import xarray as xr
    _XARRAY_AVAILABLE = True
except ImportError:  # môi trường chưa cài xarray -> dùng dự phòng, không crash app
    xr = None
    _XARRAY_AVAILABLE = False


def _open_dataset(ncfile):
    ds = None
    for engine in ("netcdf4", "h5netcdf", "scipy", None):
        try:
            ds = xr.open_dataset(ncfile, engine=engine) if engine else xr.open_dataset(ncfile)
            break
        except Exception:
            continue
    return ds


def _nearest_valid_latlon(ds, lat, lon, lat_name, lon_name, var_name):
    """Tìm tọa độ ô lưới biển hợp lệ (không NaN) gần trạm nhất — xem giải
    thích chi tiết trong core/wave_forecast.py::_nearest_valid_latlon()
    (giống hệt, chỉ khác biến kiểm tra: "uo" thay vì "VHM0")."""
    ref = ds[var_name]
    if "time" in ref.dims:
        ref = ref.isel(time=0)
    if "depth" in ref.dims:
        ref = ref.isel(depth=0)
    ref = ref.transpose(lat_name, lon_name)

    values = ref.values
    lat_vals = ds[lat_name].values
    lon_vals = ds[lon_name].values

    valid_mask = ~np.isnan(values)
    if not valid_mask.any():
        return None

    lat_grid, lon_grid = np.meshgrid(lat_vals, lon_vals, indexing="ij")
    dist2 = (lat_grid - lat) ** 2 + (lon_grid - lon) ** 2
    dist2 = np.where(valid_mask, dist2, np.inf)

    flat_idx = int(np.argmin(dist2))
    i, j = np.unravel_index(flat_idx, dist2.shape)
    return float(lat_vals[i]), float(lon_vals[j])


def get_current_forecast_at(ncfile, lat, lon):
    """
    Đọc TOÀN BỘ chuỗi thời gian dòng chảy tại tọa độ (lat, lon) bất kỳ từ
    file .nc. Trả về list[dict]: {"time": Timestamp, "Speed": float, "Dir": float}

    LƯU Ý: bản trước đây chỉ lấy `min(10, len(u))` bước thời gian đầu tiên
    rồi coi đó là "10 ngày" — trong khi dataset dòng chảy Copernicus lấy mẫu
    1 giờ/lần (xem config.CURRENT_DATASET, hậu tố PT1H-m), nên thực chất chỉ
    đọc được 10 giờ đầu. Bản này đọc toàn bộ và để get_current_daily() gộp
    đúng theo ngày lịch dựa trên mốc thời gian thật trong file.
    """
    if not _XARRAY_AVAILABLE:
        return []

    if not ncfile or not os.path.exists(str(ncfile)) or os.path.getsize(str(ncfile)) == 0:
        return []

    ds = _open_dataset(ncfile)
    if ds is None:
        return []

    try:
        lat_name = "latitude" if "latitude" in ds.coords else "lat"
        lon_name = "longitude" if "longitude" in ds.coords else "lon"

        if "uo" not in ds.variables or "vo" not in ds.variables:
            return []

        point = ds.sel({lat_name: lat, lon_name: lon}, method="nearest")

        # Nếu ô gần nhất theo tọa độ toàn NaN (trạm/vùng gần bờ, cửa sông,
        # hoặc ở rìa miền dữ liệu tải về), tìm ô biển hợp lệ gần nhất thay thế.
        check = point["uo"]
        if "time" in check.dims:
            check = check.isel(time=0)
        if "depth" in check.dims:
            check = check.isel(depth=0)
        if bool(np.isnan(check.values)):
            nearest_valid = _nearest_valid_latlon(ds, lat, lon, lat_name, lon_name, "uo")
            if nearest_valid is not None:
                valid_lat, valid_lon = nearest_valid
                point = ds.sel({lat_name: valid_lat, lon_name: valid_lon})

        if "depth" in point.dims:
            point = point.isel(depth=0)

        if "time" not in point.coords:
            return []

        u = point["uo"].values
        v = point["vo"].values

        u = np.atleast_1d(u).astype(float)
        v = np.atleast_1d(v).astype(float)
        times = pd.to_datetime(point["time"].values)

        result = []
        for i in range(len(u)):
            if math.isnan(u[i]) or math.isnan(v[i]):
                # Bỏ qua thời điểm lẻ tẻ bị thiếu dữ liệu thay vì gán cứng =
                # 0 (một giá trị 0 lọt vào sẽ làm sai lệch speed_min/speed_max
                # của get_current_daily).
                continue
            speed_val = round(float(np.sqrt(u[i] ** 2 + v[i] ** 2)), 2)
            dir_val = float((270 - np.degrees(np.arctan2(v[i], u[i]))) % 360)
            result.append({"time": times[i], "Speed": speed_val, "Dir": dir_val})

        return result

    except Exception:
        return []
    finally:
        if ds is not None:
            ds.close()


def get_current_forecast(ncfile, station):
    """Wrapper tiện dụng: tra tọa độ trạm trong station_config.STATIONS rồi
    gọi get_current_forecast_at(). Giữ lại cho code cũ còn gọi theo tên trạm."""
    if station not in STATIONS:
        return []
    return get_current_forecast_at(ncfile, STATIONS[station]["lat"], STATIONS[station]["lon"])


def get_current_daily_at(ncfile, lat, lon, days=10):
    """
    Gộp chuỗi dòng chảy thật tại tọa độ (lat, lon) theo TỪNG NGÀY lịch, trả
    về đúng `days` phần tử:
        [{"date": date|None, "speed_min": .., "speed_max": .., "dir_deg": ..}, ...]

    Nếu không đọc được dữ liệu thật, trả về giá trị dự phòng an toàn.
    """
    fallback = [
        {"date": None, "speed_min": 0.10, "speed_max": 0.30, "dir_deg": 90.0}
        for _ in range(days)
    ]

    raw = get_current_forecast_at(ncfile, lat, lon)
    if not raw:
        return fallback

    df = pd.DataFrame(raw)
    df["date"] = df["time"].dt.date

    result = []
    for d, g in df.groupby("date", sort=True):
        idx_max = g["Speed"].idxmax()
        result.append({
            "date": d,
            "speed_min": round(float(g["Speed"].min()), 2),
            "speed_max": round(float(g["Speed"].max()), 2),
            # hướng dòng chảy đại diện: tại thời điểm tốc độ lớn nhất trong ngày
            "dir_deg": float(g.loc[idx_max, "Dir"]),
        })
        if len(result) >= days:
            break

    if not result:
        return fallback

    while len(result) < days:
        result.append(result[-1])

    return result


def get_current_daily(ncfile, station, days=10):
    """Wrapper tiện dụng: tra tọa độ trạm trong station_config.STATIONS rồi
    gọi get_current_daily_at(). Giữ lại cho code cũ còn gọi theo tên trạm."""
    if station not in STATIONS:
        return [
            {"date": None, "speed_min": 0.10, "speed_max": 0.30, "dir_deg": 90.0}
            for _ in range(days)
        ]
    return get_current_daily_at(ncfile, STATIONS[station]["lat"], STATIONS[station]["lon"], days=days)
