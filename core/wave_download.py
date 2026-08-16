import logging
import time
from datetime import datetime, timedelta, timezone

from config import WAVE_DATASET, WAVE_DIR, WAVE_FILE

logger = logging.getLogger(__name__)

# Vùng biển bao phủ đủ 5 vùng dự báo chính thức (station_config.FORECAST_REGIONS)
# — đặc biệt "ngoài khơi phía Nam" ở kinh độ ~109.01°, xa hơn nhiều so với
# phạm vi ven bờ trước đây (106.5-107.5°). Có chừa biên an toàn ~0.1-0.2 độ.
BBOX = dict(
    minimum_longitude=106.4,
    maximum_longitude=109.2,
    minimum_latitude=16.6,
    maximum_latitude=18.0,
)


def _copernicus_credentials():
    """
    Đọc tài khoản Copernicus Marine từ BIẾN MÔI TRƯỜNG
    (COPERNICUSMARINE_SERVICE_USERNAME / _PASSWORD), KHÔNG hard-code trong
    code. Nếu không đặt biến môi trường, trả về (None, None) — khi đó thư
    viện copernicusmarine tự dùng phiên đăng nhập đã lưu trước đó bằng lệnh
    `copernicusmarine login` (cách bản gốc vẫn đang dùng).
    """
    import os
    return (
        os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME"),
        os.environ.get("COPERNICUSMARINE_SERVICE_PASSWORD"),
    )


def _is_fresh(path, max_age_hours):
    if not path.exists():
        return False
    age_hours = (time.time() - path.stat().st_mtime) / 3600.0
    return age_hours < max_age_hours


def download_wave_data(forecast_days=10, force=False, max_age_hours=6, retention_days=30):
    """
    Tải dữ liệu sóng (VHM0, VMDR) cho `forecast_days` ngày tới từ Copernicus
    Marine, vùng biển Quảng Trị.

    Dữ liệu mới tải về được GỘP NỐI TIẾP với dữ liệu cũ đang có (theo trục
    thời gian, ưu tiên giá trị mới nếu trùng mốc), thay vì ghi đè mất lịch
    sử -- xem core/nc_merge.py. `retention_days` (mặc định 30 ngày) giới
    hạn chỉ giữ lại dữ liệu trong khoảng thời gian gần đây, tránh file .nc
    phình to vô hạn qua nhiều lần tải.

    Trả về đường dẫn file .nc nếu tải thành công, hoặc None nếu thất bại
    (mất mạng, thiếu thư viện, chưa đăng nhập Copernicus...) — hàm này
    KHÔNG raise exception để không làm gãy luồng chính của app; bên gọi tự
    quyết định dùng file .nc cũ đang có (nếu có) hay báo người dùng.

    force=False (mặc định): bỏ qua tải nếu file hiện có còn mới hơn
    `max_age_hours` giờ, tránh gọi API Copernicus không cần thiết mỗi lần
    mở app.
    """
    if not force and _is_fresh(WAVE_FILE, max_age_hours):
        logger.info("Bỏ qua tải sóng: %s còn mới (< %sh)", WAVE_FILE, max_age_hours)
        return WAVE_FILE

    try:
        from copernicusmarine import subset
    except ImportError:
        logger.warning("Chưa cài đặt thư viện copernicusmarine (pip install copernicusmarine).")
        return None

    username, password = _copernicus_credentials()

    tmp_filename = "wave_download_tmp.nc"
    tmp_path = WAVE_DIR / tmp_filename

    kwargs = dict(
        dataset_id=WAVE_DATASET,
        variables=["VHM0", "VMDR"],
        **BBOX,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(days=forecast_days),
        output_directory=str(WAVE_DIR),
        output_filename=tmp_filename,
    )
    if username and password:
        kwargs["username"] = username
        kwargs["password"] = password

    try:
        subset(**kwargs)
    except Exception as exc:
        logger.error("Tải dữ liệu sóng Copernicus thất bại: %s", exc)
        return None

    from core.nc_merge import merge_and_trim_netcdf

    try:
        merged_ok = merge_and_trim_netcdf(
            existing_path=WAVE_FILE,
            new_path=tmp_path,
            final_path=WAVE_FILE,
            retention_days=retention_days,
        )
    except Exception as exc:
        logger.error("Gộp dữ liệu sóng thất bại: %s", exc)
        merged_ok = False
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    if merged_ok:
        logger.info("Đã tải + gộp dữ liệu sóng Copernicus -> %s", WAVE_FILE)
        return WAVE_FILE

    logger.error("Gộp dữ liệu sóng thất bại, giữ nguyên file cũ (nếu có).")
    return WAVE_FILE if WAVE_FILE.exists() else None
