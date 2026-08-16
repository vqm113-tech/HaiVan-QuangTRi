# ==========================================================
# models/astronomy.py
# HaiVan Forecast System 6.0
# Astronomical Arguments for Harmonic Tide Analysis
# ==========================================================

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from datetime import datetime


# ==========================================================
# JULIAN
# ==========================================================

def julian_day(dt: datetime) -> float:

    y = dt.year
    m = dt.month

    d = (
        dt.day
        + dt.hour / 24
        + dt.minute / 1440
        + dt.second / 86400
    )

    if m <= 2:
        y -= 1
        m += 12

    a = int(y / 100)

    b = 2 - a + int(a / 4)

    jd = (
        int(365.25 * (y + 4716))
        + int(30.6001 * (m + 1))
        + d
        + b
        - 1524.5
    )

    return jd


# ==========================================================
# JULIAN CENTURY
# ==========================================================

def julian_century(jd):

    return (jd - 2451545.0) / 36525.0


# ==========================================================
# SOLAR MEAN LONGITUDE
# ==========================================================

def solar_longitude(T):

    L = (
        280.46646
        + 36000.76983 * T
        + 0.0003032 * T * T
    )

    return np.mod(L, 360)


# ==========================================================
# LUNAR MEAN LONGITUDE
# ==========================================================

def lunar_longitude(T):

    L = (
        218.3165
        + 481267.8813 * T
    )

    return np.mod(L, 360)


# ==========================================================
# LUNAR PERIGEE
# ==========================================================

def lunar_perigee(T):

    P = (
        83.3532465
        + 4069.0137287 * T
    )

    return np.mod(P, 360)


# ==========================================================
# ASCENDING NODE
# ==========================================================

def ascending_node(T):

    N = (
        125.04452
        - 1934.136261 * T
    )

    return np.mod(N, 360)


# ==========================================================
# LUNAR ELONGATION
# ==========================================================

def mean_elongation(T):

    D = (
        297.8501921
        + 445267.1114034 * T
    )

    return np.mod(D, 360)


# ==========================================================
# SUN ANOMALY
# ==========================================================

def solar_anomaly(T):

    M = (
        357.5291092
        + 35999.0502909 * T
    )

    return np.mod(M, 360)


# ==========================================================
# MOON ANOMALY
# ==========================================================

def lunar_anomaly(T):

    Mp = (
        134.9633964
        + 477198.8675055 * T
    )

    return np.mod(Mp, 360)


# ==========================================================
# NODAL FACTOR
# ==========================================================

def nodal_factor(name, N):

    N = np.deg2rad(N)

    if name == "M2":

        return 1 - 0.037*np.cos(N)

    elif name == "S2":

        return 1.0

    elif name == "N2":

        return 1 - 0.037*np.cos(N)

    elif name == "K1":

        return 1.006 + 0.115*np.cos(N)

    elif name == "O1":

        return 1.009 + 0.187*np.cos(N)

    return 1.0


# ==========================================================
# PHASE CORRECTION
# ==========================================================

def phase_correction(name, N):

    N = np.deg2rad(N)

    if name == "M2":

        return np.rad2deg(
            -2.1*np.sin(N)
        )

    elif name == "N2":

        return np.rad2deg(
            -2.1*np.sin(N)
        )

    elif name == "K1":

        return np.rad2deg(
            8.9*np.sin(N)
        )

    elif name == "O1":

        return np.rad2deg(
            10.8*np.sin(N)
        )

    return 0.0


# ==========================================================
# GREENWICH ARGUMENT
# ==========================================================

def greenwich_argument(speed, hour):

    return np.mod(

        speed * hour,

        360

    )


# ==========================================================
# DATACLASS
# ==========================================================

@dataclass
class Astronomy:

    julian: float

    century: float

    solar: float

    lunar: float

    node: float

    perigee: float

    elongation: float

    solar_anomaly: float

    lunar_anomaly: float


# ==========================================================
# MAIN
# ==========================================================

def compute_astronomy(dt: datetime):

    jd = julian_day(dt)

    T = julian_century(jd)

    return Astronomy(

        julian=jd,

        century=T,

        solar=solar_longitude(T),

        lunar=lunar_longitude(T),

        node=ascending_node(T),

        perigee=lunar_perigee(T),

        elongation=mean_elongation(T),

        solar_anomaly=solar_anomaly(T),

        lunar_anomaly=lunar_anomaly(T)

    )