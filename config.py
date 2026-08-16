from pathlib import Path

# =========================
# THƯ MỤC GỐC
# =========================
BASE_DIR = Path(__file__).parent

# =========================
# DATA
# =========================
DATA_DIR = BASE_DIR / "data"

WAVE_DIR = DATA_DIR / "wave_data"
CURRENT_DIR = DATA_DIR / "current_data"

OUTPUT_DIR = BASE_DIR / "output"

WAVE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# COPERNICUS
# =========================
WAVE_DATASET = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"

# Đổi đuôi từ _P1D-m (ngày) thành _PT1H-m (giờ)
CURRENT_DATASET = "cmems_mod_glo_phy_anfc_0.083deg_PT1H-m"

# =========================
# FILE NETCDF
# =========================
WAVE_FILE = WAVE_DIR / "wave.nc"

CURRENT_FILE = CURRENT_DIR / "current.nc"