"""
============================================================
models/nodal.py

Nodal Corrections
HaiVan Forecast System

Author : HaiVan Project
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from .astronomy import compute_astronomy


# ==========================================================
# RESULT
# ==========================================================

@dataclass(slots=True)
class NodalCorrection:

    constituent: str

    f: float

    u: float

    V: float


# ==========================================================
# EQUILIBRIUM ARGUMENT
# ==========================================================

def equilibrium_argument(
    speed: float,
    hour: float
) -> float:

    return np.mod(
        speed * hour,
        360.0
    )


# ==========================================================
# FACTOR
# ==========================================================

def nodal_factor(
    constituent: str,
    node: float
) -> float:

    N = np.deg2rad(node)

    match constituent:

        case "M2":
            return 1.000 - 0.03731*np.cos(N)

        case "S2":
            return 1.000

        case "N2":
            return 1.000 - 0.03731*np.cos(N)

        case "K2":
            return 1.024 + 0.286*np.cos(N)

        case "K1":
            return 1.006 + 0.115*np.cos(N)

        case "O1":
            return 1.009 + 0.187*np.cos(N)

        case "P1":
            return 1.000

        case "Q1":
            return 1.009 + 0.188*np.cos(N)

        case _:
            return 1.0


# ==========================================================
# PHASE
# ==========================================================

def phase_correction(
    constituent: str,
    node: float
) -> float:

    N = np.deg2rad(node)

    match constituent:

        case "M2":
            return np.rad2deg(
                -2.1*np.sin(N)
            )

        case "N2":
            return np.rad2deg(
                -2.1*np.sin(N)
            )

        case "K1":
            return np.rad2deg(
                8.9*np.sin(N)
            )

        case "O1":
            return np.rad2deg(
                10.8*np.sin(N)
            )

        case "Q1":
            return np.rad2deg(
                10.8*np.sin(N)
            )

        case "K2":
            return np.rad2deg(
                17.7*np.sin(N)
            )

        case _:
            return 0.0


# ==========================================================
# COMPLETE
# ==========================================================

def compute_nodal(
    constituent: str,
    speed: float,
    dt: datetime
) -> NodalCorrection:

    astro = compute_astronomy(dt)

    hour = (
        dt.hour +
        dt.minute/60 +
        dt.second/3600
    )

    f = nodal_factor(
        constituent,
        astro.node
    )

    u = phase_correction(
        constituent,
        astro.node
    )

    V = equilibrium_argument(
        speed,
        hour
    )

    return NodalCorrection(

        constituent=constituent,

        f=f,

        u=u,

        V=V

    )


# ==========================================================
# BATCH
# ==========================================================

def compute_all(
    constituents,
    dt: datetime
):

    result = {}

    for c in constituents:

        result[c.name] = compute_nodal(

            constituent=c.name,

            speed=c.speed,

            dt=dt

        )

    return result