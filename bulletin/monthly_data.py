# ==========================================
# bulletin/monthly_data.py
# Tính dữ liệu cho "BẢN TIN DỰ BÁO, CẢNH BÁO HẢI VĂN THỜI HẠN THÁNG"
# (bản tin HV1T) — khớp mẫu thật QTRI_HV1T_20260801_1600.docx.
#
# Khác bản tin 10 ngày (HVHV):
#   - Bảng thủy triều chia 3 kỳ trong tháng (01-10 / 11-20 / 21-cuối tháng),
#     mỗi kỳ lấy 1 đỉnh (Hx) và 1 chân (Hm) triều LỚN NHẤT/NHỎ NHẤT trong cả
#     kỳ (không phải từng ngày như bảng 2/3 của HVHV).
#   - Thủy triều vẫn dùng ĐÚNG mô hình điều hòa chuẩn (bulletin/tide_model.py)
#     đã có sẵn — mô hình thiên văn nên ngoại suy xa (~1 tháng) vẫn hợp lệ,
#     khác sóng/dòng chảy (mô hình đại dương Copernicus chỉ có ~10 ngày dự
#     báo thật).
#   - Sóng biển: CHỈ có dữ liệu thật (Copernicus) cho ~10 ngày đầu (kỳ 1).
#     Kỳ 2/3 KHÔNG có nguồn dữ liệu thật nào trong dự án (không có mô hình
#     sóng hạn tháng/khí hậu sóng) — dùng giá trị mặc định có thể sửa tay,
#     đúng tinh thần "dự phòng an toàn, không làm gãy app" đã áp dụng cho
#     toàn bộ dự án (xem README).
#   - Phần văn bản "Phân tích tháng trước" / "Dự báo tháng này" bản chất là
#     nhận định khí hậu/synop của dự báo viên — không có nguồn số liệu lịch
#     sử (chỉ có dữ liệu Excel do người dùng tải lên + ~10 ngày Copernicus),
#     nên để MẶC ĐỊNH placeholder ngắn kèm số liệu thật trích ra được (đỉnh
#     triều cao nhất/sóng lớn nhất trong dữ liệu đã tải lên nếu có), dự báo
#     viên sửa tay trên giao diện trước khi xuất — giống hệt cách app.py đã
#     làm với bản tin 10 ngày/tin nguy hiểm (xem "Đã thêm: xem trước & sửa
#     trực tiếp" trong README).
# ==========================================

from __future__ import annotations

import calendar
import logging
from datetime import datetime, timedelta

from bulletin.area_data import forecast_tide_from_observed, STATION_COLUMN_KEYWORDS, _cm_to_m_str
from bulletin.marine_data import build_wave_current_tables, REGION_TO_STATION, degrees_to_text
from station_config import FORECAST_REGIONS

logger = logging.getLogger(__name__)

REGIONS = ['offshore_north', 'offshore_south', 'coastal_north', 'coastal_south', 'con_co']

REGION_DISPLAY = {
    'offshore_north': 'Vùng biển ngoài khơi phía Bắc',
    'offshore_south': 'Vùng biển ngoài khơi phía Nam',
    'coastal_north': 'Vùng biển ven bờ phía Bắc',
    'coastal_south': 'Vùng biển ven bờ phía Nam',
    'con_co': 'Cồn Cỏ',
}

# Sóng biển mặc định (dự phòng) cho kỳ 2/3 trong tháng — không có nguồn dữ
# liệu thật (xem giải thích module docstring). Dự báo viên SỬA TAY trên
# giao diện trước khi xuất, đây chỉ là khởi điểm hợp lý theo mùa.
DEFAULT_WAVE_RANGE = "0.5 - 1.5"


def _period_bounds(year, month):
    """Trả về 3 khoảng ngày trong tháng: (01, 10), (11, 20), (21, cuối tháng)."""
    last_day = calendar.monthrange(year, month)[1]
    return [(1, 10), (11, 20), (21, last_day)]


def _next_month(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _prev_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _tide_period_extrema(dates_10plus, tide_dict, start_day, end_day, month, year):
    """Từ chuỗi triều theo NGÀY (dates_str + tide_dict trả về bởi
    forecast_tide_from_observed), lọc đúng khoảng [start_day, end_day] của
    `month`/`year`, lấy Hx LỚN NHẤT và Hm NHỎ NHẤT trong cả khoảng, kèm thời
    điểm xuất hiện (giờ + ngày)."""
    best_hx, best_hx_dt = None, None
    best_hm, best_hm_dt = None, None

    for i, d_str in enumerate(dates_10plus):
        d = datetime.strptime(d_str, '%d/%m/%Y').date()
        if d.year != year or d.month != month or not (start_day <= d.day <= end_day):
            continue
        hx = int(tide_dict['tide_hx'][i])
        hm = int(tide_dict['tide_hm'][i])
        if best_hx is None or hx > best_hx:
            best_hx = hx
            best_hx_dt = (tide_dict['tide_hx_time'][i], d.day)
        if best_hm is None or hm < best_hm:
            best_hm = hm
            best_hm_dt = (tide_dict['tide_hm_time'][i], d.day)

    return best_hx, best_hx_dt, best_hm, best_hm_dt


def build_monthly_data(
    df,
    target_month=None,
    target_year=None,
    tide_corrections=None,
    wave_scale=1.0,
    forecaster="",
    issue_time="16h00",
    bulletin_num=None,
):
    """
    Tính toàn bộ dữ liệu cho bản tin hải văn thời hạn THÁNG (HV1T).

    df : DataFrame mực nước thực đo (giống bản tin 10 ngày), cột 1 = thời
        gian, các cột sau = mực nước từng trạm. Dữ liệu nên có tới cuối
        tháng liền trước tháng dự báo (bản tin phát ngày 01 hàng tháng).
    target_month/target_year : tháng/năm cần dự báo. Mặc định: tháng kế
        tiếp theo mốc thời gian cuối cùng có trong `df` (đúng thực tế phát
        hành bản tin ngày 01 đầu tháng).
    tide_corrections, wave_scale : xem bulletin/area_data.py::build_area_data
        — cùng cơ chế hiệu chỉnh RIÊNG từng trạm/vùng.

    Trả về dict để truyền vào bulletin_generator.create_qtri_monthly_bulletin().
    Không raise exception khi thiếu dữ liệu sóng/vượt hạn dự báo Copernicus —
    tự dùng giá trị dự phòng, giống toàn bộ phần còn lại của dự án.
    """
    tide_corrections = tide_corrections or {}

    # ---- Xác định tháng dự báo ----
    if target_month is None or target_year is None:
        try:
            time_col = df.columns[0]
            last_obs = pd_to_datetime_max(df[time_col])
            target_year, target_month = _next_month(last_obs.year, last_obs.month)
        except Exception:
            now = datetime.now()
            target_year, target_month = _next_month(now.year, now.month)

    last_day = calendar.monthrange(target_year, target_month)[1]
    periods = _period_bounds(target_year, target_month)
    period_labels = [f"{p[0]:02d}-{p[1]:02d}" for p in periods]

    # ---- Số ngày cần dự báo: từ NGAY SAU mốc quan trắc cuối cùng cho tới hết
    # tháng dự báo (không phải cố định "số ngày trong tháng + đệm") — nếu dữ
    # liệu Excel người dùng tải lên có mốc cuối SỚM hơn đầu tháng dự báo khá
    # xa (ví dụ còn thiếu vài tuần số liệu mới nhất), cần dự báo dài hơn để
    # phủ hết tới cuối tháng, nếu không kỳ cuối tháng (21-cuối tháng) sẽ rơi
    # ngoài phạm vi và ra toàn "-" .
    try:
        last_obs_date = pd_to_datetime_max(df[df.columns[0]]).date()
    except Exception:
        last_obs_date = datetime.now().date()
    month_end_date = datetime(target_year, target_month, last_day).date()
    days_needed = (month_end_date - last_obs_date).days + 5
    days_needed = max(days_needed, last_day + 5)

    # ---- Thủy triều: dự báo đủ số ngày trong tháng, riêng từng trạm ----
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
            logger.warning(
                "Dự báo triều tháng thất bại cho trạm %s, dùng dữ liệu dự phòng: %s",
                station_key, exc,
            )
            per_station_tide[station_key] = (None, None)

    # ---- Sóng biển thật (Copernicus, ~10 ngày đầu tháng = kỳ 1) ----
    wave_tables = build_wave_current_tables(forecast_days=10, wave_scale=wave_scale)

    # ---- Đóng gói Bảng 1: mỗi vùng x mỗi kỳ ----
    table_data = {}
    max_wave_period1 = None
    for reg in REGIONS:
        station_key = REGION_TO_STATION[reg]
        dates, tide_dict = per_station_tide.get(station_key, (None, None))

        hx_list, hx_time_list, hm_list, hm_time_list, wave_list = [], [], [], [], []
        for p_idx, (start_day, end_day) in enumerate(periods):
            if dates and tide_dict:
                hx, hx_dt, hm, hm_dt = _tide_period_extrema(
                    dates, tide_dict, start_day, end_day, target_month, target_year
                )
            else:
                hx, hx_dt, hm, hm_dt = None, None, None, None

            hx_list.append(_cm_to_m_str(hx) if hx is not None else "-")
            hx_time_list.append(f"{hx_dt[0]}/{hx_dt[1]:02d}" if hx_dt else "-")
            hm_list.append(_cm_to_m_str(hm) if hm is not None else "-")
            hm_time_list.append(f"{hm_dt[0]}/{hm_dt[1]:02d}" if hm_dt else "-")

            if p_idx == 0:
                # Kỳ 1: lấy khoảng min-max sóng thật trong 10 ngày Copernicus
                heights = wave_tables.get(reg, {}).get('wave_height', [])
                if heights:
                    mins = [float(h.split(' - ')[0]) for h in heights if ' - ' in h]
                    maxs = [float(h.split(' - ')[1]) for h in heights if ' - ' in h]
                    if mins and maxs:
                        w_str = f"{min(mins):.1f} - {max(maxs):.1f}"
                        if max_wave_period1 is None or max(maxs) > max_wave_period1:
                            max_wave_period1 = max(maxs)
                    else:
                        w_str = DEFAULT_WAVE_RANGE
                else:
                    w_str = DEFAULT_WAVE_RANGE
            else:
                # Kỳ 2/3: ngoài hạn dự báo sóng thật -> dự phòng, sửa tay
                w_str = DEFAULT_WAVE_RANGE
            wave_list.append(w_str)

        table_data[reg] = {
            'tide_hx': hx_list,
            'tide_hx_time': hx_time_list,
            'tide_hm': hm_list,
            'tide_hm_time': hm_time_list,
            'wave_height': wave_list,
        }

    now = datetime.now()
    prev_year, prev_month = _prev_month(target_year, target_month)
    next_year, next_month = _next_month(target_year, target_month)

    month_wave_hint = (
        f" (số liệu thật 10 ngày đầu tháng: sóng lớn nhất đạt khoảng {max_wave_period1:.1f}m)"
        if max_wave_period1 else ""
    )

    data = {
        'bulletin_num': bulletin_num or f"HVHD-{target_month:02d}/QTRI",
        'issue_date': now.strftime('ngày %d tháng %m năm %Y'),
        'title_period': f"Tháng {target_month} năm {target_year}",
        'prev_month_label': f"tháng {prev_month} năm {prev_year}",
        'this_month_label': f"tháng {target_month} năm {target_year}",
        'period_labels': period_labels,
        'table_data': table_data,
        'regions': [(REGION_DISPLAY[r], r) for r in REGIONS],
        # ---- Văn bản mục 1: phân tích tháng trước (dự báo viên tự biên tập) ----
        'sec1_wave_text': (
            f"Trong {f'tháng {prev_month} năm {prev_year}'}, độ cao sóng tại trạm Hải văn "
            f"Cồn Cỏ phổ biến từ 0.25-2.0m, biển bình thường; cần dự báo viên bổ sung/"
            f"hiệu chỉnh theo số liệu quan trắc/bản tin đã phát trong tháng."
        ),
        'sec1_tide_text': (
            "Chế độ triều khu vực ven biển phía Bắc Quảng Trị chịu ảnh hưởng bởi chế độ "
            "nhật triều không đều, khu vực phía Nam chịu ảnh hưởng bởi chế độ bán nhật "
            "triều không đều. Dự báo viên bổ sung ngày xuất hiện triều cường thực tế."
        ),
        # ---- Văn bản mục 2: dự báo tháng này ----
        'sec2_wave_text': (
            f"Trong {f'tháng {target_month} năm {target_year}'}, độ cao sóng vùng biển khu vực "
            f"Quảng Trị phổ biến dao động từ {DEFAULT_WAVE_RANGE}m{month_wave_hint}. Riêng một "
            "số ngày trong tháng khả năng ảnh hưởng của Bão/ATNĐ và gió giật trong mưa dông "
            "nên độ cao sóng lớn nhất có khả năng đạt 2.0 - 3.0m, biển động."
        ),
        'sec2_tide_text': (
            "Vùng ven biển tỉnh Quảng Trị có khả năng xuất hiện thời kỳ triều cường — dự báo "
            "viên bổ sung các đợt cụ thể theo bảng thủy triều bên dưới."
        ),
        'sec3_text': (
            "Trong tháng những ngày chịu ảnh hưởng của dải hội tụ nhiệt đới/XTNĐ hoạt động "
            "trên Biển Đông, gió mùa có cường độ trung bình đến mạnh và gió giật trong mưa "
            "dông nên vùng biển tỉnh Quảng Trị có khả năng xảy ra các hiện tượng hải văn "
            "nguy hiểm như lốc xoáy, gió giật mạnh, sóng lớn."
        ),
        'sec4_text': (
            "Gió mạnh, lốc xoáy, sóng lớn có thể gây nguy hiểm cho việc nuôi trồng thủy sản, "
            "các hoạt động đánh bắt thuỷ hải sản trên biển, hoạt động hàng hải và du lịch "
            "biển và ven biển."
        ),
        'next_issue_time': f"16h00 ngày 01/{next_month:02d}/{next_year}",
        'issue_time': issue_time,
        'forecasters': forecaster,
    }
    return data


def pd_to_datetime_max(series):
    import pandas as pd
    return pd.to_datetime(series, errors='coerce').max()


def build_monthly_dossier_data(monthly_data: dict, shift_leader="", forecasters="",
                                bulletin_file_ref="", data_sources_note="", quality_note="Đầy đủ; kịp thời; độ tin cậy: Đạt"):
    """Chuyển dữ liệu build_monthly_data() sang cấu trúc cho
    bulletin.dossier_generator.create_forecast_dossier() — style='simple',
    đúng khung mẫu HS_QTRI_HV1T_20260801_1600.docx (bảng 3 cột, mã a/b/c,
    KHÔNG có hàng 'Kết luận' riêng — khác cấu trúc 4 cột của tin nguy hiểm).
    Trang 2 nhúng lại ĐÚNG Bảng 1 (vùng biển 3 kỳ/tháng) của bản tin chính."""
    return {
        'style': 'simple',
        'title': "HỒ SƠ DỰ BÁO, CẢNH BÁO HẢI VĂN THỜI HẠN THÁNG",
        'issue_time_text': f"{monthly_data.get('issue_time', '16h00')} {monthly_data.get('issue_date', '')}",
        'unit_text': "Đài KTTV tỉnh Quảng Trị - Đài Khí tượng Thủy văn Trung Bộ",
        'shift_leader': shift_leader,
        'forecasters': forecasters or monthly_data.get('forecasters', ''),
        'section1_items': [
            ("a", "Thu thập số liệu quan trắc các yếu tố khí tượng: Gió, khí áp", data_sources_note or ""),
            ("b", "Thu thập số liệu quan trắc các yếu tố hải văn: Mực nước triều, độ cao sóng",
             "Số liệu mực nước trạm hải văn (Excel)"),
            ("c", "Thu thập số liệu dự báo khí tượng trên biển",
             "Sản phẩm mô hình dự báo của Trung tâm Dự báo KTTV Quốc gia, ECMWF, GFS..."),
            ("d", "Cập nhật số liệu phương án dự báo hải văn",
             "Mô hình điều hòa triều (8 hằng số chính); Copernicus Marine (sóng biển 10 ngày đầu tháng)"),
        ],
        'section2_items': [
            ("a", "Phân tích diễn biến thời tiết biển", monthly_data.get('sec1_wave_text', '')),
            ("b", "Phân tích diễn biến các hiện tượng hải văn", monthly_data.get('sec1_tide_text', '')),
        ],
        'section3_items': [
            (None, "Phương án 1", f"{monthly_data.get('sec2_wave_text', '')}"),
            (None, "Phương án 2", f"{monthly_data.get('sec2_tide_text', '')}"),
        ],
        'section4_extra': [
            ("Dự báo lượng gió", "Đủ độ tin cậy"),
            ("Dự báo hải văn", "Đủ độ tin cậy"),
        ],
        'section5_file_ref': bulletin_file_ref,
        'section6_text': (
            "Văn phòng tỉnh ủy; Văn phòng UBND tỉnh; BCH PTDS tỉnh; Sở NN&MT tỉnh; Báo "
            "và Đài PTTH tỉnh; Phòng QLDB&TT, DL KTTV (Cục KTTV); Trung tâm TT&DL KTTV "
            "(Cục KTTV); Phòng Dự báo KTTV (Đài KTTV Trung Bộ); Các trạm KTTV, rada; "
            "Lưu Đài tỉnh."
        ),
        'section7_text': "Không",
        'section8_text': quality_note,
        'discussion_title': "HỒ SƠ DỰ BÁO, CẢNH BÁO HẢI VĂN THỜI HẠN THÁNG",
        'discussion_body': [
            ("Sóng biển:", monthly_data.get('sec2_wave_text', '')),
            ("Triều cường:", monthly_data.get('sec2_tide_text', '')),
        ],
        'zone_table_kind': 'monthly',
        'zone_table_data': monthly_data,
        'discussion_warning': monthly_data.get('sec3_text', ''),
        'discussion_impact': monthly_data.get('sec4_text', ''),
        'discussion_forecaster_note': "Dự báo viên: Nhất trí với ý kiến của đồng chí trưởng ca.",
    }
