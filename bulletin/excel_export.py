# ==========================================
# bulletin/excel_export.py
# Xuất file Excel số liệu sóng & dòng chảy theo từng mốc thời gian thật
# trong file .nc Copernicus đã tải (thường là 10 ngày tới) cho cả 5 vùng
# dự báo — phục vụ dự báo viên xem/đối chiếu số liệu chi tiết theo giờ,
# khác với bảng 2/3 trong bản tin (chỉ có giá trị min-max mỗi ngày).
#
# LƯU Ý: đây là dữ liệu MÔ HÌNH Copernicus (phân tích + dự báo đại dương),
# KHÔNG phải số liệu quan trắc thực đo tại phao/trạm — đặt tên sheet rõ
# ràng để không gây hiểu nhầm là số liệu đo đạc thật.
# ==========================================

import logging

import pandas as pd

from config import WAVE_FILE, CURRENT_FILE
from core.wave_forecast import get_wave_forecast_at
from core.current_forecast import get_current_forecast_at
from station_config import FORECAST_REGIONS

logger = logging.getLogger(__name__)


def build_marine_excel(output_path):
    """
    Xuất file Excel 2 sheet (Sóng, Dòng chảy) — mỗi vùng dự báo 1 cặp cột
    (Hs/Hướng hoặc Vận tốc/Hướng), theo đúng mốc thời gian thật có trong
    file .nc đã tải (sóng lấy mẫu 3 giờ/lần, dòng chảy 1 giờ/lần — KHÔNG
    nội suy giả để ép về cùng tần suất).

    Trả về output_path nếu tạo thành công, None nếu chưa có dữ liệu .nc
    thật để xuất (chưa tải Copernicus / thiếu thư viện xarray) — không
    raise exception.
    """
    wave_frames = []
    for region in FORECAST_REGIONS.values():
        raw = get_wave_forecast_at(str(WAVE_FILE), region["lat"], region["lon"])
        if not raw:
            continue
        df = pd.DataFrame(raw).rename(columns={
            "Hs": f"{region['name']} - Hs (m)",
            "Dir": f"{region['name']} - Hướng sóng (°)",
        }).set_index("time")
        wave_frames.append(df)

    current_frames = []
    for region in FORECAST_REGIONS.values():
        raw = get_current_forecast_at(str(CURRENT_FILE), region["lat"], region["lon"])
        if not raw:
            continue
        df = pd.DataFrame(raw).rename(columns={
            "Speed": f"{region['name']} - Vận tốc (m/s)",
            "Dir": f"{region['name']} - Hướng dòng chảy (°)",
        }).set_index("time")
        current_frames.append(df)

    if not wave_frames and not current_frames:
        logger.warning("Không có dữ liệu sóng/dòng chảy .nc để xuất Excel.")
        return None

    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            if wave_frames:
                wave_df = pd.concat(wave_frames, axis=1).sort_index()
                wave_df.index.name = "Thời gian"
                wave_df.reset_index().to_excel(writer, sheet_name="Sóng (Copernicus)", index=False)
            if current_frames:
                current_df = pd.concat(current_frames, axis=1).sort_index()
                current_df.index.name = "Thời gian"
                current_df.reset_index().to_excel(writer, sheet_name="Dòng chảy (Copernicus)", index=False)
    except Exception as exc:
        logger.error("Xuất Excel sóng/dòng chảy thất bại: %s", exc)
        return None

    return output_path
