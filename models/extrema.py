"""
=========================================================
models/extrema.py
HaiVan Forecast System 6.0
Professional Tide Extrema Detection
=========================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from scipy.signal import find_peaks


# ==========================================================
# DATACLASS
# ==========================================================

@dataclass(slots=True)
class DailyExtrema:

    date: date

    high1_time: pd.Timestamp | None = None
    high1_level: float = np.nan

    high2_time: pd.Timestamp | None = None
    high2_level: float = np.nan

    low1_time: pd.Timestamp | None = None
    low1_level: float = np.nan

    low2_time: pd.Timestamp | None = None
    low2_level: float = np.nan


# ==========================================================
# DETECTOR
# ==========================================================

class TideExtremaDetector:

    def __init__(
        self,
        min_distance_hours: float = 4.0,
        prominence: float = 0.03,
        interval_minutes: int = 60
    ):

        self.distance = max(
            1,
            int(min_distance_hours * 60 / interval_minutes)
        )

        self.prominence = prominence

    # ------------------------------------------------------

    def _find_highs(self, level):

        idx, _ = find_peaks(
            level,
            distance=self.distance,
            prominence=self.prominence
        )

        return idx

    # ------------------------------------------------------

    def _find_lows(self, level):

        idx, _ = find_peaks(
            -level,
            distance=self.distance,
            prominence=self.prominence
        )

        return idx

    # ------------------------------------------------------

    def analyse_day(self, df_day):

        level = df_day["WaterLevel"].values

        highs = self._find_highs(level)

        lows = self._find_lows(level)

        result = DailyExtrema(
            date=df_day["Datetime"].iloc[0].date()
        )

        # -------------------- HIGH -------------------------

        if len(highs):

            h = df_day.iloc[highs]

            h = h.sort_values(
                "WaterLevel",
                ascending=False
            )

            if len(h) >= 1:

                result.high1_time = h.iloc[0]["Datetime"]
                result.high1_level = float(
                    h.iloc[0]["WaterLevel"]
                )

            if len(h) >= 2:

                result.high2_time = h.iloc[1]["Datetime"]
                result.high2_level = float(
                    h.iloc[1]["WaterLevel"]
                )

        # -------------------- LOW --------------------------

        if len(lows):

            l = df_day.iloc[lows]

            l = l.sort_values(
                "WaterLevel"
            )

            if len(l) >= 1:

                result.low1_time = l.iloc[0]["Datetime"]
                result.low1_level = float(
                    l.iloc[0]["WaterLevel"]
                )

            if len(l) >= 2:

                result.low2_time = l.iloc[1]["Datetime"]
                result.low2_level = float(
                    l.iloc[1]["WaterLevel"]
                )

        return result

    # ------------------------------------------------------

    def analyse(self, prediction_df):

        prediction_df = prediction_df.copy()

        prediction_df["Date"] = (
            prediction_df["Datetime"].dt.date
        )

        rows = []

        for _, g in prediction_df.groupby("Date"):

            rows.append(
                self.analyse_day(g)
            )

        return pd.DataFrame([
            vars(r)
            for r in rows
        ])