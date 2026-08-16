# ==========================================
# core/nc_merge.py
# Gộp dữ liệu .nc MỚI vừa tải về với dữ liệu .nc ĐANG CÓ SẴN (nếu có), theo
# trục thời gian "time" -- để mỗi lần tải KHÔNG GHI ĐÈ mất lịch sử cũ, mà
# nối tiếp thành 1 chuỗi thời gian liên tục. Dùng chung cho cả sóng
# (core/wave_download.py) và dòng chảy (core/current_download.py).
# ==========================================

import logging

logger = logging.getLogger(__name__)


def merge_and_trim_netcdf(
    existing_path,
    new_path,
    final_path,
    retention_days=30,
    time_dim="time",
):
    """
    Gộp file .nc `new_path` (vừa tải) vào file .nc `existing_path` (đang có
    sẵn -- có thể CHƯA TỒN TẠI ở lần tải đầu tiên), theo trục thời gian, rồi
    lưu kết quả vào `final_path`.

    - Nếu 2 file trùng mốc thời gian nào, ưu tiên giá trị từ file MỚI tải
      (`new_path`), vì đó là dự báo cập nhật hơn.
    - Sắp xếp lại toàn bộ theo thời gian tăng dần.
    - Cắt bỏ các mốc thời gian cũ hơn `retention_days` ngày so với thời
      điểm hiện tại, tránh file phình to vô hạn qua nhiều lần tải.

    Trả về True nếu gộp + ghi file thành công. Trả về False nếu có lỗi --
    trong trường hợp lỗi, KHÔNG động gì tới `final_path` (giữ nguyên dữ
    liệu cũ đang có, tránh mất dữ liệu vì một lần gộp lỗi).
    """

    import numpy as np
    import xarray as xr

    try:
        new_ds = xr.load_dataset(new_path)
    except Exception as exc:
        logger.error("Không đọc được file .nc vừa tải (%s): %s", new_path, exc)
        return False

    old_ds = None
    if existing_path.exists():
        try:
            old_ds = xr.load_dataset(existing_path)
        except Exception as exc:
            logger.warning(
                "File .nc cũ (%s) bị lỗi/không đọc được, bỏ qua, chỉ dùng "
                "dữ liệu vừa tải: %s",
                existing_path,
                exc,
            )
            old_ds = None

    try:
        if old_ds is not None and time_dim in old_ds.dims:
            # old_ds nối TRƯỚC, new_ds nối SAU -> khi khử trùng mốc thời
            # gian bên dưới, occurrence CUỐI (từ new_ds) sẽ được giữ lại.
            combined = xr.concat([old_ds, new_ds], dim=time_dim)

            times = combined[time_dim].values
            # Giữ occurrence CUỐI cho mỗi mốc thời gian trùng nhau: đảo
            # ngược mảng, lấy occurrence ĐẦU (= cuối trong mảng gốc), rồi
            # quy đổi lại chỉ số, sắp xếp tăng dần.
            _, idx_rev = np.unique(times[::-1], return_index=True)
            idx = len(times) - 1 - idx_rev
            idx = np.sort(idx)
            combined = combined.isel({time_dim: idx})
        else:
            combined = new_ds

        combined = combined.sortby(time_dim)

        # Dùng datetime chuẩn (không phụ thuộc API pandas hay đổi giữa các
        # phiên bản) để tính mốc cắt dữ liệu cũ.
        from datetime import datetime, timedelta, timezone

        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=retention_days)
        cutoff = np.datetime64(cutoff_dt.replace(tzinfo=None))
        combined = combined.sel({time_dim: slice(cutoff, None)})

        # Ghi ra file tạm trước, chỉ thay thế final_path nếu ghi thành
        # công hoàn toàn -- tránh để lại file .nc hỏng/dở dang nếu quá
        # trình ghi bị gián đoạn giữa chừng (mất điện, đóng app đột ngột).
        tmp_final = final_path.with_suffix(final_path.suffix + ".tmp")
        combined.to_netcdf(str(tmp_final))
        combined.close()

        tmp_final.replace(final_path)

        logger.info(
            "Đã gộp dữ liệu -> %s (%d mốc thời gian, giữ %d ngày gần nhất)",
            final_path,
            combined.sizes.get(time_dim, 0),
            retention_days,
        )
        return True

    except Exception as exc:
        logger.error("Gộp dữ liệu .nc thất bại: %s", exc)
        return False

    finally:
        new_ds.close()
        if old_ds is not None:
            old_ds.close()
