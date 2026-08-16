# ==========================================================
# models/constituents.py
# Global Harmonic Constituents Library
# HaiVan Forecast System 6.0
# ==========================================================

from dataclasses import dataclass


@dataclass(slots=True)
class Constituent:

    name: str

    speed: float          # degree/hour

    doodson: str

    species: int

    amplitude: float = 0.0

    phase: float = 0.0


# ==========================================================
# NOAA / IHO STANDARD
# ==========================================================

STANDARD_CONSTITUENTS = [

    Constituent("M2",28.9841042,"255.555",2),

    Constituent("S2",30.0000000,"273.555",2),

    Constituent("N2",28.4397295,"245.655",2),

    Constituent("K2",30.0821373,"275.555",2),

    Constituent("L2",29.5284789,"265.455",2),

    Constituent("T2",29.9589333,"272.556",2),

    Constituent("MU2",27.9682084,"235.755",2),

    Constituent("NU2",28.5125831,"245.655",2),

    Constituent("2N2",27.8953548,"235.555",2),

    Constituent("EPS2",29.4556253,"264.655",2),

    Constituent("MNS2",29.4556253,"264.555",2),

    Constituent("M2A",28.0,"255.550",2),

    Constituent("K1",15.0410686,"165.555",1),

    Constituent("O1",13.9430356,"145.555",1),

    Constituent("P1",14.9589314,"163.555",1),

    Constituent("Q1",13.3986609,"135.655",1),

    Constituent("J1",15.5854433,"175.455",1),

    Constituent("OO1",16.1391017,"185.555",1),

    Constituent("M1",14.4966939,"155.455",1),

    Constituent("RHO1",13.4715145,"136.555",1),

    Constituent("SIGMA1",15.0,"164.555",1),

    Constituent("M3",43.4761563,"355.555",3),

    Constituent("M4",57.9682084,"455.555",4),

    Constituent("MS4",58.9841042,"465.555",4),

    Constituent("MN4",57.4238337,"445.555",4),

    Constituent("M6",86.9523126,"655.555",6),

    Constituent("M8",115.9364168,"855.555",8),

    Constituent("SA",0.0410686,"056.554",0),

    Constituent("SSA",0.0821373,"057.555",0),

]