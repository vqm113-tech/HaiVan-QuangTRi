"""Streamlit Cloud compatibility and seasonal bulletin formatting fixes."""
import mimetypes
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Streamlit Cloud: replace the legacy Windows folder-opening action with
# browser downloads.
# ---------------------------------------------------------------------------
if not hasattr(os, "startfile") and sys.platform != "win32":
    def _startfile_linux_compat(path):
        try:
            import streamlit as st

            output_dir = Path(path)
            st.markdown("### 📥 TẢI FILE BÁO CÁO")
            if not output_dir.exists():
                st.info("Chưa có file báo cáo để tải.")
                return

            files = sorted(
                (p for p in output_dir.iterdir() if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not files:
                st.info("Chưa có file báo cáo để tải.")
                return

            for file_path in files:
                mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
                with file_path.open("rb") as file_obj:
                    st.download_button(
                        label=f"⬇️ Tải {file_path.name}",
                        data=file_obj.read(),
                        file_name=file_path.name,
                        mime=mime_type,
                        key=f"cloud_download_{file_path.name}",
                    )
        except Exception as exc:
            import streamlit as st
            st.error(f"Không thể tạo khu vực tải file: {exc}")

    os.startfile = _startfile_linux_compat


# ---------------------------------------------------------------------------
# Bản tin mùa: chỉnh Bảng 1 đúng bố cục mẫu và đổi đơn vị phụ lục mùa sang m.
# Dùng wrapper sau khi generator gốc tạo DOCX, nên không ảnh hưởng các bản tin
# 10 ngày/tháng/nguy hiểm.
# ---------------------------------------------------------------------------
try:
    from docx import Document
    from docx.shared import Pt, Twips
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import bulletin.bulletin_generator as _bg

    _original_seasonal_bulletin = _bg.create_qtri_seasonal_bulletin
    _original_appendix_tables = _bg._add_seasonal_appendix_tables

    def _set_seasonal_table_widths(table, widths_dxa):
        table.autofit = False
        for i, width in enumerate(widths_dxa):
            table.columns[i].width = Twips(width)
            for row in table.rows:
                row.cells[i].width = Twips(width)

    def _format_seasonal_t1_cell(cell, text, bold=False, size=10.5):
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.clear()
        r = p.add_run(str(text))
        r.bold = bold
        r.font.name = "Times New Roman"
        r.font.size = Pt(size)
        _bg.set_cell_margins(cell, top=45, bottom=45, left=35, right=35)

    def _replace_seasonal_table1(output_path, data_dict):
        doc = Document(output_path)

        old_table = None
        for table in doc.tables:
            txt = " ".join(c.text for row in table.rows for c in row.cells)
            if "Yếu tố" in txt and ("Hmax" in txt or "Hmin" in txt):
                old_table = table
                break
        if old_table is None:
            return

        labels = list(data_dict.get("table1_labels", []))[:3]
        rows = list(data_dict.get("table1_rows", []))[:3]
        while len(labels) < 3:
            labels.append("-")
        while len(rows) < 3:
            rows.append({})

        station_name = data_dict.get("table1_station_name", "Cồn Cỏ")

        # Bố cục đúng ảnh mẫu: 3 cột mô tả + 3 cột kỳ, một hàng tiêu đề.
        new_table = doc.add_table(rows=1, cols=6)
        new_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _bg.set_table_borders(new_table)

        hdr = new_table.rows[0].cells
        merged_hdr = hdr[0].merge(hdr[2])
        _format_seasonal_t1_cell(merged_hdr, "Yếu tố", bold=True, size=11)
        for i, label in enumerate(labels):
            _format_seasonal_t1_cell(hdr[3 + i], label, bold=True, size=10.5)

        specs = [
            ("Thủy triều", "Nước lớn", "Hmax (cm)", "hmax"),
            ("Thủy triều", "Nước lớn", "Ngày xuất hiện", "hmax_day"),
            ("Thủy triều", "Nước ròng", "Hmin (cm)", "hmin"),
            ("Thủy triều", "Nước ròng", "Ngày xuất hiện", "hmin_day"),
            ("Sóng", "", "Độ cao sóng lớn nhất (m)", "wave_max"),
            ("Sóng", "", "Hướng sóng", "wave_dir"),
            ("Sóng", "", "Ngày xuất hiện", "wave_day"),
        ]

        group_starts = {}
        group_ends = {}
        for group_name, sub_name, metric, key in specs:
            cells = new_table.add_row().cells
            row_idx = len(new_table.rows) - 1
            group_starts.setdefault(group_name, row_idx)
            group_ends[group_name] = row_idx
            _format_seasonal_t1_cell(cells[1], sub_name, size=10.5)
            _format_seasonal_t1_cell(cells[2], metric, size=10.5)

            for period_idx, ext in enumerate(rows):
                value = ext.get(key) if ext else None
                if value is None or value == "":
                    value = "-"
                elif key in ("hmax", "hmin"):
                    value = str(int(round(float(value))))
                elif key in ("hmax_day", "hmin_day", "wave_day"):
                    value = str(int(value)) if str(value).isdigit() else str(value)
                _format_seasonal_t1_cell(cells[3 + period_idx], value, size=10.5)

        for group_name in ("Thủy triều", "Sóng"):
            _bg.merge_vertical(
                new_table, 0, group_starts[group_name], group_ends[group_name],
                group_name, bold=False, size=11,
            )

        # Cột cố định para vừa A4 đứng; các kỳ cuối đủ rộng cho ngày/giá trị.
        _set_seasonal_table_widths(new_table, [1120, 1050, 1750, 1700, 1700, 1700])

        # Đặt bảng mới đúng vị trí bảng cũ.
        old_element = old_table._element
        parent = old_element.getparent()
        new_element = new_table._element
        parent.replace(old_element, new_element)

        # Tiêu đề Bảng 1 theo đúng kiểu ảnh mẫu.
        for paragraph in doc.paragraphs:
            if paragraph.text.strip().startswith("Bảng 1:"):
                if len(labels) >= 3:
                    first = labels[0].replace("Tháng ", "tháng ")
                    first_month = first.split("/")[0]
                    last = labels[2]
                    m = re.search(r"01-(\d+)/(\d+)/(\d+)", last)
                    if m:
                        title = (
                            f"Bảng 1: Đặc trưng sóng, thủy triều tại trạm Hải văn {station_name} "
                            f"từ tháng {first_month} đến ngày {int(m.group(1))} tháng {int(m.group(2))}/{m.group(3)}"
                        )
                    else:
                        title = paragraph.text
                else:
                    title = paragraph.text
                paragraph.text = title
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.bold = True
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)
                break

        doc.save(output_path)

    def _fixed_seasonal_bulletin(data_dict, forecaster=None, issue_time=None, output_path="Ban_tin_Hai_van_Mua_Quang_Tri.docx"):
        result = _original_seasonal_bulletin(
            data_dict, forecaster=forecaster, issue_time=issue_time, output_path=output_path
        )
        try:
            _replace_seasonal_table1(result, data_dict)
        except Exception:
            # Không làm hỏng việc xuất bản tin nếu chỉ phần định dạng hậu xử lý gặp lỗi.
            pass
        return result

    _bg.create_qtri_seasonal_bulletin = _fixed_seasonal_bulletin

    def _fixed_seasonal_appendix_tables(doc, data_dict):
        # Hồ sơ mùa: Phụ lục 1 và 2 dùng MÉT (m), không dùng cm.
        section = doc.sections[-1]
        n_months = len(data_dict.get("forecast_months", [])) or 3
        col_widths = _bg._compute_tide_table_col_widths(
            section.page_width, section.left_margin, section.right_margin, n_months
        )
        _bg._render_tide_zone_table(
            doc, data_dict,
            "Phụ lục 1: Kết quả dự báo theo phương pháp phân tích hàm điều hòa",
            col_widths, use_cm=False,
        )
        _bg._render_tide_zone_table(
            doc, data_dict,
            "Phụ lục 2: Chọn kết quả dự báo",
            col_widths, use_cm=False,
        )

    _bg._add_seasonal_appendix_tables = _fixed_seasonal_appendix_tables

except Exception:
    # Không chặn Streamlit khởi động nếu một phiên bản môi trường thiếu docx.
    pass
