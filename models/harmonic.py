# ==========================================================
# models/harmonic.py
# Harmonic Tide Analysis Engine
# Version : 1.0
# ==========================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy.optimize import least_squares


# ==========================================================
# CONSTITUENT
# ==========================================================

@dataclass
class Constituent:

    name: str

    speed: float

    amplitude: float = 0.0

    phase: float = 0.0


# ==========================================================
# NOAA STANDARD CONSTITUENTS
# degree/hour
# ==========================================================

STANDARD_CONSTITUENTS = [

    Constituent("M2",28.9841042),

    Constituent("S2",30.0000000),

    Constituent("N2",28.4397295),

    Constituent("K2",30.0821373),

    Constituent("K1",15.0410686),

    Constituent("O1",13.9430356),

    Constituent("P1",14.9589314),

    Constituent("Q1",13.3986609),

    Constituent("M4",57.9682084),

    Constituent("MS4",58.9841042),

    Constituent("MN4",57.4238337),

    Constituent("M6",86.9523126),

]


# ==========================================================
# ENGINE
# ==========================================================

class HarmonicAnalyzer:

    """
    Least Squares Harmonic Analysis

    NOAA Standard
    """

    def __init__(self):

        self.constituents = STANDARD_CONSTITUENTS

    # ------------------------------------------------------

    def _design_matrix(

        self,

        hours

    ):

        cols = []

        for c in self.constituents:

            omega = np.deg2rad(c.speed)

            cols.append(

                np.cos(

                    omega*hours

                )

            )

            cols.append(

                np.sin(

                    omega*hours

                )

            )

        return np.column_stack(cols)

    # ------------------------------------------------------

    def fit(

        self,

        water_level: np.ndarray,

        dt_hour: float=1.0

    ):

        n = len(water_level)

        t = np.arange(n)*dt_hour

        A = self._design_matrix(t)

        coef, *_ = np.linalg.lstsq(

            A,

            water_level,

            rcond=None

        )

        k = 0

        for c in self.constituents:

            a = coef[k]

            b = coef[k+1]

            k += 2

            c.amplitude = np.sqrt(

                a*a+b*b

            )

            c.phase = np.degrees(

                np.arctan2(

                    b,

                    a

                )

            )

        return self.constituents

    # ------------------------------------------------------

    def predict(

        self,

        hours

    ):

        y = np.zeros(

            len(hours)

        )

        for c in self.constituents:

            omega = np.deg2rad(

                c.speed

            )

            y += (

                c.amplitude *

                np.cos(

                    omega*hours-

                    np.deg2rad(c.phase)

                )

            )

        return y

    # ------------------------------------------------------

    def constituent_table(

        self

    ):

        rows=[]

        for c in self.constituents:

            rows.append(

                {

                    "Name":c.name,

                    "Amplitude":round(c.amplitude,3),

                    "Phase":round(c.phase,2),

                    "Speed":c.speed

                }

            )

        return pd.DataFrame(rows)