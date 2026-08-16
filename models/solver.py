"""
=========================================================
models/solver.py
HaiVan Forecast System
Robust Harmonic Least Squares Solver
=========================================================
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from scipy.optimize import least_squares


# =========================================================
# RESULT
# =========================================================

@dataclass(slots=True)
class SolverResult:

    coefficients: np.ndarray

    residual: np.ndarray

    rmse: float

    mae: float

    bias: float

    r2: float

    method: str


# =========================================================
# SOLVER
# =========================================================

class HarmonicSolver:

    """
    Robust Least Squares Solver
    """

    def __init__(

        self,

        loss="soft_l1",

        f_scale=1.0

    ):

        self.loss = loss

        self.f_scale = f_scale

    # =====================================================

    def _residual(

        self,

        x,

        A,

        y

    ):

        return A @ x - y

    # =====================================================

    def solve(

        self,

        A,

        y

    ):

        x0 = np.zeros(

            A.shape[1]

        )

        result = least_squares(

            self._residual,

            x0,

            args=(A, y),

            loss=self.loss,

            f_scale=self.f_scale,

            verbose=0

        )

        coef = result.x

        pred = A @ coef

        residual = y - pred

        rmse = np.sqrt(

            np.mean(

                residual**2

            )

        )

        mae = np.mean(

            np.abs(

                residual

            )

        )

        bias = np.mean(

            residual

        )

        ssr = np.sum(

            residual**2

        )

        sst = np.sum(

            (y-y.mean())**2

        )

        r2 = 1-ssr/sst

        return SolverResult(

            coefficients=coef,

            residual=residual,

            rmse=rmse,

            mae=mae,

            bias=bias,

            r2=r2,

            method=self.loss

        )

    # =====================================================

    def ordinary(

        self,

        A,

        y

    ):

        coef, *_ = np.linalg.lstsq(

            A,

            y,

            rcond=None

        )

        pred = A @ coef

        residual = y-pred

        return SolverResult(

            coefficients=coef,

            residual=residual,

            rmse=np.sqrt(

                np.mean(

                    residual**2

                )

            ),

            mae=np.mean(

                np.abs(

                    residual

                )

            ),

            bias=np.mean(

                residual

            ),

            r2=1-

            np.sum(

                residual**2

            )/

            np.sum(

                (y-y.mean())**2

            ),

            method="OLS"

        )

    # =====================================================

    def huber(

        self,

        A,

        y

    ):

        self.loss="huber"

        return self.solve(

            A,

            y

        )

    # =====================================================

    def soft_l1(

        self,

        A,

        y

    ):

        self.loss="soft_l1"

        return self.solve(

            A,

            y

        )

    # =====================================================

    def cauchy(

        self,

        A,

        y

    ):

        self.loss="cauchy"

        return self.solve(

            A,

            y

        )

    # =====================================================

    def arctan(

        self,

        A,

        y

    ):

        self.loss="arctan"

        return self.solve(

            A,

            y

        )


# =========================================================
# COEFFICIENT PARSER
# =========================================================

def coefficient_to_constituent(

    coef,

    constituents

):

    k = 0

    for c in constituents:

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

    return constituents