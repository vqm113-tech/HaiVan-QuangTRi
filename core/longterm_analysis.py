# ==========================================
# core/longterm_analysis.py
# HẢI VĂN QUẢNG TRỊ 5.0
# ==========================================

import pandas as pd


# ==========================================
# XU THẾ TRIỀU
# ==========================================

def tide_trend(forecast_df):
    # 1. Kiểm tra an toàn DataFrame đầu vào
    if forecast_df is None or not isinstance(forecast_df, pd.DataFrame) or forecast_df.empty:
        return "ít biến đổi"

    n_rows = len(forecast_df)

    # 2. Xác định chỉ số bắt đầu (ngày thứ 4, ưu tiên index 3) và chỉ số kết thúc (ngày cuối)
    idx_begin = 3 if n_rows > 3 else (n_rows - 1 if n_rows > 0 else 0)
    idx_end = -1  # Luôn lấy ngày cuối cùng thực tế có trong bảng

    try:
        hx_begin = float(forecast_df.iloc[idx_begin]["Hx"])
        hx_end = float(forecast_df.iloc[idx_end]["Hx"])

        diff = hx_end - hx_begin

        if diff > 10:
            return "cao dần"
        elif diff < -10:
            return "thấp dần"
        else:
            return "ít biến đổi"

    except (IndexError, KeyError, ValueError, TypeError):
        return "ít biến đổi"


# ==========================================
# NHẬN XÉT SÓNG
# ==========================================

def wave_trend(wave_data):
    # Kiểm tra an toàn danh sách sóng
    if not wave_data or not isinstance(wave_data, (list, tuple)):
        return 0.5, 1.0

    hs = [
        float(x.get("Hs", 0.5))
        for x in wave_data
        if isinstance(x, dict) and "Hs" in x and x["Hs"] is not None
    ]

    # Dự phòng nếu danh sách lọc ra bị rỗng
    if not hs:
        return 0.5, 1.0

    hs_min = round(min(hs), 1)
    hs_max = round(max(hs), 1)

    return hs_min, hs_max


# ==========================================
# NHẬN XÉT DÒNG CHẢY
# ==========================================

def current_trend(current_data):
    # Kiểm tra an toàn danh sách dòng chảy
    if not current_data or not isinstance(current_data, (list, tuple)):
        return 0.5

    speeds = [
        float(x.get("Speed", 0.2))
        for x in current_data
        if isinstance(x, dict) and "Speed" in x and x["Speed"] is not None
    ]

    # Dự phòng nếu danh sách lọc ra bị rỗng
    if not speeds:
        return 0.5

    vmax = max(speeds)

    return round(vmax, 1)


# ==========================================
# SINH ĐOẠN VĂN MỤC 4
# ==========================================

def generate_longterm_comment(
        tide_df,
        wave_data,
        current_data
):
    trend = tide_trend(
        tide_df
    )

    hs_min, hs_max = wave_trend(
        wave_data
    )

    vmax = current_trend(
        current_data
    )

    text = (
        f"Từ ngày thứ 4 đến ngày thứ 10, "
        f"mực nước triều có xu thế {trend}. "
        f"Độ cao sóng phổ biến "
        f"{hs_min}-{hs_max}m. "
        f"Dòng chảy mạnh nhất khoảng "
        f"{vmax}m/s. "
        f"Biển ít biến động."
    )

    return text