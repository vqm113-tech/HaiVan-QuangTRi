# ==========================================
# THÔNG TIN CÁC TRẠM HẢI VĂN
# ==========================================

STATIONS = {

    "tan_my": {

        "name": "Tân Mỹ",

        "lat": 17.84,

        "lon": 106.90,

        "region": "ven_bo_bac"

    },


    "dong_hoi": {

        "name": "Đồng Hới",

        "lat": 17.48,

        "lon": 106.62,

        "region": "ngoai_khoi_bac"

    },


    "cua_viet": {

        "name": "Cửa Việt",

        "lat": 16.87,

        "lon": 107.12,

        "region": "ven_bo_nam"

    },


    "con_co": {

        "name": "Cồn Cỏ",

        "lat": 17.17,

        "lon": 107.34,

        "region": "ngoai_khoi_nam"

    }

}


# ==========================================
# TỌA ĐỘ CHÍNH THỨC 5 VÙNG DỰ BÁO (khác với tọa độ trạm triều ở trên)
#
# STATIONS ở trên là các trạm đo triều thực tế (ven bờ/đảo) — dùng để tính
# thủy triều. FORECAST_REGIONS dưới đây là tâm điểm CHÍNH THỨC của 5 vùng
# biển dự báo trong bản tin (do người dùng cung cấp, đơn vị độ thập phân),
# dùng để truy vấn dữ liệu sóng/dòng chảy (Copernicus) đúng vị trí, và hiển
# thị trên bản đồ giao diện — không dùng trạm triều làm proxy nữa vì lệch
# vị trí khá xa (ví dụ "ngoài khơi phía Nam" cách xa Cồn Cỏ hơn 150km).
# ==========================================

FORECAST_REGIONS = {

    "offshore_north": {
        "name": "Vùng biển ngoài khơi phía Bắc",
        "lat": 17.85291666666667,
        "lon": 108.0120833333333,
    },

    "offshore_south": {
        "name": "Vùng biển ngoài khơi phía Nam",
        "lat": 16.73091666666667,
        "lon": 109.0135555555556,
    },

    "coastal_north": {
        "name": "Vùng biển ven bờ phía Bắc",
        "lat": 17.84805555555555,
        "lon": 106.6483611111111,
    },

    "coastal_south": {
        "name": "Vùng biển ven bờ phía Nam",
        "lat": 16.74891666666667,
        "lon": 107.5275,
    },

    # Cồn Cỏ: dùng luôn tọa độ trạm thật (không có tọa độ riêng do người
    # dùng cung cấp, và trạm Cồn Cỏ vốn đã nằm ngoài khơi).
    "con_co": {
        "name": "Cồn Cỏ",
        "lat": STATIONS["con_co"]["lat"],
        "lon": STATIONS["con_co"]["lon"],
    },

}

LATS = {

    station: STATIONS[station]["lat"]

    for station in STATIONS

}


LONS = {

    station: STATIONS[station]["lon"]

    for station in STATIONS

}


# ==========================================
# TÊN HIỂN THỊ TRONG BẢN TIN
# ==========================================

DISPLAY_NAMES = {

    "ngoai_khoi_bac":
        "Vùng biển ngoài khơi phía Bắc",

    "ngoai_khoi_nam":
        "Vùng biển ngoài khơi phía Nam",

    "ven_bo_bac":
        "Vùng biển ven bờ phía Bắc",

    "ven_bo_nam":
        "Vùng biển ven bờ phía Nam",

    "con_co":
        "Cồn Cỏ"

}


# ==========================================
# DANH SÁCH 4 TRẠM
# ==========================================

STATION_LIST = [

    "tan_my",

    "dong_hoi",

    "cua_viet",

    "con_co"

]