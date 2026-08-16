"""
=========================================================
models/design_matrix.py
HaiVan Forecast System
=========================================================
"""

from __future__ import annotations

import numpy as np

from .nodal import compute_all


class DesignMatrix:

    """
    Harmonic Design Matrix

    y = AX

    """

    def __init__(

        self,

        constituents

    ):

        self.constituents = constituents

    # ---------------------------------------------------

    def build(

        self,

        time_hours,

        start_datetime

    ):

        nodal = compute_all(

            self.constituents,

            start_datetime

        )

        n = len(time_hours)

        m = len(self.constituents)

        A = np.zeros(

            (

                n,

                2 * m

            ),

            dtype=float

        )

        col = 0

        for c in self.constituents:

            corr = nodal[c.name]

            omega = np.deg2rad(

                c.speed

            )

            theta = (

                omega * time_hours

                + np.deg2rad(

                    corr.V +

                    corr.u

                )

            )

            A[:, col] = (

                corr.f *

                np.cos(theta)

            )

            A[:, col + 1] = (

                corr.f *

                np.sin(theta)

            )

            col += 2

        return A