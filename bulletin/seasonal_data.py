# ==========================================
# bulletin/seasonal_data.py
# Tính dữ liệu cho "BẢN TIN DỰ BÁO, CẢNH BÁO HẢI VĂN THỜI HẠN MÙA" (HVHM)
# — khớp mẫu thật QTRI_HVHM_20260615_1700.docx.
#
# Cấu trúc mẫu:
#   1. Phân tích 02 tháng qua (Bảng 1: đặc trưng sóng/triều THỰC ĐO tại 1
#      trạm đại diện — Cồn Cỏ trong mẫu).
#   2. Dự báo hải văn 3 tháng tới (Bảng 2: thủy triều Nước lớn/Nước ròng
#      từng tháng, cả 5 vùng biển).
#   3. Xu thế hải văn 3 tháng sau nữa (chỉ văn bản, KHÔNG có bảng — đúng
#      như mẫu thật).
#
# Dữ liệu THẬT dùng được trong dự án:
#   - Bảng 1 (Hmax/Hmin thủy triều 2 tháng qua): tính TRỰC TIẾP từ số liệu
#     Excel thực đo do người dùng tải lên (không qua mô hình) — đây là số
#     liệu quan trắc thật, chính xác nhất có thể.
#   - Bảng 2 (thủy triều 3 tháng tới): dùng ĐÚNG mô hình điều hòa triều
#     chuẩn (bulletin/tide_model.py) ngoại suy ~90 ngày — hợp lệ vì đây là
#     mô hình thiên văn, không suy giảm độ tin cậy theo thời gian như dự
#     báo khí tượng/sóng.
#   - Sóng biển (cả 2 phần): dự án KHÔNG có nguồn khí hậu sóng dài hạn nào
#     (chỉ có ~10 ngày dự báo Copernicus) — để mặc định placeholder, dự báo
#     viên sửa tay theo hiểu biết nghiệp vụ/số liệu khí hậu tham khảo riêng.
#   - Văn bản xu thế XTNĐ, cảnh báo, tác động: hoàn toàn thuộc nhận định
#     synop/khí hậu của dự báo viên — không có mô hình nào trong dự án tạo
#     ra được, để placeholder biên tập trên giao diện trước khi xuất.
# ==========================================

from __future__ import annotations

import calendar
import logging
from datetime import datetime

import pandas as pd

from bulletin.area_data import forecast_tide_from_observed, STATION_COLUMN_KEYWORDS, _pick_value_column
from bulletin.marine_data import REGION_TO_STATION
from core.qc import MarineQualityControl

logger = logging.getLogger(__name__)

REGIONS = ['offshore_north', 'offshore_south', 'coastal_north', 'coastal_south', 'con_co']

REGION_DISPLAY = {
    'offshore_north': 'Vùng biển ngoài khơi phía Bắc',
    'offshore_south': 'Vùng biển ngoài khơi phía Nam',
    'coastal_north': 'Vùng biển ven bờ phía Bắc',
    'coastal_south': 'Vùng biển ven bờ phía Nam',
    'con_co': 'Cồn Cỏ',
}

OFFSET_CHART_DATUM_CM = 110.0
DEFAULT_WAVE_RANGE = "0.5 - 1.5"


def _add_months(year, month, n):
    total = (month - 1) + n
    return year + total // 12, total % 12 + 1


def _month_extrema_observed(df, station_key, year, month, chart_datum_offset_cm=None, end_day=None):
    """Hx/Hm THỰC ĐO trong 1 tháng lịch, lấy trực tiếp từ Excel người dùng
    tải lên (không qua mô hình) — dùng cho Bảng 1 (hồi cứu). `end_day`, nếu
    có, giới hạn chỉ lấy từ ngày 01 đến hết ngày đó trong tháng (dùng cho kỳ
    thứ 3 "Từ 01-DD/tháng phát tin" — đúng mẫu thật, KHÔNG tính hết cả
    tháng phát tin vì bản tin phát ra giữa tháng)."""
    if chart_datum_offset_cm is None:
        chart_datum_offset_cm = OFFSET_CHART_DATUM_CM
    try:
        time_col = df.columns[0]
        val_col = _pick_value_column(df, station_key)
        d = pd.DataFrame({
            'dt': pd.to_datetime(df[time_col], errors='coerce'),
            'val': pd.to_numeric(df[val_col], errors='coerce'),
        }).dropna()
        d = d[(d['dt'].dt.year == year) & (d['dt'].dt.month == month)]
        if end_day is not None:
            d = d[d['dt'].dt.day <= end_day]
        if d.empty:
            return None
        d = d.copy()
        d['val_chart'] = d['val'] * 100.0 + chart_datum_offset_cm
        max_row = d.loc[d['val_chart'].idxmax()]
        min_row = d.loc[d['val_chart'].idxmin()]
        return {
            'hmax': int(round(max_row['val_chart'])),
            'hmax_day': max_row['dt'].day,
            'hmin': int(round(min_row['val_chart'])),
            'hmin_day': min_row['dt'].day,
        }
    except Exception as exc:
        logger.warning("Không lấy được Hx/Hm thực đo tháng %02d/%d cho trạm %s: %s",
                        month, year, station_key, exc)
        return None


def _month_forecast_extrema(dates, tide_dict, year, month):
    """Hx/Hm DỰ BÁO (mô hình điều hòa) lớn nhất/nhỏ nhất trong 1 tháng lịch,
    từ chuỗi ngày trả về bởi forecast_tide_from_observed — dùng cho Bảng 2."""
    best_hx, best_hx_time, best_hx_day = None, None, None
    best_hm, best_hm_time, best_hm_day = None, None, None
    for i, d_str in enumerate(dates):
        d = datetime.strptime(d_str, '%d/%m/%Y').date()
        if d.year != year or d.month != month:
            continue
        hx = int(tide_dict['tide_hx'][i])
        hm = int(tide_dict['tide_hm'][i])
        if best_hx is None or hx > best_hx:
            best_hx, best_hx_time, best_hx_day = hx, tide_dict['tide_hx_time'][i], d.day
        if best_hm is None or hm < best_hm:
            best_hm, best_hm_time, best_hm_day = hm, tide_dict['tide_hm_time'][i], d.day
    return best_hx, best_hx_time, best_hx_day, best_hm, best_hm_time, best_hm_day


def build_seasonal_data(
    df,
    start_month=None,
    start_year=None,
    representative_station="con_co",
    tide_corrections=None,
    forecaster="",
    issue_time="17h00",
    bulletin_num=None,
    issue_day=None,
):
    """
    Tính dữ liệu cho bản tin hải văn thời hạn MÙA (HVHM, 6 tháng: 3 tháng dự
    báo chi tiết + 3 tháng xu thế).

    df : DataFrame mực nước thực đo (giống các bản tin khác) — nên có tối
        thiểu ~2 tháng số liệu gần nhất để tính Bảng 1 hồi cứu.
    start_month/start_year : tháng đầu tiên của giai đoạn dự báo 3 tháng
        (mục 2). Mặc định: tháng kế tiếp theo mốc cuối dữ liệu.
    issue_day : ngày phát hành trong tháng phát tin (để cắt kỳ hồi cứu thứ 3
        "01-DD/tháng phát tin" ở Bảng 1 — đúng mẫu thật: bản tin phát ngày
        15/6 thì Bảng 1 hồi cứu tới "Từ 01-15/6", không phải hết cả tháng).
        Mặc định: lấy từ ngày cuối cùng có trong `df`, hoặc 15 nếu không rõ.
    representative_station : trạm đại diện cho Bảng 1 (mẫu thật dùng Cồn Cỏ).

    Trả về dict để truyền vào bulletin_generator.create_qtri_seasonal_bulletin().
    """
    tide_corrections = tide_corrections or {}

    if start_month is None or start_year is None:
        try:
            time_col = df.columns[0]
            last_obs = pd.to_datetime(df[time_col], errors='coerce').max()
            start_year, start_month = _add_months(last_obs.year, last_obs.month, 1)
        except Exception:
            now = datetime.now()
            start_year, start_month = _add_months(now.year, now.month, 1)

    # ---- Bảng 1: 2 tháng liền trước (đủ tháng) + phần đầu tháng phát tin
    # (thực đo) — ĐÚNG cấu trúc mẫu thật (QTRI_HVHM_20260615_1700.docx: bản
    # tin phát 15/6 có Bảng 1 gồm "Tháng 4/2026", "Tháng 5/2026", "Từ
    # 01-15/6/2026" — KHÔNG phải 2 tháng tròn như bản trước đây tính) ----
    issue_year, issue_month = _add_months(start_year, start_month, -1)
    m2_year, m2_month = _add_months(issue_year, issue_month, -2)
    m1_year, m1_month = _add_months(issue_year, issue_month, -1)

    if issue_day is None:
        try:
            last_obs_dt = pd.to_datetime(df[df.columns[0]], errors='coerce').max()
            if last_obs_dt.year == issue_year and last_obs_dt.month == issue_month:
                issue_day = last_obs_dt.day
            else:
                issue_day = 15
        except Exception:
            issue_day = 15

    table1_months = [(m2_year, m2_month), (m1_year, m1_month), (issue_year, issue_month)]
    table1_labels = [
        f"Tháng {m2_month}/{m2_year}",
        f"Tháng {m1_month}/{m1_year}",
        f"Từ 01-{issue_day:02d}/{issue_month}/{issue_year}",
    ]
    table1_rows = []
    for i, (yr, mo) in enumerate(table1_months):
        end_day = issue_day if i == 2 else None  # tháng thứ 3 chỉ tính đến ngày phát tin
        ext = _month_extrema_observed(df, representative_station, yr, mo, end_day=end_day)
        if ext is not None:
            # Sóng biển: không có nguồn khí hậu/lưu trữ sóng lịch sử trong dự
            # án (chỉ có ~10 ngày dự báo Copernicus, không phải số liệu quá
            # khứ) — để trống cho dự báo viên tự điền theo bản tin đã phát.
            ext['wave_max'] = None
            ext['wave_dir'] = None
            ext['wave_day'] = None
        table1_rows.append(ext)

    # ---- Bảng 2: 3 tháng dự báo chi tiết, cả 5 vùng ----
    forecast_months = [_add_months(start_year, start_month, i) for i in range(3)]
    last_fm_year, last_fm_month = forecast_months[-1]
    last_fm_day = calendar.monthrange(last_fm_year, last_fm_month)[1]
    month_end_date = datetime(last_fm_year, last_fm_month, last_fm_day).date()
    try:
        last_obs_date = pd.to_datetime(df[df.columns[0]], errors='coerce').max().date()
    except Exception:
        last_obs_date = datetime.now().date()
    days_needed = (month_end_date - last_obs_date).days + 10
    days_needed = max(days_needed, sum(calendar.monthrange(y, m)[1] for y, m in forecast_months) + 10)

    station_keys = sorted(set(REGION_TO_STATION.values()))
    per_station_tide = {}
    for station_key in station_keys:
        corr = tide_corrections.get(station_key, {})
        try:
            dates, tide_dict = forecast_tide_from_observed(
                df, station_key=station_key, forecast_days=days_needed,
                amplitude_scale=corr.get('amplitude_scale'),
                manual_offset_m=corr.get('manual_offset_m', 0.0),
                chart_datum_offset_cm=corr.get('chart_datum_offset_cm'),
            )
            per_station_tide[station_key] = (dates, tide_dict)
        except Exception as exc:
            logger.warning("Dự báo triều mùa thất bại cho trạm %s: %s", station_key, exc)
            per_station_tide[station_key] = (None, None)

    table2_data = {}
    for reg in REGIONS:
        station_key = REGION_TO_STATION[reg]
        dates, tide_dict = per_station_tide.get(station_key, (None, None))
        month_rows = []
        for yr, mo in forecast_months:
            if dates and tide_dict:
                hx, hx_t, hx_d, hm, hm_t, hm_d = _month_forecast_extrema(dates, tide_dict, yr, mo)
            else:
                hx = hx_t = hx_d = hm = hm_t = hm_d = None
            month_rows.append({
                'hx': hx, 'hx_time': hx_t, 'hx_day': hx_d,
                'hm': hm, 'hm_time': hm_t, 'hm_day': hm_d,
            })
        table2_data[reg] = month_rows

    xu_the_months = [_add_months(start_year, start_month, i) for i in range(3, 6)]

    period1_label = f"tháng {forecast_months[0][1]} - {forecast_months[-1][1]}/{forecast_months[-1][0]}"
    period2_label = f"tháng {xu_the_months[0][1]}/{xu_the_months[0][0]} đến tháng {xu_the_months[-1][1]}/{xu_the_months[-1][0]}"

    # Trích số liệu triều cao nhất thật (nếu có) cho câu mở đầu Bảng 1
    hmax_hint = ""
    valid_rows = [r for r in table1_rows if r]
    if valid_rows:
        best = max(valid_rows, key=lambda r: r['hmax'])
        hmax_hint = f" Mực nước đỉnh triều lớn nhất tại {REGION_DISPLAY.get(representative_station, representative_station)} đạt {best['hmax']/100:.2f} m."

    now = datetime.now()
    next_year, next_month = _add_months(start_year, start_month, 2)  # bản tin mùa kỳ tiếp theo cách 2 tháng

    data = {
        'bulletin_num': bulletin_num or f"HVHM-{((start_month - 1) // 3) + 1:02d}/QTRI",
        'issue_date': now.strftime('ngày %d tháng %m năm %Y'),
        'title_period': f"Từ tháng {forecast_months[0][1]}/{forecast_months[0][0]} đến tháng {xu_the_months[-1][1]}/{xu_the_months[-1][0]}",
        'table1_labels': table1_labels,
        'table1_rows': table1_rows,
        'table1_station_name': REGION_DISPLAY.get(representative_station, representative_station),
        'table1_period_text': f"từ tháng {table1_months[0][1]}/{table1_months[0][0]} đến ngày {issue_day:02d} tháng {table1_months[-1][1]}/{table1_months[-1][0]}",
        'sec1_text': (
            "Thời tiết trên vùng biển Quảng Trị bình thường, độ cao sóng phổ biến 0.50 - "
            "2.00m (dự báo viên cập nhật theo số liệu quan trắc thực tế trong kỳ)."
            + hmax_hint
        ),
        'forecast_months': forecast_months,
        'forecast_period_label': period1_label,
        'table2_data': table2_data,
        'regions': [(REGION_DISPLAY[r], r) for r in REGIONS],
        'sec2_text': (
            f"Mực nước ven biển chủ yếu dao động theo thủy triều và ở mức trung bình nhiều "
            f"năm cùng kỳ. Từ {period1_label} có khả năng xuất hiện XTNĐ trên khu vực Biển "
            f"Đông và có khả năng ảnh hưởng đến thời tiết tỉnh Quảng Trị, độ cao sóng vùng "
            f"biển ven bờ dao động từ {DEFAULT_WAVE_RANGE}m, vùng biển ngoài khơi Quảng Trị "
            "(bao gồm cả đặc khu Cồn Cỏ) dao động cao hơn. Dự báo viên bổ sung số đợt XTNĐ/"
            "triều cường dự kiến theo bản tin khí hậu tham khảo."
        ),
        'sec2_warning_text': (
            "Những ngày chịu ảnh hưởng của bão, ATNĐ, gió mùa Tây Nam độ cao sóng khu vực "
            "vùng biển ven bờ Quảng Trị có thể tăng cao hơn mức phổ biến; vùng biển ngoài "
            "khơi (bao gồm đảo Cồn Cỏ) có thể dao động mạnh hơn. Biển động đến động rất mạnh."
        ),
        'sec2_impact_text': (
            "Bão, ATNĐ và gió mùa Tây Nam có khả năng gây ra gió mạnh, sóng lớn ảnh hưởng "
            "đến các hoạt động của tàu thuyền và các hoạt động trên biển và ven biển, nuôi "
            "trồng, đánh bắt thủy sản tại vùng biển Quảng Trị. Các đợt triều cường nếu trùng "
            "vào thời kỳ có bão, ATNĐ và gió mùa Tây Nam sẽ gây nguy cơ sạt lở bờ biển, vùng "
            "cửa sông và ngập úng vùng trũng thấp."
        ),
        'xu_the_period_label': period2_label,
        'sec3_text': (
            "Mực nước ven biển chủ yếu dao động theo thủy triều và ở mức trung bình nhiều "
            f"năm cùng kỳ. Độ cao sóng tại trạm Hải văn Cồn Cỏ phổ biến ở mức {DEFAULT_WAVE_RANGE}m, "
            "những ngày có bão, ATNĐ và KKL sóng biển có thể tăng cao hơn nhiều. Biển động "
            "đến động rất mạnh."
        ),
        'sec3_warning_text': (
            f"Từ {period2_label}, vùng biển Quảng Trị có khả năng xuất hiện các đợt triều "
            "cường và XTNĐ hoạt động trên Biển Đông — dự báo viên bổ sung số đợt/mức nước "
            "đỉnh triều dự kiến theo bản tin khí hậu tham khảo."
        ),
        'sec3_impact_text': (
            "Những ngày ảnh hưởng của bão/ATNĐ, toàn bộ tàu thuyền và các hoạt động trên "
            "biển và ven biển, nuôi trồng, đánh bắt thủy sản tại vùng biển Quảng Trị đều có "
            "nguy cơ chịu tác động của gió mạnh, sóng lớn. Các đợt triều cường nếu trùng vào "
            "thời kỳ ảnh hưởng bão, ATNĐ sẽ gây nguy cơ sạt lở bờ biển, vùng cửa sông và ngập "
            "úng vùng trũng thấp."
        ),
        'next_issue_time': f"17h00 ngày 15/{next_month:02d}/{next_year}",
        'issue_time': issue_time,
        'forecasters': forecaster,
    }
    return data


def build_seasonal_dossier_data(seasonal_data: dict, shift_leader="", forecasters="",
                                 bulletin_file_ref="", data_sources_note="", quality_note="Đầy đủ; kịp thời; Độ tin cậy: Đạt"):
    """Chuyển dữ liệu build_seasonal_data() sang cấu trúc cho
    bulletin.dossier_generator.create_forecast_dossier() — style='simple',
    đúng khung mẫu HS_QTRI_HVHM_20260615_1700.docx (bảng 3 cột, mã a/b/c,
    mục 3 nhóm theo 'Dự báo sóng, dòng chảy' / 'Dự báo thuỷ triều'). Trang 2
    nhúng lại ĐÚNG Bảng 2 (thủy triều 3 tháng tới) của bản tin chính."""
    return {
        'style': 'simple',
        'title': "HỒ SƠ DỰ BÁO, CẢNH BÁO HẢI VĂN THỜI HẠN MÙA",
        'issue_time_text': f"{seasonal_data.get('issue_time', '17h00')} {seasonal_data.get('issue_date', '')}",
        'unit_text': "Đài KTTV tỉnh Quảng Trị.",
        'shift_leader': shift_leader,
        'forecasters': forecasters or seasonal_data.get('forecasters', ''),
        'section1_items': [
            ("a", "Thu thập số liệu quan trắc", data_sources_note or "Số liệu mực nước, sóng thực đo tại trạm KTHV (Excel)"),
            ("b", "Xử lý các loại thông tin dữ liệu",
             "Phân tích, kiểm tra tính hợp lý của chuỗi số liệu; tính toán đặc trưng các yếu tố sóng, dòng chảy, mực nước theo từng tháng"),
            ("c", "Cập nhật số liệu",
             "Cập nhật số liệu thực đo đã thu thập vào cơ sở dữ liệu dự báo và mô hình dự báo"),
            ("d", "Thu thập số liệu, dữ liệu về môi trường, điều kiện sống, cơ sở hạ tầng, các hoạt động kinh tế - xã hội", "Không có"),
        ],
        'section2_items': [
            ("a", "Phân tích các dữ liệu quan trắc để xác định điều kiện hải văn đã qua và hiện tại",
             seasonal_data.get('sec1_text', '')),
            ("b", "Phân tích diễn biến của yếu tố mực nước trên cơ sở dữ liệu quan trắc và sản phẩm mô hình dự báo số trị",
             ""),
            ("c", "Phân tích số liệu, dữ liệu về môi trường, điều kiện sống, cơ sở hạ tầng, các hoạt động kinh tế - xã hội", "Không có"),
        ],
        'section3_items': [
            ("Dự báo sóng, dòng chảy", "Phương án dựa trên cơ sở phương pháp giải tích",
             seasonal_data.get('sec2_text', '')),
            (None, "Phương án dựa trên cơ sở phương pháp mô hình số trị",
             seasonal_data.get('sec2_warning_text', '')),
            ("Dự báo thuỷ triều", "Phương án dựa trên cơ sở phương pháp phân tích điều hòa", "Ghi trang sau"),
            (None, "Phương án dựa trên cơ sở phương pháp mô hình số trị", ""),
        ],
        'section4_extra': None,
        'section5_file_ref': bulletin_file_ref,
        'section6_text': (
            "VP BCH PTDS tỉnh; Báo & Đài PTTH Quảng Trị; Trung tâm Dự báo KTTV quốc "
            "gia; Phòng Quản lý DB & TT, DL KTTV (Cục KTTV); Trung tâm TT&DL KTTV (Cục "
            "KTTV); Phòng Dự báo (Đài Trung Bộ); Các trạm KTTV, Ra đa trong tỉnh; Lưu: "
            "Đài tỉnh."
        ),
        'section7_text': "Không",
        'section8_text': quality_note,
        'discussion_title': "HỒ SƠ DỰ BÁO, CẢNH BÁO HẢI VĂN THỜI HẠN MÙA",
        'discussion_body': [
            (f"Dự báo hải văn {seasonal_data.get('forecast_period_label', '')}:", seasonal_data.get('sec2_text', '')),
        ],
        'zone_table_kind': 'seasonal_appendix',
        'zone_table_data': seasonal_data,
        'zone_table_intro': (
            f"Sau khi thảo luận, trưởng ca dự báo chốt trị số {seasonal_data.get('forecast_period_label', '')} "
            "theo phụ lục 2."
        ),
        'discussion_warning': seasonal_data.get('sec2_warning_text', ''),
        'discussion_impact': seasonal_data.get('sec2_impact_text', ''),
        'discussion_forecaster_note': "Dự báo viên: Nhất trí với ý kiến của đồng chí trưởng ca.",
    }
