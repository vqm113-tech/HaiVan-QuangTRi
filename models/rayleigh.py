# ==========================================================
# models/rayleigh.py
# HaiVan Forecast System 6.0
# Rayleigh Resolution Criterion
# NOAA / Foreman Method
# ==========================================================

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import numpy as np


# ==========================================================
# RESULT
# ==========================================================

@dataclass(slots=True)
class RayleighResult:

    constituent1: str

    constituent2: str

    delta_speed: float

    rayleigh_number: float

    resolvable: bool


# ==========================================================
# CRITERION
# ==========================================================

class RayleighCriterion:

    """
    Rayleigh Criterion

    T = observation length (hour)

    Δω × T > R

    NOAA:
        R ≈ 1.0

    """

    def __init__(

        self,

        observation_hours: float,

        threshold: float = 1.0

    ):

        self.T = observation_hours

        self.threshold = threshold


    # ------------------------------------------------------

    def rayleigh_number(

        self,

        speed1,

        speed2

    ):

        dw = abs(speed1-speed2)

        return dw*self.T/360.0


    # ------------------------------------------------------

    def compare(

        self,

        c1,

        c2

    ):

        rn = self.rayleigh_number(

            c1.speed,

            c2.speed

        )

        return RayleighResult(

            constituent1=c1.name,

            constituent2=c2.name,

            delta_speed=abs(

                c1.speed-c2.speed

            ),

            rayleigh_number=rn,

            resolvable=rn>=self.threshold

        )


    # ------------------------------------------------------

    def analyse(

        self,

        constituents: Iterable

    ):

        result=[]

        for c1,c2 in combinations(

            constituents,

            2

        ):

            result.append(

                self.compare(

                    c1,

                    c2

                )

            )

        return result


# ==========================================================
# REMOVE BAD CONSTITUENTS
# ==========================================================

class ConstituentSelector:

    """
    Remove unresolved constituents
    """

    def __init__(

        self,

        observation_hours

    ):

        self.rc = RayleighCriterion(

            observation_hours

        )


    def select(

        self,

        constituents

    ):

        bad=set()

        analysis=self.rc.analyse(

            constituents

        )

        for r in analysis:

            if not r.resolvable:

                bad.add(

                    r.constituent2

                )

        keep=[]

        for c in constituents:

            if c.name not in bad:

                keep.append(c)

        return keep


# ==========================================================
# REPORT
# ==========================================================

def print_report(result):

    print(

        "-"*70

    )

    print(

        "RAYLEIGH REPORT"

    )

    print(

        "-"*70

    )

    for r in result:

        print(

            f"{r.constituent1:5s}"

            f"{r.constituent2:5s}"

            f"{r.rayleigh_number:8.3f}"

            f"{r.resolvable}"

        )

    print(

        "-"*70
    )