# ==========================================================
# core/qc.py
# Hai Van Forecast System 6.0
# Marine Quality Control Module - Refactored Edition
# ==========================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class QCReport:
    total_records: int = 0
    missing_values: int = 0
    duplicated_rows: int = 0
    outlier_range: int = 0
    outlier_step: int = 0
    outlier_hampel: int = 0
    interpolated: int = 0
    quality: str = "GOOD"
    quality_score: float = 100.0
    messages: List[str] = field(default_factory=list)


class MarineQualityControl:
    """
    Marine Observation Quality Control System
    Standardized according to UNESCO/IOC Sea Level & Ocean QC guidelines.
    """

    def __init__(self):
        # Physical Range Bounds
        self.bounds = {
            "water_level": (-3.0, 6.0),    # m (Hải đồ / Hòn Dấu)
            "wave_height": (0.0, 15.0),   # m
            "wind_speed": (0.0, 60.0),     # m/s (~ Cấp 17)
            "wind_direction": (0.0, 360.0),# degree
            "current_speed": (0.0, 4.5),   # m/s
        }

        # Step limits (Maximum change per sampling step - default hourly)
        self.step_limit = {
            "water_level": 0.8,   # Max 0.8m change per hour
            "wave_height": 2.5,   # Max 2.5m change per hour
            "wind_speed": 12.0,   # Max 12 m/s change per hour
            "current_speed": 1.5, # Max 1.5 m/s change per hour
        }

    def remove_duplicates(self, df: pd.DataFrame, report: QCReport) -> pd.DataFrame:
        before = len(df)
        df = df.drop_duplicates()
        report.duplicated_rows = before - len(df)
        return df

    def range_check(self, series: pd.Series, variable: str, report: QCReport) -> pd.Series:
        if variable not in self.bounds:
            return series

        low, high = self.bounds[variable]
        mask = (series < low) | (series > high)
        report.outlier_range = int(mask.sum())
        series = series.copy()
        series.loc[mask] = np.nan
        return series

    def step_check(self, series: pd.Series, variable: str, report: QCReport) -> pd.Series:
        if variable not in self.step_limit:
            return series

        diff = series.diff().abs()
        mask = diff > self.step_limit[variable]
        report.outlier_step = int(mask.sum())
        series = series.copy()
        series.loc[mask] = np.nan
        return series

    def hampel_filter(
        self,
        series: pd.Series,
        report: QCReport,
        window: int = 5,
        sigma: float = 3.0
    ) -> pd.Series:
        """Robust Outlier Detection using Rolling Median and MAD"""
        values = series.copy()
        k = 1.4826
        
        rolling_median = values.rolling(window=2*window+1, center=True, min_periods=1).median()
        rolling_mad = k * (values - rolling_median).abs().rolling(window=2*window+1, center=True, min_periods=1).median()
        
        threshold = sigma * rolling_mad
        outlier_mask = (values - rolling_median).abs() > threshold
        
        # Avoid marking normal flat lines as outliers when MAD == 0
        outlier_mask = outlier_mask & (rolling_mad > 1e-6)
        
        report.outlier_hampel = int(outlier_mask.sum())
        values.loc[outlier_mask] = np.nan
        return values

    def auto_fix_interpolation(
        self, 
        series: pd.Series, 
        report: QCReport, 
        max_gap: int = 6
    ) -> pd.Series:
        """
        Nội suy dữ liệu chỉ khi khoảng trống khuyết thiếu <= max_gap mẫu liên tiếp.
        Không nội suy lấp lỗ hổng dài quá quy định.
        """
        s = series.copy()
        is_na = s.isna()
        
        # Nhóm các đoạn NaN liên tiếp
        blocks = (~is_na).cumsum()[is_na]
        gap_sizes = blocks.value_counts()
        
        # Tìm các index của block NaN có độ dài quá max_gap
        invalid_gaps = gap_sizes[gap_sizes > max_gap].index
        invalid_mask = blocks.isin(invalid_gaps)
        # blocks/invalid_mask chỉ có index tại các vị trí NaN (tập con của
        # index gốc) — phải reindex về đúng index đầy đủ của `s` (các vị trí
        # không NaN coi như False) thì mới dùng làm boolean indexer được,
        # nếu không pandas sẽ báo lỗi "Unalignable boolean Series".
        invalid_mask = invalid_mask.reindex(s.index, fill_value=False)
        
        before_missing = is_na.sum()
        
        # Thực hiện nội suy PCHIP hoặc Linear
        s_interpolated = s.interpolate(method="pchip", limit_direction="both")
        
        # Giữ nguyên NaN cho các khoảng khuyết quá dài
        s_interpolated[invalid_mask] = np.nan
        
        after_missing = s_interpolated.isna().sum()
        report.interpolated = int(before_missing - after_missing)
        
        return s_interpolated

    def create_flag_column(self, series_raw: pd.Series, series_clean: pd.Series, variable: str) -> pd.Series:
        """
        Gắn Flag chuẩn IOC:
        1: Good, 3: Suspect/Outlier, 4: Bad/Out of Range, 9: Missing Original
        """
        flags = pd.Series(1, index=series_raw.index)
        
        if variable in self.bounds:
            low, high = self.bounds[variable]
            flags.loc[(series_raw < low) | (series_raw > high)] = 4
            
        flags.loc[series_clean.isna() & ~series_raw.isna()] = 3
        flags.loc[series_raw.isna()] = 9
        return flags

    def classify_quality(self, report: QCReport):
        if report.total_records == 0:
            report.quality = "BAD"
            report.quality_score = 0.0
            return

        score = 100.0
        score -= (report.missing_values / report.total_records) * 30.0
        score -= (report.outlier_range / report.total_records) * 40.0
        score -= (report.outlier_step / report.total_records) * 20.0
        score -= (report.outlier_hampel / report.total_records) * 10.0

        score = max(round(score, 2), 0.0)
        report.quality_score = score

        if score >= 95:
            report.quality = "EXCELLENT"
        elif score >= 85:
            report.quality = "GOOD"
        elif score >= 70:
            report.quality = "FAIR"
        elif score >= 50:
            report.quality = "POOR"
        else:
            report.quality = "BAD"

    def run_pipeline(
        self, 
        df: pd.DataFrame, 
        value_col: str, 
        variable: str = "water_level",
        max_gap: int = 6
    ) -> Tuple[pd.DataFrame, QCReport]:
        
        report = QCReport()
        df = df.copy()
        report.total_records = len(df)
        report.missing_values = int(df[value_col].isna().sum())

        # 1. Deduplicate
        df = self.remove_duplicates(df, report)
        raw_series = df[value_col].copy()

        # 2. Check Range
        s_clean = self.range_check(raw_series, variable, report)

        # 3. Check Step Change
        s_clean = self.step_check(s_clean, variable, report)

        # 4. Hampel Outlier Filter
        s_clean = self.hampel_filter(s_clean, report)

        # 5. Smart Interpolation
        s_fixed = self.auto_fix_interpolation(s_clean, report, max_gap=max_gap)

        # 6. Quality Flagging & Scoring
        df["QC_FLAG"] = self.create_flag_column(raw_series, s_fixed, variable)
        df[value_col] = s_fixed
        
        self.classify_quality(report)

        return df, report


# ==========================================================
# HELPER LOADERS & API
# ==========================================================

def load_data(uploaded_file) -> pd.DataFrame:
    """Đọc dữ liệu an toàn cho Streamlit hoặc File Path local"""
    filename = getattr(uploaded_file, 'name', str(uploaded_file)).lower()

    if filename.endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded_file)
    elif filename.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    else:
        raise ValueError(f"Định dạng file '{filename}' không được hỗ trợ!")