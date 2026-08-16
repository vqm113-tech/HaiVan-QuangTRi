"""
=========================================================
models/prediction.py
HaiVan Forecast System
Harmonic Tide Prediction Engine
=========================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# ==========================================================
# RESULT
# ==========================================================

@dataclass(slots=True)
class PredictionResult:

    dataframe: pd.DataFrame

    highest: float

    lowest: float

    mean_level: float


# ==========================================================
# PREDICTOR
# ==========================================================

class TidePredictor:

    """
    Harmonic Tide Prediction
    """

    def __init__(

        self,

        constituents,

        nodal

    ):

        self.constituents = constituents

        self.nodal = nodal

    # ------------------------------------------------------

    def predict(

        self,

        start_time: datetime,

        forecast_hours: int = 240,

        interval_minutes: int = 60

    ):

        dt = interval_minutes / 60

        t = np.arange(

            0,

            forecast_hours,

            dt

        )

        water = np.zeros(

            len(t),

            dtype=float

        )

        for c in self.constituents:

            corr = self.nodal[c.name]

            omega = np.deg2rad(

                c.speed

            )

            theta = (

                omega * t +

                np.deg2rad(

                    corr.V +

                    corr.u

                )

            )

            water += (

                corr.f *

                c.amplitude *

                np.cos(

                    theta -

                    np.deg2rad(

                        c.phase

                    )

                )

            )

        time = [

            start_time +

            timedelta(

                hours=float(i)

            )

            for i in t

        ]

        df = pd.DataFrame(

            {

                "Datetime": time,

                "WaterLevel": water

            }

        )

        return PredictionResult(

            dataframe=df,

            highest=float(

                water.max()

            ),

            lowest=float(

                water.min()

            ),

            mean_level=float(

                water.mean()

            )

        )

    # ------------------------------------------------------

    def daily_extrema(

        self,

        prediction: PredictionResult

    ):

        df = prediction.dataframe.copy()

        df["Date"] = df["Datetime"].dt.date

        result = []

        for day, g in df.groupby("Date"):

            idx_max = g["WaterLevel"].idxmax()

            idx_min = g["WaterLevel"].idxmin()

            result.append(

                {

                    "Date": day,

                    "HighTime":

                        df.loc[idx_max, "Datetime"],

                    "HighLevel":

                        df.loc[idx_max, "WaterLevel"],

                    "LowTime":

                        df.loc[idx_min, "Datetime"],

                    "LowLevel":

                        df.loc[idx_min, "WaterLevel"]

                }

            )

        return pd.DataFrame(result)

    # ------------------------------------------------------

    def export_csv(

        self,

        prediction,

        filename="prediction.csv"

    ):

        prediction.dataframe.to_csv(

            filename,

            index=False,

            encoding="utf-8-sig"

        )

    # ------------------------------------------------------

    def export_excel(

        self,

        prediction,

        filename="prediction.xlsx"

    ):

        prediction.dataframe.to_excel(

            filename,

            index=False

        )