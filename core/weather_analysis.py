# ==========================================
# core/weather_analysis.py
# HẢI VĂN QUẢNG TRỊ 5.0
# ==========================================

import random


# ==========================================
# PHÂN CẤP GIÓ
# ==========================================

def wind_level_text(speed):

    if speed < 5:
        return "cấp 2-3"

    elif speed < 8:
        return "cấp 3-4"

    elif speed < 11:
        return "cấp 4-5"

    elif speed < 14:
        return "cấp 5-6"

    else:
        return "cấp 6-7"


# ==========================================
# TRẠNG THÁI BIỂN
# ==========================================

def sea_state_text(hs):

    if hs < 0.5:

        return "Biển bình thường"

    elif hs < 1.5:

        return "Biển động nhẹ"

    elif hs < 2.5:

        return "Biển động"

    elif hs < 4:

        return "Biển động mạnh"

    else:

        return "Biển rất động"


# ==========================================
# SINH THỜI TIẾT
# ==========================================

def weather_text():

    options = [

        "Có mưa rào và dông vài nơi",

        "Mây thay đổi, đêm không mưa, ngày nắng",

        "Có mưa rào rải rác và có nơi có dông",

        "Ngày nắng, chiều tối và đêm có mưa rào và dông vài nơi"

    ]

    return random.choice(options)


# ==========================================
# TẦM NHÌN XA
# ==========================================

def visibility_text():

    return "Trên 10 km"


# ==========================================
# SINH DỰ BÁO THỜI TIẾT BIỂN 3 NGÀY
# ==========================================

def generate_weather_3days(
        wave_data,
        atmos_data=None,
):
    """
    atmos_data: dữ liệu khí tượng khí quyển THẬT (mưa, gió, tầm nhìn) lấy từ
    core/weather_forecast.py::get_weather_daily() — list[dict] tối thiểu 3
    phần tử, mỗi phần tử có "Thời_tiết", "Tầm_nhìn", "wind_speed_ms",
    "wind_dir_text". Nếu None (chưa tải được dữ liệu khí tượng thật), quay
    lại hành vi CŨ: "Thời tiết" chọn ngẫu nhiên, "Tầm nhìn" cố định "Trên 10
    km", hướng gió cố định "Tây Bắc" — xem README mục "Giới hạn thật của
    bảng 1" để biết vì sao đây vẫn là phương án dự phòng hợp lý khi không
    có dữ liệu khí tượng thật.
    """

    weather_data = []

    for day in range(3):

        hs = wave_data[day]["Hs"]

        if atmos_data and len(atmos_data) > day:
            day_atmos = atmos_data[day]
            weather_data.append(
                {
                    "Thời_tiết": day_atmos["Thời_tiết"],
                    "Tầm_nhìn": day_atmos["Tầm_nhìn"],
                    "Gió":
                        day_atmos["wind_dir_text"] + " " +
                        wind_level_text(day_atmos["wind_speed_ms"]),
                    "Trạng_thái_biển":
                        sea_state_text(hs),
                }
            )
            continue

        weather_data.append(

            {

                "Thời_tiết":

                    weather_text(),

                "Tầm_nhìn":

                    visibility_text(),

                "Gió":

                    "Tây Bắc " +

                    wind_level_text(

                        hs * 6

                    ),

                "Trạng_thái_biển":

                    sea_state_text(

                        hs

                    )

            }

        )

    return weather_data