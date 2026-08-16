# ==========================================
# bulletin/tide_model.py
# Dự báo thủy triều bằng bộ mô hình điều hòa chuẩn (models/)
# Thay thế bản fit 6 hằng số thô sơ trước đây trong area_data.py:
#   - Có hiệu chỉnh nodal (models/nodal.py) cho từng hằng số triều
#   - Tự động chọn hằng số triều theo tiêu chuẩn Rayleigh dựa trên độ dài
#     chuỗi số liệu quan trắc thực tế (models/rayleigh.py)
#   - Dùng Least-Squares solver riêng (models/solver.py)
# ==========================================

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from models.constituents import STANDARD_CONSTITUENTS
from models.design_matrix import DesignMatrix
from models.solver import HarmonicSolver, coefficient_to_constituent
from models.nodal import compute_all
from models.prediction import TidePredictor
from models.rayleigh import ConstituentSelector

# 8 hằng số triều chính — đây cũng chính là các hằng số có công thức hiệu
# chỉnh nodal (nodal_factor/phase_correction) tường minh trong models/nodal.py.
# Các hằng số phụ khác trong STANDARD_CONSTITUENTS chỉ nhận hệ số mặc định
# f=1.0/u=0.0 (không có hiệu chỉnh thật), nên không đưa vào để tránh cộng
# tuyến tính thừa mà không có giá trị vật lý thêm.
MAIN_CONSTITUENT_NAMES = {"M2", "S2", "N2", "K2", "K1", "O1", "P1", "Q1"}

MIN_OBS_HOURS = 48.0  # tối thiểu ~2 ngày số liệu mới đủ để fit

# Số ngày quan trắc gần nhất dùng để hiệu chỉnh mực nước trung bình. Mực
# nước biển thực tế trôi theo mùa/gió mùa mà các hằng số triều ngắn hạn
# (bán nhật/nhật triều) không nắm được, nên KHÔNG dùng trung bình của toàn
# bộ chuỗi quan trắc (có thể dài hàng năm) mà dùng độ lệch trung bình so
# với tín hiệu triều thuần túy trong giai đoạn gần nhất — tương tự cách
# dự báo viên hiệu chỉnh theo mực nước thực đo mới nhất.
RECENT_BIAS_WINDOW_DAYS = 15


def _select_constituents(observation_hours: float):
    """Lấy bản sao 8 hằng số chính, rồi tự loại hằng số không phân giải được
    theo tiêu chuẩn Rayleigh nếu chuỗi số liệu quan trắc quá ngắn."""
    base = [
        replace(c) for c in STANDARD_CONSTITUENTS
        if c.name in MAIN_CONSTITUENT_NAMES
    ]
    try:
        base = ConstituentSelector(observation_hours).select(base)
    except Exception:
        pass
    return base


def predict_tide(
    dt_series: pd.Series,
    level_series: pd.Series,
    forecast_start: datetime,
    forecast_days: int = 10,
    amplitude_scale: Optional[dict] = None,
    manual_offset_m: float = 0.0,
) -> Optional[pd.DataFrame]:
    """
    Chạy mô hình điều hòa triều chuẩn trên số liệu quan trắc và dự báo tiếp.

    dt_series, level_series : số liệu mực nước thực đo (đơn vị mét, cùng datum
        với số liệu đầu vào — chưa quy đổi hải đồ).
    forecast_start : thời điểm bắt đầu lấy kết quả dự báo (thường là 00:00
        ngày kế tiếp sau ngày quan trắc cuối cùng).
    amplitude_scale : dict {tên_hằng_số: hệ_số_nhân} tùy chọn — cho phép dự
        báo viên tăng/giảm biên độ từng hằng số triều (M2,S2,N2,K2,K1,O1,P1,Q1)
        so với kết quả fit từ số liệu, để bù cho đặc điểm địa phương mà mô
        hình thuần túy không nắm hết được (ví dụ trạm đo tại cửa sông chịu
        ảnh hưởng dòng chảy nước ngọt, không phải sóng triều thuần túy).
        Hằng số không có trong dict giữ nguyên hệ số 1.0 (không đổi).
    manual_offset_m : số mét cộng thêm vào toàn bộ chuỗi mực nước dự báo —
        hiệu chỉnh sai số hệ thống do dự báo viên tự đánh giá theo kinh
        nghiệm địa phương.

    Trả về DataFrame cột [Datetime, WaterLevel] (mét) đúng `forecast_days`
    ngày, hoặc None nếu không đủ số liệu để fit mô hình (bên gọi tự xử lý
    phương án dự phòng).
    """
    dt_series = pd.to_datetime(dt_series)
    t0 = dt_series.min()

    t_obs = (dt_series - t0).dt.total_seconds().to_numpy() / 3600.0
    y_obs = pd.to_numeric(level_series, errors="coerce").to_numpy(dtype=float)

    valid = ~(np.isnan(t_obs) | np.isnan(y_obs))
    t_obs, y_obs = t_obs[valid], y_obs[valid]

    if len(y_obs) < 10 or (t_obs.max() - t_obs.min()) < MIN_OBS_HOURS:
        return None

    observation_hours = float(t_obs.max() - t_obs.min())
    constituents = _select_constituents(observation_hours)
    if not constituents:
        return None

    # models/design_matrix.py chỉ dựng các cột dao động điều hòa (cos/sin),
    # không có số hạng mực nước trung bình (mean sea level) — cộng thêm 1 cột
    # hằng số để mô hình không bị lệch (bias) so với mực nước quan trắc.
    design = DesignMatrix(constituents)
    try:
        A_harmonic = design.build(t_obs, start_datetime=t0)
    except Exception:
        return None
    A = np.column_stack([np.ones_like(t_obs), A_harmonic])

    try:
        result = HarmonicSolver().ordinary(A, y_obs)
    except Exception:
        return None

    mean_level_global = float(result.coefficients[0])
    harmonic_coefs = result.coefficients[1:]
    coefficient_to_constituent(harmonic_coefs, constituents)

    # Hệ số nhân biên độ do dự báo viên tự hiệu chỉnh (nếu có) — áp dụng SAU
    # khi fit, không ảnh hưởng tới bước ước lượng biên độ/pha từ số liệu.
    if amplitude_scale:
        for c in constituents:
            factor = amplitude_scale.get(c.name)
            if factor is not None:
                c.amplitude *= float(factor)

    # Hiệu chỉnh mực nước trung bình theo RECENT_BIAS_WINDOW_DAYS ngày quan
    # trắc gần nhất thay vì dùng trung bình toàn chuỗi (xem giải thích ở
    # RECENT_BIAS_WINDOW_DAYS phía trên).
    harmonic_only_obs = A_harmonic @ harmonic_coefs
    residual_obs = y_obs - harmonic_only_obs
    recent_hours = RECENT_BIAS_WINDOW_DAYS * 24
    recent_mask = t_obs >= (t_obs.max() - recent_hours)
    if recent_mask.any():
        mean_level = float(residual_obs[recent_mask].mean())
    else:
        mean_level = mean_level_global

    # Dự báo LIÊN TỤC từ mốc quy chiếu pha t0 (thời điểm quan trắc đầu tiên)
    # cho tới hết cửa sổ dự báo cần lấy, sau đó mới cắt lấy đoạn cần — để pha
    # triều luôn nhất quán với hiệu chỉnh nodal đã tính tại t0.
    nodal = compute_all(constituents, t0)
    predictor = TidePredictor(constituents, nodal)

    total_hours = (forecast_start - t0).total_seconds() / 3600.0 + forecast_days * 24
    if total_hours <= 0:
        return None

    prediction = predictor.predict(
        start_time=t0,
        forecast_hours=int(np.ceil(total_hours)) + 1,
        interval_minutes=60,
    )

    df = prediction.dataframe.copy()
    df["WaterLevel"] = df["WaterLevel"] + mean_level + manual_offset_m

    forecast_end = forecast_start + timedelta(days=forecast_days)
    df = df[(df["Datetime"] >= forecast_start) & (df["Datetime"] < forecast_end)]

    if df.empty:
        return None

    return df.reset_index(drop=True)
