# ==========================================
# core/beaufort.py
# Quy đổi tốc độ gió (m/s) sang cấp gió Bô-pho (Beaufort) — thang chuẩn quốc tế.
#
# Bảng độ cao sóng trung bình + mức độ nguy hại theo TỪNG CẤP GIÓ dưới đây
# lấy đúng từ "BẢNG CẤP GIÓ VÀ SÓNG (Việt Nam)" — Phòng QLMLT, Đài KTTV khu
# vực Trung Trung Bộ (áp dụng thống nhất cho toàn dự án: bản tin nguy hiểm
# HVNH dùng để suy ra câu "Biển động/Biển động mạnh...", các bản tin
# tháng/mùa dùng để đồng bộ cách mô tả trạng thái biển theo cùng 1 nguồn).
# ==========================================

# (tốc độ tối đa của cấp, m/s) — ngưỡng trên mỗi cấp, theo thang Beaufort chuẩn
_BEAUFORT_THRESHOLDS = [
    (0.2, 0), (1.5, 1), (3.3, 2), (5.4, 3), (7.9, 4),
    (10.7, 5), (13.8, 6), (17.1, 7), (20.7, 8), (24.4, 9),
    (28.4, 10), (32.6, 11),
]

# Độ cao sóng trung bình (m) ứng với từng cấp gió Bô-pho — cột "Độ cao sóng
# trung bình" của bảng gốc. Cấp 13-17 (siêu bão) bảng gốc không cho trị số
# cụ thể ("Sóng biển cực kỳ mạnh") nên để None.
BEAUFORT_WAVE_HEIGHT_M = {
    0: 0.0, 1: 0.1, 2: 0.2, 3: 0.6, 4: 1.0, 5: 2.0, 6: 3.0, 7: 4.0,
    8: 5.5, 9: 7.0, 10: 9.0, 11: 11.5, 12: 14.0,
    13: None, 14: None, 15: None, 16: None, 17: None,
}

# Tốc độ gió (m/s) ứng với từng cấp — (min, max) — cột "Tốc độ gió" bảng gốc.
BEAUFORT_WIND_SPEED_MS = {
    0: (0.0, 0.2), 1: (0.3, 1.5), 2: (1.6, 3.3), 3: (3.4, 5.4),
    4: (5.5, 7.9), 5: (8.0, 10.7), 6: (10.8, 13.8), 7: (13.9, 17.1),
    8: (17.2, 20.7), 9: (20.8, 24.4), 10: (24.5, 28.4), 11: (28.5, 32.6),
    12: (32.7, 36.9), 13: (37.0, 41.4), 14: (41.5, 46.1), 15: (46.2, 50.9),
    16: (51.0, 56.0), 17: (56.1, 61.2),
}

# Mức độ nguy hại (nguyên văn bảng gốc, phần liên quan tới biển) theo NHÓM
# cấp — dùng để sinh câu mô tả trạng thái biển thống nhất trong bản tin.
_SEA_STATE_BY_FORCE = [
    (3, "Biển lặng"),
    (5, "Biển hơi động"),
    (7, "Biển động"),
    (9, "Biển động rất mạnh"),
    (11, "Biển động dữ dội"),
    (17, "Biển động dữ dội, sóng biển cực kỳ mạnh"),
]

_HAZARD_TEXT_BY_FORCE = [
    (3, "Gió nhẹ, không gây nguy hại."),
    (5, "Biển hơi động. Thuyền đánh cá bị chao nghiêng, phải cuốn bớt buồm."),
    (7, "Biển động. Nguy hiểm đối với tàu, thuyền."),
    (9, "Biển động rất mạnh. Rất nguy hiểm đối với tàu, thuyền."),
    (11, "Biển động dữ dội. Làm đắm tàu biển."),
    (17, "Sóng biển cực kỳ mạnh. Đánh đắm tàu biển có trọng tải lớn."),
]


def beaufort_scale(speed_ms: float) -> int:
    """Trả về cấp gió Bô-pho (0-12) từ tốc độ gió trung bình (m/s)."""
    if speed_ms is None:
        return 0
    for max_speed, force in _BEAUFORT_THRESHOLDS:
        if speed_ms <= max_speed:
            return force
    return 12


def beaufort_text(force_avg: int, force_gust: int) -> str:
    """Câu mô tả cấp gió kiểu bản tin: 'cấp 5, có lúc cấp 6, giật cấp 7'."""
    if force_gust > force_avg + 1:
        return f"cấp {force_avg}, có lúc cấp {force_avg + 1}, giật cấp {force_gust}"
    return f"cấp {force_avg}, giật cấp {force_gust}"


def wave_height_to_beaufort(height_m: float) -> int:
    """Suy ra cấp gió Bô-pho TƯƠNG ĐƯƠNG từ độ cao sóng (m), theo cột 'Độ
    cao sóng trung bình' của bảng gốc (nội suy tuyến tính giữa các mốc cấp
    đã biết, cấp 13+ không có mốc cụ thể nên trả về 12 khi vượt 14m)."""
    if height_m is None:
        return 0
    known = [(f, h) for f, h in BEAUFORT_WAVE_HEIGHT_M.items() if h is not None]
    known.sort(key=lambda x: x[1])
    if height_m <= known[0][1]:
        return known[0][0]
    for (f0, h0), (f1, h1) in zip(known, known[1:]):
        if h0 <= height_m <= h1:
            return f1 if (height_m - h0) > (h1 - height_m) else f0
    return known[-1][0]


def sea_state_text(height_m: float) -> str:
    """Câu mô tả trạng thái biển ('Biển động', 'Biển động mạnh'...) từ độ
    cao sóng (m), lấy đúng từ BẢNG CẤP GIÓ VÀ SÓNG (Việt Nam) — thay cho
    các ngưỡng tự đặt trước đây, để thống nhất 1 nguồn tham chiếu duy nhất
    trong toàn dự án (bản tin nguy hiểm, bản tin tháng, bản tin mùa)."""
    force = wave_height_to_beaufort(height_m)
    for max_force, text in _SEA_STATE_BY_FORCE:
        if force <= max_force:
            return text
    return _SEA_STATE_BY_FORCE[-1][1]


def hazard_text_for_force(force_avg: int) -> str:
    """Câu 'Mức độ nguy hại' nguyên văn bảng gốc, ứng với cấp gió trung bình."""
    for max_force, text in _HAZARD_TEXT_BY_FORCE:
        if force_avg <= max_force:
            return text
    return _HAZARD_TEXT_BY_FORCE[-1][1]
