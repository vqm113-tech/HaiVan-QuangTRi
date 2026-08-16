# ==========================================
# bulletin/area_data.py
# DỰ BÁO THỦY TRIỀU 10 NGÀY QUY ĐỔI SANG HẢI ĐỒ (+110cm)
#
# So với bản gốc:
#   - Thủy triều: dùng bộ mô hình điều hòa chuẩn trong models/ (qua
#     bulletin/tide_model.py) thay cho fit 6 hằng số thô sơ, có QC dữ liệu
#     đầu vào (core/qc.py) trước khi fit.
#   - Sóng/dòng chảy: đọc dữ liệu thật từ file .nc (qua bulletin/marine_data.py)
#     thay cho số liệu cố định. Nếu chưa có/không đọc được dữ liệu .nc thật,
#     marine_data.py tự trả về giá trị dự phòng an toàn.
# ==========================================

import logging

import pandas as pd
from datetime import datetime, timedelta

from core.qc import MarineQualityControl
from bulletin.tide_model import predict_tide
from bulletin.marine_data import build_wave_current_tables, get_province_wide_daily, REGION_TO_STATION

from core.weather_analysis import generate_weather_3days
from core.weather_forecast import get_weather_daily
from core.sea_weather_text import (
    generate_weather_summary,
    generate_marine_comment,
    analyze_impact,
)
from core.warning_analysis import analyze_danger
from core.longterm_analysis import generate_longterm_comment

logger = logging.getLogger(__name__)

# Hằng số quy đổi từ Mực nước Quốc gia (m) sang Hải đồ Quốc tế (cm)
OFFSET_CHART_DATUM_CM = 110.0


# Từ khóa nhận diện cột trạm trong file Excel, khớp với 4 trạm thật trong
# station_config.STATIONS — dùng để tính triều RIÊNG cho từng trạm thay vì
# dùng chung 1 trạm cho cả 5 vùng biển của bản tin (bug đã sửa: trước đây
# bảng 2/3 mọi vùng biển đều ra CÙNG một giá trị triều).
STATION_COLUMN_KEYWORDS = {
    'tan_my': ['tân mỹ', 'tan my'],
    'dong_hoi': ['đồng hới', 'dong hoi'],
    'cua_viet': ['cửa việt', 'cua viet'],
    'con_co': ['cồn cỏ', 'con co'],
}


def _pick_value_column(df, station_key=None):
    """Chọn đúng cột mực nước của trạm `station_key` trong Excel. Nếu không
    tìm thấy cột khớp tên trạm (ví dụ người dùng chỉ tải lên 1-2 cột), dùng
    cột dữ liệu thứ 2 làm phương án dự phòng."""
    keywords = STATION_COLUMN_KEYWORDS.get(station_key, [])
    for c in df.columns:
        cl = str(c).lower()
        if any(kw in cl for kw in keywords):
            return c
    return df.columns[1]


def forecast_tide_from_observed(
    df_obs,
    station_key=None,
    forecast_days=10,
    amplitude_scale=None,
    manual_offset_m=0.0,
    chart_datum_offset_cm=None,
):
    """
    1. Đọc mực nước thực đo (đơn vị mét) từ file Excel, đúng cột trạm
       `station_key` (xem STATION_COLUMN_KEYWORDS).
    2. QC dữ liệu (loại giá trị ngoài khoảng vật lý, bước nhảy bất thường,
       ngoại lai theo bộ lọc Hampel, nội suy khoảng trống ngắn) — core/qc.py.
    3. Chạy mô hình điều hòa triều chuẩn (bulletin/tide_model.py) để dự báo
       `forecast_days` ngày tiếp theo — CÓ áp dụng hiệu chỉnh của dự báo viên
       (amplitude_scale, manual_offset_m) nếu có, xem tide_model.predict_tide().
    4. Quy đổi sang chuẩn Hải đồ: H_hải_đồ (cm) = (H_thực_đo_m * 100) +
       chart_datum_offset_cm (mặc định OFFSET_CHART_DATUM_CM nếu không truyền
       riêng cho trạm — các trạm khác nhau có thể có mốc "0 hải đồ" khác
       nhau, đặc biệt trạm cửa sông như Cửa Việt).
    5. Trích xuất đỉnh triều (Hx) / chân triều (Hm) mỗi ngày.

    Raise Exception nếu không đủ số liệu hợp lệ để fit mô hình — bên gọi
    (build_area_data) có phương án dự phòng riêng.
    """
    if chart_datum_offset_cm is None:
        chart_datum_offset_cm = OFFSET_CHART_DATUM_CM

    # ---- 1. Xác định cột thời gian / cột mực nước ----
    df_clean = df_obs.copy()
    time_col = df_clean.columns[0]
    val_col = _pick_value_column(df_clean, station_key)

    df_clean['dt'] = pd.to_datetime(df_clean[time_col], errors='coerce')
    df_clean['val'] = pd.to_numeric(df_clean[val_col], errors='coerce')
    df_clean = df_clean.dropna(subset=['dt']).sort_values('dt').reset_index(drop=True)

    # ---- 2. QC dữ liệu quan trắc trước khi fit mô hình ----
    qc = MarineQualityControl()
    df_qc, qc_report = qc.run_pipeline(
        df_clean[['dt', 'val']],
        value_col='val',
        variable='water_level',
    )
    df_qc = df_qc.dropna(subset=['dt', 'val'])
    logger.info(
        "QC mực nước: %d bản ghi, chất lượng %s (điểm %.1f)",
        qc_report.total_records, qc_report.quality, qc_report.quality_score,
    )

    # ---- 3. Chạy mô hình điều hòa triều chuẩn ----
    last_dt = df_qc['dt'].max()
    start_forecast_dt = (last_dt + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    pred_df = predict_tide(
        df_qc['dt'], df_qc['val'], start_forecast_dt, forecast_days=forecast_days,
        amplitude_scale=amplitude_scale, manual_offset_m=manual_offset_m,
    )
    if pred_df is None:
        raise ValueError(
            "Không đủ số liệu hợp lệ sau QC để fit mô hình điều hòa triều "
            "(cần tối thiểu ~2 ngày số liệu quan trắc liên tục)."
        )

    # ---- 4. Quy đổi sang chuẩn Hải đồ (cm) ----
    pred_df = pred_df.copy()
    pred_df['val_chart'] = (pred_df['WaterLevel'] * 100.0) + chart_datum_offset_cm

    # ---- 5. Trích xuất Đỉnh (Hx) và Chân (Hm) theo từng ngày ----
    tide_result = {
        'tide_hx': [],
        'tide_hx_time': [],
        'tide_hm': [],
        'tide_hm_time': [],
    }
    dates_str = []

    for d in pred_df['Datetime'].dt.date.unique()[:forecast_days]:
        dates_str.append(d.strftime('%d/%m/%Y'))
        df_day = pred_df[pred_df['Datetime'].dt.date == d]

        max_row = df_day.loc[df_day['val_chart'].idxmax()]
        min_row = df_day.loc[df_day['val_chart'].idxmin()]

        tide_result['tide_hx'].append(f"{int(round(max_row['val_chart']))}")
        tide_result['tide_hx_time'].append(max_row['Datetime'].strftime('%Hh%M'))
        tide_result['tide_hm'].append(f"{int(round(min_row['val_chart']))}")
        tide_result['tide_hm_time'].append(min_row['Datetime'].strftime('%Hh%M'))

    return dates_str, tide_result


def generate_narrative_texts(tide_dict, forecast_days=10, wave_scale=1.0, current_scale=1.0):
    """
    Sinh bảng 1 (thời tiết biển tường thuật) + văn bản mục 1-6 từ dữ liệu
    triều/sóng/dòng chảy thật, dùng các hàm trong core/weather_analysis.py,
    core/sea_weather_text.py, core/warning_analysis.py, core/longterm_analysis.py.

    CHỦ Ý: không dùng core.ai_forecaster.generate_ai_forecast() vì hàm đó
    truyền CHUNG một bộ (tide_data, wave_data, current_data) cho cả văn bản
    "3 ngày tới" lẫn "ngày 4-10", trong khi generate_longterm_comment() cần
    dữ liệu đủ 10 ngày (dùng chỉ số ngày 4 và ngày 10) còn generate_marine_
    comment()/analyze_danger()/analyze_impact() chỉ nên dùng riêng 3 ngày đầu
    — dùng chung sẽ làm sai lệch phạm vi thời gian của từng đoạn văn. Ở đây
    gọi trực tiếp từng hàm con với đúng phạm vi dữ liệu cần thiết.

    wave_scale, current_scale : hệ số hiệu chỉnh sóng/dòng chảy do dự báo
        viên tự nhập (xem build_area_data()) — áp dụng để văn bản tường
        thuật khớp với số liệu đã hiệu chỉnh trong bảng 2/3.

    Trả về (weather_3days, sec_texts).
    """
    wave_prov, current_prov = get_province_wide_daily(
        forecast_days=forecast_days, wave_scale=wave_scale, current_scale=current_scale
    )

    tide_df_full = pd.DataFrame({'Hx': [int(x) for x in tide_dict['tide_hx']]})
    tide_df_3 = tide_df_full.iloc[:3].reset_index(drop=True)

    weather_3days = generate_weather_3days(wave_prov[:3], atmos_data=get_weather_daily(days=3))
    weather_text = generate_weather_summary(weather_3days)
    marine_text = generate_marine_comment(tide_df_3, wave_prov[:3], current_prov[:3])
    danger_text = analyze_danger(wave_prov[:3], current_prov[:3], weather_3days)
    impact_text = analyze_impact(wave_prov[:3], current_prov[:3])
    longterm_text = generate_longterm_comment(tide_df_full, wave_prov[3:10], current_prov[3:10])

    sec_texts = {
        'weather_text': weather_text,
        'marine_text': marine_text,
        'danger_text': danger_text,
        'impact_text': impact_text,
        'longterm_text': longterm_text,
        'wave_today': wave_prov[0],
    }

    return weather_3days, sec_texts


def _cm_to_m_str(cm_value):
    """Quy đổi chuỗi cm (ví dụ '136') sang mét, 2 số thập phân (ví dụ '1.36')
    — dùng riêng cho hiển thị Bảng 2/3, không đổi giá trị cm dùng nội bộ cho
    văn bản tường thuật/tính xu thế (vẫn giữ nguyên đơn vị cm ở đó)."""
    try:
        return f"{float(cm_value) / 100.0:.2f}"
    except (TypeError, ValueError):
        return cm_value


def _tide_list_to_m(cm_list):
    return [_cm_to_m_str(v) for v in cm_list]


def build_area_data(df, tide_corrections=None, wave_scale=1.0, current_scale=1.0):
    """
    Hàm chính tiếp nhận DataFrame từ app.py để đóng gói dữ liệu sinh bản tin Word.

    tide_corrections : dict tùy chọn {station_key: {"amplitude_scale": {...},
        "manual_offset_m": float, "chart_datum_offset_cm": float}} — hiệu
        chỉnh dự báo triều RIÊNG cho từng trạm do dự báo viên tự nhập trên
        giao diện (app.py), để bù cho đặc điểm địa phương mà mô hình thuần
        túy không nắm hết được — ví dụ Cửa Việt là trạm đo tại CỬA SÔNG, số
        liệu chịu ảnh hưởng dòng chảy nước ngọt/hình thái lòng sông chứ
        không thuần túy là triều biển hở, nên có thể cần hiệu chỉnh khác so
        với Cồn Cỏ (trạm đảo, đại diện triều biển hở tốt hơn).
    wave_scale, current_scale : hệ số nhân hiệu chỉnh sóng/dòng chảy do dự
        báo viên tự nhập — áp dụng CHO TẤT CẢ các ngày và vùng biển (ví dụ
        dự báo gốc H = 0.5 - 1.5m, wave_scale = 1.2 -> hiển thị H = 0.6 -
        1.8m). Mặc định 1.0 = không đổi.
    """
    tide_corrections = tide_corrections or {}
    fallback_dates = None
    fallback_tide = {
        'tide_hx': ['145', '148', '152', '150', '145', '140', '138', '142', '146', '150'],
        'tide_hx_time': ['11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00'],
        'tide_hm': ['75', '78', '80', '82', '85', '82', '78', '75', '72', '76'],
        'tide_hm_time': ['03:30', '04:00', '04:30', '05:00', '05:30', '06:00', '06:30', '07:00', '07:30', '08:00']
    }

    def _fallback_dates():
        base_date = datetime.now()
        return [(base_date + timedelta(days=i)).strftime('%d/%m/%Y') for i in range(10)]

    # ---- Tính triều RIÊNG cho từng trạm thật (không dùng chung 1 trạm cho
    # cả 5 vùng biển như bản trước — đó là nguyên nhân bảng 2/3 mọi vùng ra
    # cùng 1 giá trị triều). Chỉ cần tính 1 lần/trạm (4 trạm), rồi ánh xạ ra
    # 5 vùng qua REGION_TO_STATION (offshore_south và con_co cùng dùng trạm
    # Cồn Cỏ nên chỉ tính 1 lần, không lặp lại).
    station_keys = sorted(set(REGION_TO_STATION.values()))
    per_station_tide = {}
    for station_key in station_keys:
        corr = tide_corrections.get(station_key, {})
        try:
            dates, tide_dict = forecast_tide_from_observed(
                df, station_key=station_key, forecast_days=10,
                amplitude_scale=corr.get('amplitude_scale'),
                manual_offset_m=corr.get('manual_offset_m', 0.0),
                chart_datum_offset_cm=corr.get('chart_datum_offset_cm'),
            )
            per_station_tide[station_key] = (dates, tide_dict)
        except Exception as exc:
            logger.warning(
                "forecast_tide_from_observed thất bại cho trạm %s, dùng dữ liệu dự phòng: %s",
                station_key, exc,
            )
            per_station_tide[station_key] = (fallback_dates or _fallback_dates(), fallback_tide)

    # Trạm "chính" dùng cho các phần KHÔNG tách theo vùng biển (days_3/days_7,
    # số hiệu bản tin, văn bản tường thuật mục 1-6...) — ưu tiên Cửa Việt vì
    # đây là trạm ven bờ trung tâm, gần khu dân cư/tàu thuyền hoạt động chính.
    primary_station = 'cua_viet' if 'cua_viet' in per_station_tide else station_keys[0]
    dates_10, tide_dict = per_station_tide[primary_station]

    days_3 = dates_10[:3]
    days_7 = dates_10[3:10]

    regions = ['offshore_north', 'offshore_south', 'coastal_north', 'coastal_south', 'con_co']

    # Sóng/dòng chảy THẬT từ file .nc (marine_data.py tự trả về dự phòng an
    # toàn nếu chưa đọc được dữ liệu thật — xem README mục "Trạng thái thật").
    # Có áp dụng hiệu chỉnh wave_scale/current_scale nếu dự báo viên nhập.
    marine_tables = build_wave_current_tables(forecast_days=10, wave_scale=wave_scale, current_scale=current_scale)

    # Bảng 1 (thời tiết biển tường thuật) + văn bản mục 1-6: sinh từ dữ liệu
    # sóng/dòng chảy/triều thật qua core/weather_analysis.py, sea_weather_text.py,
    # warning_analysis.py, longterm_analysis.py (xem generate_narrative_texts()).
    # LƯU Ý: hệ thống này KHÔNG có nguồn dữ liệu khí tượng khí quyển thật (mưa,
    # hướng gió) — chỉ có dữ liệu sóng/dòng chảy hải dương. Nên trong bảng 1,
    # cột "Thời tiết"/"Tầm nhìn" và hướng gió trong cột "Gió" vẫn là suy diễn/
    # giả định (gió chỉ suy ra tốc độ từ độ cao sóng, hướng gió mặc định "Tây
    # Bắc"), KHÔNG phải số liệu khí tượng thật — xem README.
    try:
        weather_3days, sec_texts = generate_narrative_texts(
            tide_dict, forecast_days=10, wave_scale=wave_scale, current_scale=current_scale
        )
    except Exception as exc:
        logger.warning("generate_narrative_texts thất bại, dùng văn bản dự phòng: %s", exc)
        weather_3days = None
        sec_texts = None

    if weather_3days and len(weather_3days) >= 3:
        table1_data = {reg: {
            'weather': [d['Thời_tiết'] for d in weather_3days],
            'visibility': [d['Tầm_nhìn'] for d in weather_3days],
            'wind': [d['Gió'] for d in weather_3days],
            'sea_state': [d['Trạng_thái_biển'] for d in weather_3days],
        } for reg in regions}
    else:
        table1_data = {reg: {
            'weather': ['Mưa rào rải rác', 'Có mưa rào vài nơi', 'Không mưa, ngày nắng'],
            'visibility': ['4 - 10 km', 'Trên 10 km', 'Trên 10 km'],
            'wind': ['Tây Bắc cấp 3-4', 'Đông Nam cấp 3', 'Đông cấp 3-4'],
            'sea_state': ['Bình thường', 'Bình thường', 'Bình thường']
        } for reg in regions}

    table2_data = {reg: {
        'tide_hx': _tide_list_to_m(per_station_tide[REGION_TO_STATION[reg]][1]['tide_hx'][:3]),
        'tide_hx_time': per_station_tide[REGION_TO_STATION[reg]][1]['tide_hx_time'][:3],
        'tide_hm': _tide_list_to_m(per_station_tide[REGION_TO_STATION[reg]][1]['tide_hm'][:3]),
        'tide_hm_time': per_station_tide[REGION_TO_STATION[reg]][1]['tide_hm_time'][:3],
        'wave_height': marine_tables[reg]['wave_height'][:3],
        'wave_dir': marine_tables[reg]['wave_dir'][:3],
        'current_speed': marine_tables[reg]['current_speed'][:3],
        'current_dir': marine_tables[reg]['current_dir'][:3],
    } for reg in regions}

    table3_data = {reg: {
        'tide_hx': _tide_list_to_m(per_station_tide[REGION_TO_STATION[reg]][1]['tide_hx'][3:10]),
        'tide_hx_time': per_station_tide[REGION_TO_STATION[reg]][1]['tide_hx_time'][3:10],
        'tide_hm': _tide_list_to_m(per_station_tide[REGION_TO_STATION[reg]][1]['tide_hm'][3:10]),
        'tide_hm_time': per_station_tide[REGION_TO_STATION[reg]][1]['tide_hm_time'][3:10],
        'wave_height': marine_tables[reg]['wave_height'][3:10],
        'wave_dir': marine_tables[reg]['wave_dir'][3:10],
    } for reg in regions}

    hx_1, hx_3 = tide_dict['tide_hx'][0], tide_dict['tide_hx'][2]
    hx_t1 = tide_dict['tide_hx_time'][0]
    hm_1, hm_t1 = tide_dict['tide_hm'][0], tide_dict['tide_hm_time'][0]

    all_hx_7 = [int(x) for x in tide_dict['tide_hx'][3:10] if str(x).isdigit()]
    max_hx_7 = max(all_hx_7) if all_hx_7 else 150

    # Giá trị mét dùng riêng cho văn bản tường thuật mục 1-6, khớp đơn vị
    # với Bảng 2/3 (m) — tide_dict/hx_1/hx_3/hm_1/max_hx_7 ở trên vẫn giữ cm
    # cho các mục đích tính toán khác (không đổi).
    hx_1_m = _cm_to_m_str(hx_1)
    hx_3_m = _cm_to_m_str(hx_3)
    hm_1_m = _cm_to_m_str(hm_1)
    max_hx_7_m = _cm_to_m_str(max_hx_7)

    if sec_texts is not None:
        wave_today = sec_texts['wave_today']
        sec1_text = (
            f"Trong 24 giờ qua, vùng biển Quảng Trị sóng cao phổ biến từ "
            f"{wave_today['Hs_min']:.2f} – {wave_today['Hs']:.2f}m."
        )
        sec2_text = sec_texts['weather_text']
        sec3_text = sec_texts['marine_text']
        sec4_text = sec_texts['longterm_text']
        sec5_text = sec_texts['danger_text']
        sec6_text = sec_texts['impact_text']
    else:
        sec1_text = "Trong 24 giờ qua, vùng biển Quảng Trị có gió nhẹ, sóng cao phổ biến từ 0.25 – 0.75m."
        sec2_text = "Dự báo 3 ngày tới: Vùng biển Quảng Trị có mưa rào và dông vài nơi, trong mưa dông đề phòng lốc xoáy và gió giật mạnh. Gió hướng Đông Bắc đến Đông Nam cấp 3-4."
        sec3_text = f"Trong 3 ngày tới, sóng biển cao phổ biến từ 0.25 – 1.25m. Độ cao đỉnh triều có xu thế thay đổi từ {hx_1_m}m đến {hx_3_m}m."
        sec4_text = f"Từ ngày {days_7[0]} đến ngày {days_7[-1]}: Mực nước triều dao động với đỉnh triều cực đại đạt khoảng {max_hx_7_m}m. Sóng biển phổ biến từ 0.5 - 1.5m, biển bình thường."
        sec5_text = "Đề phòng khả năng xuất hiện lốc xoáy và gió giật mạnh trong các đợt mưa dông rải rác."
        sec6_text = "Tất cả tàu thuyền, hoạt động nuôi trồng thủy hải sản và công trình ven biển cần chú ý theo dõi các bản tin cảnh báo gió giật trong mưa dông."

    area_data = {
        'bulletin_num': 'HVHN-114/QTRI',
        'issue_date': datetime.now().strftime('ngày %d tháng %m năm %Y'),
        'period_text': f"Từ ngày {dates_10[0]} đến ngày {dates_10[-1]}",
        'days_3': days_3,
        'days_7': days_7,
        'table1_data': table1_data,
        'table2_data': table2_data,
        'table3_data': table3_data,
        'sec1_text': sec1_text,
        'sec2_text': sec2_text,
        'sec3_text': sec3_text,
        'sec4_text': sec4_text,
        'sec5_text': sec5_text,
        'sec6_text': sec6_text,
        'next_issue_time': f"16h00 ngày {(datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')}"
    }

    return area_data
