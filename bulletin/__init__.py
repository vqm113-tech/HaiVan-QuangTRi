"""Khởi tạo package bulletin và chuẩn hóa đơn vị cho hồ sơ mùa."""

# dossier_generator.py dùng `from bulletin.bulletin_generator import
# _add_seasonal_appendix_tables` ngay khi module được import. Vì vậy patch phải
# được cài ở package initializer, trước khi dossier_generator được nạp.
# Đây là điểm cố định để Phụ lục 1 và Phụ lục 2 của hồ sơ mùa luôn dùng mét.
try:
    from . import bulletin_generator as _bg

    def _seasonal_appendix_tables_in_meters(doc, data_dict):
        section = doc.sections[-1]
        n_months = len(data_dict.get("forecast_months", [])) or 3
        col_widths = _bg._compute_tide_table_col_widths(
            section.page_width,
            section.left_margin,
            section.right_margin,
            n_months,
        )

        _bg._render_tide_zone_table(
            doc,
            data_dict,
            "Phụ lục 1: Kết quả dự báo theo phương pháp phân tích hàm điều hòa",
            col_widths,
            use_cm=False,
        )
        _bg._render_tide_zone_table(
            doc,
            data_dict,
            "Phụ lục 2: Chọn kết quả dự báo",
            col_widths,
            use_cm=False,
        )

    _bg._add_seasonal_appendix_tables = _seasonal_appendix_tables_in_meters
except Exception:
    # Không làm hỏng các bản tin khác nếu package khởi tạo trong môi trường
    # kiểm thử thiếu một dependency phụ.
    pass
