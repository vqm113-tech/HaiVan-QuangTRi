# ==========================================================
# core/interpolation.py
# Hai Van Forecast System 6.0
# Professional Marine Interpolation Engine
# ==========================================================

from __future__ import annotations

from dataclasses import dataclass
import logging

import numpy as np
import pandas as pd

from scipy.interpolate import (
    interp1d,
    CubicSpline,
    PchipInterpolator,
    Akima1DInterpolator,
)

from scipy.signal import savgol_filter

logger = logging.getLogger(__name__)


# ==========================================================
# RESULT
# ==========================================================

@dataclass
class InterpolationResult:

    method: str

    interpolated_points: int

    rmse: float = np.nan

    mae: float = np.nan

    bias: float = np.nan


# ==========================================================
# ENGINE
# ==========================================================

class InterpolationEngine:

    def __init__(self):

        self.max_linear = 3

        self.max_pchip = 12

        self.max_spline = 48

    # ======================================================

    def linear(self, s: pd.Series):

        return s.interpolate(
            method="linear",
            limit_direction="both"
        )

    # ======================================================

    def pchip(self, s):

        x = np.arange(len(s))

        mask = s.notna()

        f = PchipInterpolator(
            x[mask],
            s[mask]
        )

        y = s.copy()

        y[:] = f(x)

        return y

    # ======================================================

    def cubic_spline(self, s):

        x = np.arange(len(s))

        mask = s.notna()

        f = CubicSpline(
            x[mask],
            s[mask]
        )

        y = s.copy()

        y[:] = f(x)

        return y

    # ======================================================

    def akima(self, s):

        x = np.arange(len(s))

        mask = s.notna()

        f = Akima1DInterpolator(
            x[mask],
            s[mask]
        )

        y = s.copy()

        y[:] = f(x)

        return y

    # ======================================================

    def smooth(self, s):

        if len(s) < 9:

            return s

        return pd.Series(

            savgol_filter(

                s,

                9,

                2

            ),

            index=s.index

        )

    # ======================================================

    def longest_gap(self, s):

        gap = s.isna()

        g = gap.ne(gap.shift()).cumsum()

        longest = 0

        for _, idx in gap.groupby(g).groups.items():

            if gap.loc[idx].iloc[0]:

                longest = max(

                    longest,

                    len(idx)

                )

        return longest

    # ======================================================

    def choose(self, s):

        gap = self.longest_gap(s)

        if gap <= self.max_linear:

            return "linear"

        if gap <= self.max_pchip:

            return "pchip"

        if gap <= self.max_spline:

            return "cubic"

        return "akima"

    # ======================================================

    def interpolate_series(
        self,
        s: pd.Series
    ):

        before = s.isna().sum()

        method = self.choose(s)

        if method == "linear":

            y = self.linear(s)

        elif method == "pchip":

            y = self.pchip(s)

        elif method == "cubic":

            y = self.cubic_spline(s)

        else:

            y = self.akima(s)

        y = self.smooth(y)

        result = InterpolationResult(

            method=method,

            interpolated_points=before

        )

        return y, result

    # ======================================================

    def interpolate_dataframe(
        self,
        df,
        value_column
    ):

        df = df.copy()

        y, report = self.interpolate_series(

            df[value_column]

        )

        df[value_column] = y

        logger.info(

            f"Interpolation : {report.method}"

        )

        return df, report