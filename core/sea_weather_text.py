# ==========================================
# core/sea_weather_text.py
# HẢI VĂN QUẢNG TRỊ 5.0
# ==========================================

import pandas as pd


# ==========================================
# MỤC 2 - THỜI TIẾT BIỂN 3 NGÀY
# ==========================================

def generate_weather_summary(weather_3days):

    if not weather_3days or not isinstance(weather_3days, (list, tuple)):
        return (
            "Vùng biển tỉnh Quảng Trị có mưa rào và dông vài nơi, "
            "trong cơn dông có khả năng xuất hiện lốc xoáy và gió giật mạnh; "
            "tầm nhìn xa trên 10 km; gió nhẹ; biển bình thường."
        )

    weather_set = set()
    sea_set = set()
    wind_set = set()

    for x in weather_3days:
        if isinstance(x, dict):
            if x.get("Thời_tiết"):
                weather_set.add(str(x["Thời_tiết"]))
            if x.get("Trạng_thái_biển"):
                sea_set.add(str(x["Trạng_thái_biển"]))
            if x.get("Gió"):
                wind_set.add(str(x["Gió"]))

    weather_text = "; ".join(weather_set) if weather_set else "có mưa rào và dông vài nơi"
    sea_text = ", ".join(sea_set) if sea_set else "biển bình thường"
    wind_text = ", ".join(wind_set) if wind_set else "gió nhẹ"

    text = (
        f"Vùng biển tỉnh Quảng Trị có "
        f"{weather_text.lower()}, "
        f"trong cơn dông có khả năng xuất hiện lốc xoáy "
        f"và gió giật mạnh; "
        f"tầm nhìn xa trên 10 km; "
        f"{wind_text.lower()}; "
        f"{sea_text.lower()}."
    )

    return text


# ==========================================
# MỤC 3 - NHẬN XÉT HẢI VĂN 3 NGÀY
# ==========================================

def generate_marine_comment(
        tide_df,
        wave_data,
        current_data
):
    # 1. BẢO VỆ CHỐNG LỖI DANH SÁCH SÓNG RỖNG
    if wave_data and isinstance(wave_data, (list, tuple)):
        hs_list = [
            float(x["Hs"])
            for x in wave_data
            if isinstance(x, dict) and "Hs" in x and x["Hs"] is not None
        ]
    else:
        hs_list = []

    if hs_list:
        hmax = max(hs_list)
        hmin = min(hs_list)
    else:
        hmin, hmax = 0.5, 1.0

    # 2. BẢO VỆ CHỐNG LỖI DANH SÁCH DỒNG CHẢY RỖNG
    if current_data and isinstance(current_data, (list, tuple)):
        speed_list = [
            float(x["Speed"])
            for x in current_data
            if isinstance(x, dict) and "Speed" in x and x["Speed"] is not None
        ]
    else:
        speed_list = []

    if speed_list:
        vmax = max(speed_list)
    else:
        vmax = 0.5

    # 3. BẢO VỆ CHỐNG LỖI OUT-OF-BOUNDS KHI TRUY CẬP TIDE_DF (tide_df.iloc[2])
    if isinstance(tide_df, pd.DataFrame) and not tide_df.empty:
        n_rows = len(tide_df)
        
        # Chỉ số ngày 1 (đầu) và ngày 3 (hoặc dòng cuối hiện có)
        idx1 = 0
        idx3 = 2 if n_rows > 2 else (n_rows - 1)

        try:
            hx1 = float(tide_df.iloc[idx1]["Hx"])
            hx3 = float(tide_df.iloc[idx3]["Hx"])

            if hx3 > hx1:
                trend = "cao dần"
            elif hx3 < hx1:
                trend = "thấp dần"
            else:
                trend = "ít biến đổi"
        except (IndexError, KeyError, ValueError, TypeError):
            trend = "ít biến đổi"
    else:
        trend = "ít biến đổi"

    text = (
        f"Trong 3 ngày tới, "
        f"độ cao sóng phổ biến "
        f"từ {hmin:.1f}-{hmax:.1f}m; "
        f"dòng chảy mạnh nhất khoảng "
        f"{vmax:.1f}m/s. "
        f"Đỉnh triều và chân triều "
        f"có xu thế {trend}."
    )

    return text


# ==========================================
# MỤC 5 - KHẢ NĂNG TÁC ĐỘNG
# ==========================================

def analyze_impact(
        wave_data,
        current_data
):
    # Bảo vệ chống lỗi danh sách rỗng
    if wave_data and isinstance(wave_data, (list, tuple)):
        hs_list = [
            float(x["Hs"])
            for x in wave_data
            if isinstance(x, dict) and "Hs" in x and x["Hs"] is not None
        ]
    else:
        hs_list = []

    hmax = max(hs_list) if hs_list else 1.0

    if hmax < 1.5:
        return (
            "Điều kiện hải văn thuận lợi cho các hoạt động hàng hải, khai thác và nuôi trồng thủy sản."
        )
    elif hmax < 2.5:
        return (
            "Biển động nhẹ, cần chú ý đối với tàu thuyền công suất nhỏ hoạt động trên biển."
        )
    elif hmax < 4:
        return (
            "Biển động, có thể ảnh hưởng đến hoạt động của tàu thuyền và các hoạt động khai thác trên biển."
        )
    else:
        return (
            "Biển động mạnh, có khả năng gây nguy hiểm cho hoạt động hàng hải và đánh bắt hải sản."
        )