# ==========================================
# bulletin/warning_data.py
# Tính dữ liệu cho "TIN DỰ BÁO GIÓ MẠNH, SÓNG LỚN TRÊN VÙNG BIỂN TỈNH QUẢNG TRỊ"
# (bản tin hải văn nguy hiểm, khác bản tin 10 ngày thường) — dùng CHUNG
# nguồn dữ liệu sóng thật (Copernicus, qua marine_data.py) và gió thật
# (Open-Meteo, qua core/weather_forecast.py) đã có sẵn trong dự án.
#
# Bản tin này dùng 3 vùng biển (Bắc / Nam / Đặc khu Cồn Cỏ) — khác 5 vùng
# của bản tin 10 ngày thường — đúng theo mẫu thực tế của Đài KTTV Quảng Trị.
# ==========================================

import logging
from datetime import datetime, timedelta

from config import WAVE_FILE
from core.beaufort import beaufort_scale, beaufort_text, sea_state_text
from core.weather_forecast import get_weather_daily
from core.wave_forecast import get_wave_daily_at
from station_config import FORECAST_REGIONS

logger = logging.getLogger(__name__)

# Ánh xạ 3 vùng của bản tin nguy hiểm -> các vùng dự báo chính thức
# (FORECAST_REGIONS) dùng để lấy sóng thật, lấy giá trị LỚN NHẤT giữa các
# vùng con để thiên về an toàn/cảnh báo.
WARNING_ZONES = {
    "Vùng biển phía Bắc": ["offshore_north", "coastal_north"],
    "Vùng biển phía Nam": ["offshore_south", "coastal_south"],
    "Đặc khu Cồn Cỏ": ["con_co"],
}

# Cấp độ rủi ro thiên tai do gió mạnh trên biển — XẤP XỈ theo cấp gió giật
# lớn nhất, tham khảo tinh thần Quyết định 18/2021/QĐ-TTg. Đây là ước lượng
# tự động, dự báo viên cần tự kiểm tra/điều chỉnh lại theo quy định hiện
# hành trước khi ban hành chính thức.
def _risk_level(max_gust_force: int) -> str:
    if max_gust_force >= 12:
        return "Cấp 4"
    if max_gust_force >= 10:
        return "Cấp 3"
    if max_gust_force >= 8:
        return "Cấp 2"
    if max_gust_force >= 6:
        return "Cấp 1"
    return "Chưa đến mức cảnh báo"


def _wave_range_for_zone(region_keys, day_idx):
    """Lấy khoảng độ cao sóng (m) LỚN NHẤT giữa các vùng con tại ngày `day_idx`."""
    best = None
    for key in region_keys:
        region = FORECAST_REGIONS[key]
        daily = get_wave_daily_at(str(WAVE_FILE), region["lat"], region["lon"], days=day_idx + 1)
        w = daily[day_idx]
        if best is None or w["hs_max"] > best["hs_max"]:
            best = w
    return best["hs_min"], best["hs_max"]


def build_warning_data(forecaster="", issue_time="16h00"):
    """
    Tính toàn bộ dữ liệu cho Tin dự báo gió mạnh, sóng lớn, dựa trên gió
    thật (Open-Meteo) và sóng thật (Copernicus) đã có sẵn trong dự án.

    Trả về dict để truyền vào bulletin_generator.create_qtri_warning_bulletin().
    Nếu không đọc được dữ liệu gió/sóng thật, tự dùng giá trị dự phòng an
    toàn (không raise exception) — giống các phần khác của dự án.
    """
    wind_daily = get_weather_daily(days=3)  # [hôm nay, 24h tới, ngày kia]
    if not wind_daily:
        wind_daily = [
            {"wind_speed_ms": 8.0, "wind_dir_text": "Đông Bắc"} for _ in range(3)
        ]

    # ---- Cấp gió + hướng cho từng mốc thời gian ----
    def _force_info(day_idx):
        w = wind_daily[min(day_idx, len(wind_daily) - 1)]
        speed = w.get("wind_speed_ms", 8.0)
        force_avg = beaufort_scale(speed)
        # Giật ước lượng ~+30% tốc độ trung bình, đảm bảo LUÔN cao hơn cấp
        # trung bình ít nhất 1 cấp (khớp cách trình bày thực tế của bản tin,
        # không có trường hợp "giật" bằng đúng cấp gió trung bình).
        force_gust = max(beaufort_scale(speed * 1.3), force_avg + 1)
        return force_avg, force_gust, w.get("wind_dir_text", "Đông Bắc")

    force0_avg, force0_gust, dir0 = _force_info(0)
    force1_avg, force1_gust, dir1 = _force_info(1)
    force2_avg, force2_gust, dir2 = _force_info(2)

    # ---- Sóng toàn tỉnh (lớn nhất giữa mọi vùng) cho mục 1 (hiện trạng) ----
    all_zone_keys = [k for keys in WARNING_ZONES.values() for k in keys]
    wave0_min, wave0_max = _wave_range_for_zone(all_zone_keys, day_idx=0)

    # ---- Bảng dự báo 24h tới: từng vùng (Bắc / Nam / Cồn Cỏ) ----
    zone_rows = []
    for zone_name, region_keys in WARNING_ZONES.items():
        w_min, w_max = _wave_range_for_zone(region_keys, day_idx=1)
        zone_rows.append({
            "zone": zone_name,
            "wind_text": beaufort_text(force1_avg, force1_gust),
            "wave_range": f"{w_min:.1f} - {w_max:.1f}",
            "wave_dir": dir1,
        })

    # ---- Sóng toàn tỉnh cho mục 3 (cảnh báo ngày kia) ----
    wave2_min, wave2_max = _wave_range_for_zone(all_zone_keys, day_idx=2)

    max_gust = max(force0_gust, force1_gust, force2_gust)
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    day_after = now + timedelta(days=2)

    sea_state = sea_state_text

    data = {
        "bulletin_num": f"HVNH-14/{issue_time}/QTRI",
        "issue_date": now.strftime("ngày %d tháng %m năm %Y"),
        "past_text": (
            f"Vùng biển Quảng Trị (bao gồm đặc khu Cồn Cỏ) có gió {dir0} "
            f"{beaufort_text(force0_avg, force0_gust)}; sóng biển cao "
            f"{wave0_min:.1f}-{wave0_max:.1f}m. {sea_state(wave0_max)}."
        ),
        "next24h_text": (
            f"Vùng biển Quảng Trị (bao gồm đặc khu Cồn Cỏ) có mưa, mưa rào rải rác. "
            f"Gió {dir1} {beaufort_text(force1_avg, force1_gust)}; sóng biển cao "
            f"{wave0_min:.1f}-{wave0_max:.1f}m. {sea_state(wave0_max)}."
        ),
        "zone_rows": zone_rows,
        "time_range_text": f"Đêm {now.strftime('%d')} và ngày {tomorrow.strftime('%d/%m')}",
        "warning_text": (
            f"Đêm {tomorrow.strftime('%d')} ngày {day_after.strftime('%d/%m')}, trên vùng biển "
            f"Quảng Trị (bao gồm đặc khu Cồn Cỏ) có mưa vài nơi, gió {dir2} "
            f"{beaufort_text(force2_avg, force2_gust)}, sóng biển cao "
            f"{wave2_min:.1f}-{wave2_max:.1f}m. {sea_state(wave2_max)}."
        ),
        "risk_level": _risk_level(max_gust),
        "impact_text": (
            "Toàn bộ tàu thuyền và các hoạt động khác tại vùng biển Quảng Trị đều có "
            "nguy cơ cao chịu tác động của mưa dông và gió mạnh, sóng lớn."
            if max_gust >= 6 else
            "Tàu thuyền hoạt động trên vùng biển Quảng Trị cần chú ý theo dõi các bản "
            "tin dự báo tiếp theo."
        ),
        "next_issue_time": f"10h00 ngày {tomorrow.strftime('%d/%m/%Y')}",
        "issue_time": issue_time,
        "forecasters": forecaster,
    }
    return data


def build_warning_dossier_data(warning_data: dict, shift_leader="", forecasters="",
                                bulletin_file_ref="", data_sources_note="", quality_note=""):
    """
    Chuyển dữ liệu đã tính bởi build_warning_data() sang đúng cấu trúc mà
    bulletin.dossier_generator.create_forecast_dossier() cần, để xuất hồ sơ
    HS_QTRI_HVNH_... đi kèm bản tin (đúng khung mẫu HS_QTRI_HVNH_20260103_1600.docx).

    Các trường KHÔNG tính được từ dữ liệu (nguồn ảnh mây/rada tham khảo,
    đánh giá chất lượng bản tin TRƯỚC — bản tin đã phát, không phải bản tin
    đang tạo) để mặc định rỗng/gợi ý — dự báo viên tự điền qua tham số hoặc
    sửa tay trên giao diện trước khi xuất.
    """
    zone_table = [
        {
            'zone': zr.get('zone', ''),
            'wind': zr.get('wind_text', ''),
            'wave_range': zr.get('wave_range', ''),
            'wave_dir': zr.get('wave_dir', ''),
        }
        for zr in warning_data.get('zone_rows', [])
    ]

    return {
        'title': "HỒ SƠ DỰ BÁO GIÓ MẠNH, SÓNG LỚN TRÊN VÙNG BIỂN",
        'issue_time_text': f"{warning_data.get('issue_time', '16h00')} {warning_data.get('issue_date', '')}",
        'unit_text': "Đài KTTV tỉnh Quảng Trị.",
        'shift_leader': shift_leader,
        'forecasters': forecasters or warning_data.get('forecasters', ''),
        'section1_conclusion': "Đầy đủ",
        'section1_rows': [
            ("Các loại bản tin", data_sources_note or "Tham khảo bản tin của TTDB Quốc Gia và Đài khu vực"),
            ("Số liệu viễn thám, quan trắc", ""),
            ("Các sản phẩm mô hình", ""),
        ],
        'section2_conclusion': warning_data.get('past_text', ''),
        'section3_conclusion': (
            f"1. Dự báo\n\n{warning_data.get('next24h_text', '')}\n\n"
            f"2. Cảnh báo\n\n{warning_data.get('warning_text', '')}"
        ),
        'section5_file_ref': bulletin_file_ref,
        'section6_text': (
            "Văn phòng tỉnh ủy; Văn phòng UBND tỉnh; BCH PCTT & TKCN tỉnh; Sở NN & MT "
            "tỉnh; Báo và Đài PTTH tỉnh; Phòng QLDB&TT, DL KTTV (Cục KTTV); Trung tâm "
            "TT&DL KTTV (Cục KTTV); Phòng Dự báo (Đài Trung Bộ); Các trạm KTTV, Ra đa; "
            "Lưu Đài tỉnh."
        ),
        'section7_text': "Không cập nhật/ bổ sung",
        'section8_text': quality_note,
        'discussion_title': "HỒ SƠ DỰ BÁO GIÓ MẠNH, SÓNG LỚN TRÊN VÙNG BIỂN",
        'discussion_intro': (
            f"{warning_data.get('next24h_text', '')}"
        ),
        'discussion_time_range': warning_data.get('time_range_text', ''),
        'discussion_zone_table': zone_table,
        'discussion_warning': warning_data.get('warning_text', ''),
        'discussion_risk': warning_data.get('risk_level', ''),
        'discussion_impact': warning_data.get('impact_text', ''),
        'discussion_forecaster_note': "Dự báo viên: Nhất trí với ý kiến của đồng chí trưởng ca.",
    }
