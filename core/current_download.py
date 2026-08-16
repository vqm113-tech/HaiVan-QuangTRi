# ==========================================
# core/current_download.py
# Tải dữ liệu dòng chảy (uo, vo) từ Copernicus Marine.
#
# LƯU Ý: bản gốc của file này KHÔNG thực sự tải dữ liệu gì cả — hàm
# `download_current_data` chỉ là alias trỏ tới `process_downloaded_current_data`,
# một hàm rỗng (`return data` với data=None mặc định), kèm ghi chú "Gán tên
# alias để bulletin/area_data.py import không bị lỗi". Ngoài ra còn có class
# `MarineDataProcessor` gọi `self.qc.execute_pipeline(...)` — phương thức
# này không tồn tại trong `core/qc.py` (chỉ có `run_pipeline`), và tham chiếu
# tới file mẫu "gfs_quangtri_latest.nc" không có thật trong dự án. Đã xác
# nhận (grep toàn repo) không có file nào khác import các hàm/class đó, nên
# đã thay bằng hàm tải dữ liệu thật, đối xứng với core/wave_download.py.
# ==========================================

import logging
import time
from datetime import datetime, timedelta, timezone

from config import CURRENT_DATASET, CURRENT_DIR, CURRENT_FILE

logger = logging.getLogger(__name__)

# Vùng biển bao phủ đủ 5 vùng dự báo chính thức — giống hệt BBOX trong
# core/wave_download.py để 2 dataset khớp phạm vi nhau.
BBOX = dict(
    minimum_longitude=106.4,
    maximum_longitude=109.2,
    minimum_latitude=16.6,
    maximum_latitude=18.0,
)


def _copernicus_credentials():
    """Đọc tài khoản Copernicus Marine từ biến môi trường — xem giải thích
    chi tiết trong core/wave_download.py::_copernicus_credentials()."""
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


def download_current_data(forecast_days=10, force=False, max_age_hours=6, retention_days=30):
    """
    Tải dữ liệu dòng chảy (uo, vo) cho `forecast_days` ngày tới từ Copernicus
    Marine, vùng biển Quảng Trị.

    Dữ liệu mới tải về được GỘP NỐI TIẾP với dữ liệu cũ đang có (theo trục
    thời gian, ưu tiên giá trị mới nếu trùng mốc), thay vì ghi đè mất lịch
    sử -- xem core/nc_merge.py. `retention_days` (mặc định 30 ngày) giới
    hạn chỉ giữ lại dữ liệu trong khoảng thời gian gần đây, tránh file .nc
    phình to vô hạn qua nhiều lần tải.

    Trả về đường dẫn file .nc nếu tải thành công, hoặc None nếu thất bại
    (mất mạng, thiếu thư viện, chưa đăng nhập Copernicus...) — hàm này
    KHÔNG raise exception để không làm gãy luồng chính của app.

    force=False (mặc định): bỏ qua tải nếu file hiện có còn mới hơn
    `max_age_hours` giờ, tránh gọi API Copernicus không cần thiết mỗi lần
    mở app.
    """
    if not force and _is_fresh(CURRENT_FILE, max_age_hours):
        logger.info("Bỏ qua tải dòng chảy: %s còn mới (< %sh)", CURRENT_FILE, max_age_hours)
        return CURRENT_FILE

    try:
        from copernicusmarine import subset
    except ImportError:
        logger.warning("Chưa cài đặt thư viện copernicusmarine (pip install copernicusmarine).")
        return None

    username, password = _copernicus_credentials()

    tmp_filename = "current_download_tmp.nc"
    tmp_path = CURRENT_DIR / tmp_filename

    kwargs = dict(
        dataset_id=CURRENT_DATASET,
        variables=["uo", "vo"],
        **BBOX,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(days=forecast_days),
        output_directory=str(CURRENT_DIR),
        output_filename=tmp_filename,
    )
    if username and password:
        kwargs["username"] = username
        kwargs["password"] = password

    try:
        subset(**kwargs)
    except Exception as exc:
        logger.error("Tải dữ liệu dòng chảy Copernicus thất bại: %s", exc)
        return None

    from core.nc_merge import merge_and_trim_netcdf

    try:
        merged_ok = merge_and_trim_netcdf(
            existing_path=CURRENT_FILE,
            new_path=tmp_path,
            final_path=CURRENT_FILE,
            retention_days=retention_days,
        )
    except Exception as exc:
        logger.error("Gộp dữ liệu dòng chảy thất bại: %s", exc)
        merged_ok = False
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    if merged_ok:
        logger.info("Đã tải + gộp dữ liệu dòng chảy Copernicus -> %s", CURRENT_FILE)
        return CURRENT_FILE

    logger.error("Gộp dữ liệu dòng chảy thất bại, giữ nguyên file cũ (nếu có).")
    return CURRENT_FILE if CURRENT_FILE.exists() else None
