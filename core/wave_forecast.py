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
    """Mở file .nc, thử lần lượt nhiều engine (dữ liệu Copernicus thường là
    NetCDF4/HDF5, không đọc được bằng scipy)."""
    ds = None
    for engine in ("netcdf4", "h5netcdf", "scipy", None):
        try:
            ds = xr.open_dataset(ncfile, engine=engine) if engine else xr.open_dataset(ncfile)
            break
        except Exception:
            continue
    return ds


def _nearest_valid_latlon(ds, lat, lon, lat_name, lon_name, var_name):
    """
    Tìm tọa độ (lat, lon) của ô lưới GẦN TRẠM NHẤT trong số các ô có dữ liệu
    hợp lệ (không NaN) cho biến `var_name`, thay vì chỉ lấy ô gần nhất theo
    khoảng cách tọa độ thuần túy (`.sel(method="nearest")`) — cách cũ có thể
    rơi đúng vào ô bị coi là đất liền (toàn NaN) đối với các trạm sát bờ/cửa
    sông như Đồng Hới, Cửa Việt, khiến sóng/dòng chảy bị gán cứng = 0.

    Miền dữ liệu Copernicus tải cho vùng biển Quảng Trị chỉ ~1 x 1.5 độ (vài
    trăm ô lưới) nên duyệt toàn bộ miền bằng numpy là đủ nhanh, không cần
    thuật toán mở rộng bán kính tìm kiếm phức tạp.

    Trả về (lat, lon) của ô hợp lệ gần nhất, hoặc None nếu CẢ FILE không có
    ô nào hợp lệ cho biến này (khi đó bên gọi coi như không có dữ liệu).
    """
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


def _floor_to_005(x):
    """Làm tròn XUỐNG bậc 0.05m gần nhất — dùng cho giá trị sóng NHỎ NHẤT
    (hs_min), ví dụ 0.57 -> 0.55. Nhân/chia qua bước trung gian round(...,6)
    để tránh sai số dấu phẩy động (0.57/0.05 có thể ra 11.399999999...)."""
    return round(math.floor(round(x / 0.05, 6)) * 0.05, 2)


def _ceil_to_005(x):
    """Làm tròn LÊN bậc 0.05m gần nhất — dùng cho giá trị sóng LỚN NHẤT
    (hs_max), ví dụ 0.82 -> 0.85."""
    return round(math.ceil(round(x / 0.05, 6)) * 0.05, 2)


def get_wave_forecast_at(ncfile, lat, lon):
    """
    Đọc TOÀN BỘ chuỗi thời gian sóng tại tọa độ (lat, lon) bất kỳ từ file .nc.
    Trả về list[dict]: {"time": Timestamp, "Hs": float, "Dir": float}

    LƯU Ý: bản trước đây chỉ lấy `min(10, len(hs))` bước thời gian đầu tiên
    rồi coi đó là "10 ngày" — trong khi dataset sóng Copernicus lấy mẫu 3
    giờ/lần (xem config.WAVE_DATASET, hậu tố PT3H-i), nên thực chất chỉ đọc
    được ~30 giờ đầu. Bản này đọc toàn bộ và để get_wave_daily() gộp đúng
    theo ngày lịch dựa trên mốc thời gian thật trong file.
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

        var_name = "VHM0" if "VHM0" in ds.variables else (
            "swh" if "swh" in ds.variables else None
        )
        if var_name is None:
            return []

        point = ds.sel({lat_name: lat, lon_name: lon}, method="nearest")

        # Nếu ô gần nhất theo tọa độ toàn NaN (trạm/vùng gần bờ, cửa sông,
        # hoặc ở rìa miền dữ liệu tải về), tìm ô biển hợp lệ gần nhất thay
        # thế thay vì để NaN.
        check = point[var_name]
        if "time" in check.dims:
            check = check.isel(time=0)
        if "depth" in check.dims:
            check = check.isel(depth=0)
        if bool(np.isnan(check.values)):
            nearest_valid = _nearest_valid_latlon(ds, lat, lon, lat_name, lon_name, var_name)
            if nearest_valid is not None:
                valid_lat, valid_lon = nearest_valid
                point = ds.sel({lat_name: valid_lat, lon_name: valid_lon})

        if "depth" in point.dims:
            point = point.isel(depth=0)

        if "time" not in point.coords:
            return []

        hs = point[var_name].values
        direc = point["VMDR"].values if "VMDR" in point else (
            point["mwd"].values if "mwd" in point else None
        )

        if hs is None:
            return []

        hs = np.atleast_1d(hs).astype(float)
        direc = (
            np.atleast_1d(direc).astype(float)
            if direc is not None
            else np.full_like(hs, np.nan)
        )
        times = pd.to_datetime(point["time"].values)

        result = []
        for i in range(len(hs)):
            if math.isnan(hs[i]):
                # Bỏ qua thời điểm lẻ tẻ bị thiếu dữ liệu thay vì gán cứng =
                # 0 (một giá trị 0 lọt vào sẽ làm sai lệch hs_min/hs_max của
                # get_wave_daily).
                continue
            hs_val = round(float(hs[i]), 2)
            dir_val = 0.0 if math.isnan(direc[i]) else float(direc[i])
            result.append({"time": times[i], "Hs": hs_val, "Dir": dir_val})

        return result

    except Exception:
        return []
    finally:
        if ds is not None:
            ds.close()


def get_wave_forecast(ncfile, station):
    """Wrapper tiện dụng: tra tọa độ trạm trong station_config.STATIONS rồi
    gọi get_wave_forecast_at(). Giữ lại cho code cũ còn gọi theo tên trạm."""
    if station not in STATIONS:
        return []
    return get_wave_forecast_at(ncfile, STATIONS[station]["lat"], STATIONS[station]["lon"])


def get_wave_daily_at(ncfile, lat, lon, days=10):
    """
    Gộp chuỗi sóng thật tại tọa độ (lat, lon) theo TỪNG NGÀY lịch, trả về
    đúng `days` phần tử:
        [{"date": date|None, "hs_min": .., "hs_max": .., "dir_deg": ..}, ...]

    Nếu không đọc được dữ liệu thật (thiếu thư viện, file rỗng, tọa độ nằm
    ngoài phạm vi dataset...), trả về giá trị dự phòng an toàn để bản tin
    vẫn sinh ra được thay vì gãy luồng.
    """
    fallback = [
        {"date": None, "hs_min": 0.25, "hs_max": 0.75, "dir_deg": 90.0}
        for _ in range(days)
    ]

    raw = get_wave_forecast_at(ncfile, lat, lon)
    if not raw:
        return fallback

    df = pd.DataFrame(raw)
    df["date"] = df["time"].dt.date

    result = []
    for d, g in df.groupby("date", sort=True):
        idx_max = g["Hs"].idxmax()
        result.append({
            "date": d,
            "hs_min": _floor_to_005(float(g["Hs"].min())),
            "hs_max": _ceil_to_005(float(g["Hs"].max())),
            # hướng sóng đại diện: tại thời điểm sóng cao nhất trong ngày
            "dir_deg": float(g.loc[idx_max, "Dir"]),
        })
        if len(result) >= days:
            break

    if not result:
        return fallback

    # Nếu file .nc tải về ít ngày hơn yêu cầu, lặp lại giá trị ngày cuối
    # cùng để bảng đủ số cột thay vì để trống.
    while len(result) < days:
        result.append(result[-1])

    return result


def get_wave_daily(ncfile, station, days=10):
    """Wrapper tiện dụng: tra tọa độ trạm trong station_config.STATIONS rồi
    gọi get_wave_daily_at(). Giữ lại cho code cũ còn gọi theo tên trạm."""
    if station not in STATIONS:
        return [
            {"date": None, "hs_min": 0.25, "hs_max": 0.75, "dir_deg": 90.0}
            for _ in range(days)
        ]
    return get_wave_daily_at(ncfile, STATIONS[station]["lat"], STATIONS[station]["lon"], days=days)
