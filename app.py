import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import traceback

from config import OUTPUT_DIR, WAVE_FILE, CURRENT_FILE
from core.qc import load_data
from core.wave_download import download_wave_data
from core.current_download import download_current_data
from core.weather_download import download_weather_data, WEATHER_FILE
from station_config import STATIONS
from bulletin.area_data import build_area_data
from bulletin.bulletin_generator import (
    create_qtri_bulletin, create_qtri_warning_bulletin,
    create_qtri_monthly_bulletin, create_qtri_seasonal_bulletin,
    REGIONS as BULLETIN_REGIONS,
)
from bulletin.warning_data import build_warning_data, build_warning_dossier_data
from bulletin.monthly_data import build_monthly_data, build_monthly_dossier_data
from bulletin.seasonal_data import build_seasonal_data, build_seasonal_dossier_data
from bulletin.dossier_generator import create_forecast_dossier
from bulletin.excel_export import build_marine_excel

# ==========================================
# CẤU HÌNH GIAO DIỆN STREAMLIT
# ==========================================
st.set_page_config(
    page_title="ĐÀI KHÍ TƯỢNG THUỶ VĂN TRUNG BỘ - ĐÀI KHÍ TƯỢNG THUỶ VĂN TỈNH QUẢNG TRỊ",
    page_icon="HaiVan.png",
    layout="wide"
)
st.image("HaiVan.png", width=100)
st.title("BẢN TIN HẢI VĂN TỈNH QUẢNG TRỊ")
st.divider()


def _file_age_text(path):
    if not path.exists():
        return "chưa có file"
    age_hours = (time.time() - path.stat().st_mtime) / 3600.0
    return f"cập nhật cách đây {age_hours:.1f} giờ"


# ==========================================
# TẢI DỮ LIỆU SÓNG / DÒNG CHẢY TỪ COPERNICUS (tùy chọn)
# ==========================================
with st.sidebar:
    st.subheader("📡 Dữ liệu sóng / dòng chảy / khí tượng")
    st.caption(f"Sóng: {_file_age_text(WAVE_FILE)}")
    st.caption(f"Dòng chảy: {_file_age_text(CURRENT_FILE)}")
    st.caption(f"Khí tượng (mưa/gió/tầm nhìn): {_file_age_text(WEATHER_FILE)}")
    st.caption(
        "Sóng/dòng chảy cần đã đăng nhập Copernicus Marine trên máy này "
        "(`copernicusmarine login`) hoặc đặt biến môi trường "
        "COPERNICUSMARINE_SERVICE_USERNAME / _PASSWORD. Dữ liệu khí tượng "
        "lấy từ Open-Meteo (miễn phí, không cần đăng ký)."
    )
    if st.button("🔄 Tải dữ liệu mới nhất"):
        with st.spinner("Đang tải dữ liệu (sóng + dòng chảy + khí tượng)..."):
            wave_ok = download_wave_data(force=True)
            current_ok = download_current_data(force=True)
            weather_ok = download_weather_data(force=True)
        if wave_ok and current_ok and weather_ok:
            st.success("Đã tải dữ liệu sóng + dòng chảy + khí tượng mới nhất.")
        else:
            missing = []
            if not wave_ok:
                missing.append("sóng")
            if not current_ok:
                missing.append("dòng chảy")
            if not weather_ok:
                missing.append("khí tượng")
            st.warning(
                f"Không tải được dữ liệu: {', '.join(missing)}. "
                "Bản tin vẫn dùng được với file cũ đang có (nếu có) hoặc "
                "giá trị dự phòng — xem log/terminal để biết lỗi cụ thể."
            )

    st.divider()
    st.caption(f"📁 Báo cáo/Excel đã tạo được lưu tại:\n`{OUTPUT_DIR}`")
    if st.button("📂 Mở thư mục chứa báo cáo"):
        try:
            os.startfile(OUTPUT_DIR)
        except Exception as exc:
            st.error(
                f"Không mở được thư mục: {exc}\n\n"
                f"Bạn có thể tự mở bằng cách dán đường dẫn sau vào "
                f"File Explorer:\n{OUTPUT_DIR}"
            )

# ==========================================
# THÔNG TIN BẢN TIN
# ==========================================
col1, col2, col3, col4 = st.columns(4)
with col1:
    forecaster = st.text_input("Dự báo viên", value="Vũ Quang Minh, Vũ Quang Minh")
with col2:
    issue_time = st.text_input("Giờ phát tin", value="16h00")
with col3:
    leader_name = st.text_input("Người ký", value="Phạm Xuân Khánh")
with col4:
    shift_leader = st.text_input("Trưởng ca dự báo", value="Phạm Xuân Khánh")

# ==========================================
# HIỆU CHỈNH DỰ BÁO TRIỀU THEO ĐỊA PHƯƠNG (dành cho dự báo viên)
# ==========================================
CONSTITUENT_ORDER = ["M2", "S2", "N2", "K2", "K1", "O1", "P1", "Q1"]
STATION_DISPLAY = {k: v["name"] for k, v in STATIONS.items()}

with st.expander("⚙️ Hiệu chỉnh dự báo triều theo địa phương (nâng cao)", expanded=False):
    st.caption(
        "Số liệu mực nước đo tại các trạm CỬA SÔNG — chịu ảnh "
        "hưởng dòng chảy nước ngọt/hình thái lòng sông, không thuần túy là "
        "triều biển hở, nên mô hình điều hòa thuần túy có thể lệch so với "
        "thực tế địa phương. Dự báo viên có thể hiệu chỉnh riêng từng trạm "
        "dưới đây dựa trên kinh nghiệm thực tế; để nguyên (0 cm, 100%) nếu "
        "không cần hiệu chỉnh."
    )

    if "tide_corrections" not in st.session_state:
        st.session_state["tide_corrections"] = {}

    correction_station = st.selectbox(
        "Chọn trạm cần hiệu chỉnh",
        options=list(STATIONS.keys()),
        format_func=lambda k: STATION_DISPLAY.get(k, k),
    )
    existing = st.session_state["tide_corrections"].get(correction_station, {})

    manual_offset_cm = st.number_input(
        "Hiệu chỉnh mực nước (m) — cộng/bớt vào toàn bộ chuỗi dự báo",
        min_value=-100.0, max_value=100.0,
        value=float(existing.get("manual_offset_cm", 0.0)),
        step=1.0,
    )

    st.caption(f"Hệ số biên độ từng hằng số triều — {STATION_DISPLAY.get(correction_station)}:")
    default_amp = existing.get("amp_scale", {c: 100.0 for c in CONSTITUENT_ORDER})
    amp_df = pd.DataFrame({
        "Hằng số triều": CONSTITUENT_ORDER,
        "Hệ số biên độ (%)": [default_amp.get(c, 100.0) for c in CONSTITUENT_ORDER],
    })
    edited_amp_df = st.data_editor(
        amp_df, hide_index=True, key=f"amp_editor_{correction_station}",
        column_config={
            "Hằng số triều": st.column_config.TextColumn(disabled=True),
            "Hệ số biên độ (%)": st.column_config.NumberColumn(min_value=0.0, max_value=300.0, step=5.0),
        },
    )
    amp_scale_pct = dict(zip(edited_amp_df["Hằng số triều"], edited_amp_df["Hệ số biên độ (%)"]))

    st.session_state["tide_corrections"][correction_station] = {
        "manual_offset_cm": manual_offset_cm,
        "amp_scale": amp_scale_pct,
    }

    if st.button("↺ Đặt lại hiệu chỉnh về mặc định (trạm này)"):
        st.session_state["tide_corrections"].pop(correction_station, None)
        st.rerun()


def _build_tide_corrections():
    """Chuyển hiệu chỉnh từ st.session_state (cm, %) sang đơn vị mô hình
    cần (m, hệ số nhân) để truyền vào build_area_data()."""
    result = {}
    for station_key, corr in st.session_state.get("tide_corrections", {}).items():
        amp_scale_pct = corr.get("amp_scale", {}) or {}
        amp_scale = {k: float(v) / 100.0 for k, v in amp_scale_pct.items() if v is not None}
        manual_offset_m = float(corr.get("manual_offset_cm", 0.0)) / 100.0
        has_amp_change = any(abs(v - 1.0) > 1e-9 for v in amp_scale.values())
        if has_amp_change or abs(manual_offset_m) > 1e-9:
            result[station_key] = {
                "amplitude_scale": amp_scale if has_amp_change else None,
                "manual_offset_m": manual_offset_m,
            }
    return result


# ==========================================
# HIỆU CHỈNH DỰ BÁO SÓNG / DÒNG CHẢY — RIÊNG TỪNG VÙNG BIỂN
# ==========================================
with st.expander("⚙️ Hiệu chỉnh dự báo sóng / dòng chảy theo từng vùng (nâng cao)", expanded=False):
    st.caption(
        "Chọn vùng biển rồi nhập hệ số nhân — áp dụng cho TẤT CẢ các ngày "
        "dự báo của RIÊNG vùng đó. Ví dụ độ cao sóng dự báo gốc H = 0.5 - "
        "1.5m, đặt hệ số 1.2 → hiển thị H = 0.6 - 1.8m; đặt 0.9 → H = "
        "0.45 - 1.35m. Để 1.0 nếu không cần hiệu chỉnh. Mỗi vùng biển có "
        "hệ số riêng, không ảnh hưởng tới các vùng khác."
    )

    if "marine_corrections" not in st.session_state:
        st.session_state["marine_corrections"] = {}

    marine_region_key = st.selectbox(
        "Chọn vùng biển cần hiệu chỉnh",
        options=[key for _, key in BULLETIN_REGIONS],
        format_func=lambda k: dict((key, name) for name, key in BULLETIN_REGIONS).get(k, k),
        key="marine_region_select",
    )
    existing_marine = st.session_state["marine_corrections"].get(marine_region_key, {})

    col_wave, col_current = st.columns(2)
    with col_wave:
        region_wave_scale = st.number_input(
            "Hệ số hiệu chỉnh độ cao sóng",
            min_value=0.1, max_value=3.0,
            value=float(existing_marine.get("wave_scale", 1.0)),
            step=0.05, format="%.2f", key=f"wave_scale_{marine_region_key}",
        )
    with col_current:
        region_current_scale = st.number_input(
            "Hệ số hiệu chỉnh tốc độ dòng chảy",
            min_value=0.1, max_value=3.0,
            value=float(existing_marine.get("current_scale", 1.0)),
            step=0.05, format="%.2f", key=f"current_scale_{marine_region_key}",
        )

    st.session_state["marine_corrections"][marine_region_key] = {
        "wave_scale": region_wave_scale,
        "current_scale": region_current_scale,
    }

    if st.button("↺ Đặt lại hiệu chỉnh về mặc định (vùng này)"):
        st.session_state["marine_corrections"].pop(marine_region_key, None)
        st.rerun()


def _build_marine_corrections():
    """Chuyển hiệu chỉnh sóng/dòng chảy từ st.session_state thành 2 dict
    {region_key: hệ_số} để truyền vào build_area_data()."""
    wave_scale_dict, current_scale_dict = {}, {}
    for region_key, corr in st.session_state.get("marine_corrections", {}).items():
        wave_scale_dict[region_key] = float(corr.get("wave_scale", 1.0))
        current_scale_dict[region_key] = float(corr.get("current_scale", 1.0))
    return wave_scale_dict, current_scale_dict

# ==========================================
# XUẤT EXCEL SỐ LIỆU SÓNG / DÒNG CHẢY THEO GIỜ
# Độc lập với file Excel thủy triều — dùng đúng file .nc Copernicus đã tải.
# ==========================================
with st.expander("📊 Xuất Excel số liệu sóng / dòng chảy theo giờ", expanded=False):
    st.caption(
        "Xuất toàn bộ chuỗi số liệu sóng và dòng chảy theo đúng mốc thời gian "
        "thật có trong file .nc Copernicus đã tải (sóng 3 giờ/lần, dòng chảy "
        "1 giờ/lần), cho cả 5 vùng dự báo — khác bảng 2/3 trong bản tin (chỉ "
        "có giá trị nhỏ nhất/lớn nhất mỗi ngày). "
        "⚠️ Đây là dữ liệu MÔ HÌNH Copernicus (phân tích + dự báo đại dương), "
        "không phải số liệu đo đạc thực tế tại phao/trạm."
    )
    if st.button("📊 Xuất file Excel"):
        with st.spinner("Đang xuất Excel..."):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            excel_path = os.path.join(OUTPUT_DIR, f"SoLieu_SongDongChay_{timestamp}.xlsx")
            result = build_marine_excel(excel_path)
        if result:
            st.success(f"Đã xuất: {result}")
            with open(result, "rb") as f:
                st.download_button(
                    "⬇ Tải file Excel số liệu sóng/dòng chảy",
                    data=f,
                    file_name=result,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_marine_excel",
                )
        else:
            st.warning(
                "Chưa có dữ liệu .nc để xuất — hãy bấm '🔄 Tải dữ liệu mới nhất' "
                "ở sidebar trước, hoặc kiểm tra đã cài xarray/netCDF4 chưa."
            )

# ==========================================
# TIN DỰ BÁO GIÓ MẠNH, SÓNG LỚN (HẢI VĂN NGUY HIỂM)
# Độc lập với file Excel thủy triều — chỉ cần dữ liệu gió/sóng thật đã tải.
# ==========================================
_WARNING_WIDGET_KEYS = [
    "warn_past", "warn_next24h", "warn_time_range", "warn_zone_table",
    "warn_warning", "warn_risk", "warn_impact",
]

with st.expander("🚨 Tin dự báo gió mạnh, sóng lớn (hải văn nguy hiểm)", expanded=False):
    st.caption(
        "Bản tin riêng, khác bản tin 10 ngày — dùng khi có gió mạnh/sóng lớn "
        "nguy hiểm. Giá trị dự báo (cấp gió, độ cao sóng, cấp độ rủi ro) tự "
        "sinh từ dữ liệu gió thật (Open-Meteo) và sóng thật (Copernicus) đã "
        "tải ở trên — không cần file Excel thủy triều. Dự báo viên xem trước "
        "và có thể sửa trực tiếp bên dưới trước khi xuất bản tin."
    )

    col_calc, col_reset = st.columns([2, 1])
    with col_calc:
        if st.button("🔄 Tính dữ liệu tin gió mạnh, sóng lớn"):
            with st.spinner("Đang tính toán..."):
                try:
                    # Xóa state widget cũ để hiển thị đúng giá trị mới tính,
                    # không bị giữ lại nội dung đã sửa từ lần tính trước.
                    for k in _WARNING_WIDGET_KEYS:
                        st.session_state.pop(k, None)
                    st.session_state["warning_data"] = build_warning_data(forecaster, issue_time)
                except Exception as e:
                    st.error(f"Lỗi khi tính dữ liệu: {e}")
    with col_reset:
        if st.button("↺ Bỏ tính toán"):
            st.session_state.pop("warning_data", None)
            for k in _WARNING_WIDGET_KEYS:
                st.session_state.pop(k, None)
            st.rerun()

    if "warning_data" in st.session_state:
        wd = st.session_state["warning_data"]

        st.markdown("**Xem trước & chỉnh sửa nội dung tin:**")
        wd['past_text'] = st.text_area(
            "1. Hiện trạng đã qua", value=wd.get('past_text', ''), key="warn_past", height=80,
        )
        wd['next24h_text'] = st.text_area(
            "2. Dự báo diễn biến trong 24 giờ tới", value=wd.get('next24h_text', ''),
            key="warn_next24h", height=80,
        )

        wd['time_range_text'] = st.text_input(
            "Thời điểm dự báo (cột đầu bảng, ví dụ 'Đêm 06 và ngày 07/08')",
            value=wd.get('time_range_text', ''), key="warn_time_range",
        )

        zone_labels = {
            "zone": "Vùng biển", "wind_text": "Gió mạnh (cấp Bô-pho)",
            "wave_range": "Độ cao sóng (m)", "wave_dir": "Hướng sóng",
        }
        zone_df = pd.DataFrame(wd.get('zone_rows', [])).rename(columns=zone_labels)
        edited_zone_df = st.data_editor(
            zone_df, key="warn_zone_table", num_rows="fixed", hide_index=True,
            column_config={"Vùng biển": st.column_config.TextColumn(disabled=True)},
        )
        inv_labels = {v: k for k, v in zone_labels.items()}
        wd['zone_rows'] = edited_zone_df.rename(columns=inv_labels).to_dict('records')

        wd['warning_text'] = st.text_area(
            "3. Cảnh báo", value=wd.get('warning_text', ''), key="warn_warning", height=80,
        )
        wd['risk_level'] = st.text_input(
            "4. Cảnh báo cấp độ rủi ro thiên tai trên biển",
            value=wd.get('risk_level', ''), key="warn_risk",
        )
        wd['impact_text'] = st.text_area(
            "5. Dự báo tác động", value=wd.get('impact_text', ''), key="warn_impact", height=80,
        )
        st.caption(
            "⚠️ Cấp độ rủi ro thiên tai là ước lượng tự động — dự báo viên cần tự "
            "kiểm tra lại theo quy định hiện hành trước khi ban hành chính thức."
        )

        if st.button("🚨 Xuất tin gió mạnh, sóng lớn (.docx)"):
            with st.spinner("Đang tạo tin..."):
                try:
                    wd['leader_name'] = leader_name
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                    warning_path = os.path.join(OUTPUT_DIR, f"HVNH_QTRI_{timestamp}.docx")
                    warning_file = create_qtri_warning_bulletin(
                        wd, forecaster, issue_time, output_path=warning_path
                    )
                    st.success(f"Đã tạo thành công: {warning_file}")
                    with open(warning_file, "rb") as f:
                        st.download_button(
                            "⬇ Tải tin gió mạnh, sóng lớn (DOCX)",
                            data=f,
                            file_name=warning_file,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="download_warning",
                        )
                except Exception as e:
                    st.error(f"Lỗi khi tạo tin: {e}")
                    st.code(traceback.format_exc())

        if st.button("📁 Xuất hồ sơ dự báo (HS_) đi kèm tin này"):
            with st.spinner("Đang tạo hồ sơ..."):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                    bulletin_ref = f"HVNH_QTRI_{timestamp}.docx"
                    hs_data = build_warning_dossier_data(
                        wd, shift_leader=shift_leader, forecasters=forecaster,
                        bulletin_file_ref=bulletin_ref,
                    )
                    hs_path = os.path.join(OUTPUT_DIR, f"HS_HVNH_QTRI_{timestamp}.docx")
                    hs_file = create_forecast_dossier(hs_data, output_path=hs_path)
                    st.success(f"Đã tạo thành công: {hs_file}")
                    with open(hs_file, "rb") as f:
                        st.download_button(
                            "⬇ Tải hồ sơ dự báo (DOCX)",
                            data=f,
                            file_name=hs_file,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="download_hs_warning",
                        )
                except Exception as e:
                    st.error(f"Lỗi khi tạo hồ sơ: {e}")
                    st.code(traceback.format_exc())

# ==========================================
# CHỌN FILE MỰC NƯỚC
# ==========================================
uploaded_file = st.file_uploader(
    "Chọn file số liệu mực nước (*.xlsx)",
    type=["xlsx"]
)

# ==========================================
# XỬ LÝ VÀ TẠO BẢN TIN
# ==========================================
if uploaded_file is not None:
    try:
        # 1. Đọc dữ liệu mực nước từ Excel
        with st.spinner("Đang đọc dữ liệu..."):
            df = load_data(uploaded_file)
        st.success("Đọc dữ liệu thành công.")

        # 2. Xây dựng toàn bộ dữ liệu khu vực: QC + mô hình triều chuẩn (có
        # áp dụng hiệu chỉnh của dự báo viên nếu có) + sóng/dòng chảy thật từ
        # file .nc (data/wave_data/wave.nc, data/current_data/current.nc —
        # dùng nút "Tải dữ liệu mới nhất" ở sidebar để cập nhật trước khi tạo
        # bản tin nếu cần). Xem README mục "Trạng thái thật" để biết rõ phần
        # nào là dữ liệu thật, phần nào vẫn còn là suy diễn/giả định.
        tide_corrections = _build_tide_corrections()
        wave_scale_dict, current_scale_dict = _build_marine_corrections()
        with st.spinner("Đang xử lý và xây dựng dữ liệu hải văn..."):
            area_data = build_area_data(
                df, tide_corrections=tide_corrections,
                wave_scale=wave_scale_dict, current_scale=current_scale_dict,
            )
            if not isinstance(area_data, dict):
                area_data = {}
        st.success("Hoàn thành dữ liệu hải văn.")

        # 2b. Xem trước & CHO PHÉP SỬA TRỰC TIẾP nội dung bản tin trước khi
        # xuất file .docx — nội dung đã sửa sẽ được dùng khi bấm "TẠO BẢN TIN".
        FIELD_LABELS = {
            'weather': 'Hiện tượng thời tiết', 'visibility': 'Tầm nhìn xa',
            'wind': 'Hướng, tốc độ gió', 'sea_state': 'Tình trạng biển',
            'tide_hx': 'Đỉnh triều Hx (m)', 'tide_hx_time': 'Giờ đỉnh triều',
            'tide_hm': 'Chân triều Hm (m)', 'tide_hm_time': 'Giờ chân triều',
            'wave_height': 'Độ cao sóng H (m)', 'wave_dir': 'Hướng sóng',
            'current_speed': 'Tốc độ dòng chảy (m/s)', 'current_dir': 'Hướng dòng chảy',
        }
        LABEL_TO_FIELD = {v: k for k, v in FIELD_LABELS.items()}

        def _to_edit_df(region_dict, days):
            if not region_dict:
                return pd.DataFrame()
            tdf = pd.DataFrame(region_dict)
            tdf.index = list(days[:len(tdf)])
            tdf = tdf.T
            tdf.index = [FIELD_LABELS.get(i, i) for i in tdf.index]
            return tdf

        def _from_edit_df(edited_df):
            result = {}
            for label, row in edited_df.iterrows():
                field_key = LABEL_TO_FIELD.get(label, label)
                result[field_key] = row.tolist()
            return result

        with st.expander("📋 Xem trước & chỉnh sửa nội dung bản tin", expanded=True):
            st.caption(
                "Dự báo viên có thể sửa trực tiếp nội dung dưới đây (văn bản và "
                "số liệu trong bảng) — bản tin xuất ra sẽ dùng đúng nội dung đã "
                "sửa, không phải nội dung tính toán gốc."
            )
            if st.button("↺ Khôi phục nội dung gốc (bỏ mọi chỉnh sửa)"):
                for k in list(st.session_state.keys()):
                    if k.startswith("edit_sec_") or k.startswith("edit_t1_") \
                            or k.startswith("edit_t2_") or k.startswith("edit_t3_"):
                        del st.session_state[k]
                st.rerun()

            sec_titles = {
                'sec1_text': "1. Tình hình hải văn trong 24 giờ qua",
                'sec2_text': "2. Dự báo thời tiết biển trong 3 ngày",
                'sec3_text': "3. Dự báo hải văn trong 3 ngày",
                'sec4_text': "4. Dự báo hải văn từ ngày thứ 4 đến ngày thứ 10",
                'sec5_text': "5. Khả năng xuất hiện hiện tượng nguy hiểm",
                'sec6_text': "6. Khả năng tác động đến môi trường, kinh tế - xã hội",
            }
            for key, title in sec_titles.items():
                area_data[key] = st.text_area(
                    title, value=area_data.get(key, ""), key=f"edit_sec_{key}", height=90,
                )

            days_3 = area_data.get('days_3', [])
            days_7 = area_data.get('days_7', [])
            table_tabs = st.tabs([name for name, _ in BULLETIN_REGIONS])
            for tab, (name, key) in zip(table_tabs, BULLETIN_REGIONS):
                with tab:
                    st.markdown("**Bảng 1 — Thời tiết biển (3 ngày)**")
                    edited1 = st.data_editor(
                        _to_edit_df(area_data.get('table1_data', {}).get(key), days_3),
                        key=f"edit_t1_{key}", num_rows="fixed",
                    )
                    area_data.setdefault('table1_data', {})[key] = _from_edit_df(edited1)

                    st.markdown("**Bảng 2 — Hải văn (3 ngày)**")
                    edited2 = st.data_editor(
                        _to_edit_df(area_data.get('table2_data', {}).get(key), days_3),
                        key=f"edit_t2_{key}", num_rows="fixed",
                    )
                    area_data.setdefault('table2_data', {})[key] = _from_edit_df(edited2)

                    st.markdown("**Bảng 3 — Hải văn (ngày 4-10)**")
                    edited3 = st.data_editor(
                        _to_edit_df(area_data.get('table3_data', {}).get(key), days_7),
                        key=f"edit_t3_{key}", num_rows="fixed",
                    )
                    area_data.setdefault('table3_data', {})[key] = _from_edit_df(edited3)

        # ==========================================
        # BẢN TIN HẢI VĂN THỜI HẠN THÁNG (HV1T)
        # ==========================================
        _MONTHLY_WIDGET_KEYS = [
            "m_sec1_wave", "m_sec1_tide", "m_sec2_wave", "m_sec2_tide",
            "m_sec3", "m_sec4",
        ]
        with st.expander("📅 Bản tin hải văn thời hạn THÁNG (HV1T)", expanded=False):
            st.caption(
                "Bảng thủy triều (Hx/Hm theo 3 kỳ 01-10/11-20/21-cuối tháng) tính "
                "thật từ mô hình điều hòa triều, ngoại suy đến hết tháng dự báo. "
                "Sóng biển chỉ có số liệu thật (Copernicus) cho ~10 ngày đầu tháng — "
                "phần còn lại và các đoạn văn bản nhận định là giá trị khởi điểm, "
                "dự báo viên cần sửa lại theo nghiệp vụ trước khi xuất."
            )
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                m_target_month = st.number_input("Tháng dự báo", min_value=1, max_value=12,
                                                   value=(datetime.now().month % 12) + 1, key="m_target_month")
            with col_m2:
                m_target_year = st.number_input("Năm dự báo", min_value=2020, max_value=2100,
                                                  value=datetime.now().year, key="m_target_year")
            with col_m3:
                st.write("")

            col_mc, col_mr = st.columns([2, 1])
            with col_mc:
                if st.button("🔄 Tính dữ liệu bản tin tháng"):
                    with st.spinner("Đang tính toán..."):
                        try:
                            for k in _MONTHLY_WIDGET_KEYS:
                                st.session_state.pop(k, None)
                            st.session_state["monthly_data"] = build_monthly_data(
                                df, target_month=int(m_target_month), target_year=int(m_target_year),
                                tide_corrections=tide_corrections, wave_scale=wave_scale_dict,
                                forecaster=forecaster, issue_time=issue_time,
                            )
                        except Exception as e:
                            st.error(f"Lỗi khi tính dữ liệu: {e}")
                            st.code(traceback.format_exc())
            with col_mr:
                if st.button("↺ Bỏ tính toán", key="m_reset"):
                    st.session_state.pop("monthly_data", None)
                    for k in _MONTHLY_WIDGET_KEYS:
                        st.session_state.pop(k, None)
                    st.rerun()

            if "monthly_data" in st.session_state:
                md = st.session_state["monthly_data"]
                st.markdown(f"**Xem trước & chỉnh sửa — {md.get('title_period', '')}:**")
                md['sec1_wave_text'] = st.text_area(
                    "1. Phân tích tháng trước — Sóng biển", value=md.get('sec1_wave_text', ''),
                    key="m_sec1_wave", height=70,
                )
                md['sec1_tide_text'] = st.text_area(
                    "1. Phân tích tháng trước — Triều cường", value=md.get('sec1_tide_text', ''),
                    key="m_sec1_tide", height=70,
                )
                md['sec2_wave_text'] = st.text_area(
                    "2. Dự báo tháng này — Sóng biển", value=md.get('sec2_wave_text', ''),
                    key="m_sec2_wave", height=70,
                )
                md['sec2_tide_text'] = st.text_area(
                    "2. Dự báo tháng này — Triều cường", value=md.get('sec2_tide_text', ''),
                    key="m_sec2_tide", height=70,
                )

                st.markdown("**Bảng 1 — Dự báo vùng biển theo 3 kỳ trong tháng**")
                period_labels = md.get('period_labels', ['01-10', '11-20', '21-30'])
                m_table_tabs = st.tabs([name for name, _ in md.get('regions', [])])
                for tab, (name, key) in zip(m_table_tabs, md.get('regions', [])):
                    with tab:
                        reg_dict = md.get('table_data', {}).get(key, {})
                        edit_df = pd.DataFrame(reg_dict, index=period_labels).T
                        edited = st.data_editor(edit_df, key=f"m_edit_{key}", num_rows="fixed")
                        md.setdefault('table_data', {})[key] = {
                            row: edited.loc[row].tolist() for row in edited.index
                        }

                md['sec3_text'] = st.text_area(
                    "3. Khả năng xuất hiện hiện tượng nguy hiểm", value=md.get('sec3_text', ''),
                    key="m_sec3", height=70,
                )
                md['sec4_text'] = st.text_area(
                    "4. Khả năng tác động", value=md.get('sec4_text', ''),
                    key="m_sec4", height=70,
                )

                col_mx1, col_mx2 = st.columns(2)
                with col_mx1:
                    if st.button("📄 Xuất bản tin tháng (.docx)"):
                        with st.spinner("Đang tạo bản tin..."):
                            try:
                                md['leader_name'] = leader_name
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                                m_path = os.path.join(OUTPUT_DIR, f"HV1T_QTRI_{timestamp}.docx")
                                m_file = create_qtri_monthly_bulletin(
                                    md, forecaster, issue_time, output_path=m_path
                                )
                                st.session_state["monthly_bulletin_ref"] = os.path.basename(m_file)
                                st.success(f"Đã tạo thành công: {m_file}")
                                with open(m_file, "rb") as f:
                                    st.download_button(
                                        "⬇ Tải bản tin tháng (DOCX)", data=f, file_name=m_file,
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key="download_monthly",
                                    )
                            except Exception as e:
                                st.error(f"Lỗi khi tạo bản tin: {e}")
                                st.code(traceback.format_exc())
                with col_mx2:
                    if st.button("📁 Xuất hồ sơ dự báo (HS_) đi kèm", key="hs_monthly_btn"):
                        with st.spinner("Đang tạo hồ sơ..."):
                            try:
                                bulletin_ref = st.session_state.get("monthly_bulletin_ref", "")
                                hs_data = build_monthly_dossier_data(
                                    md, shift_leader=shift_leader, forecasters=forecaster,
                                    bulletin_file_ref=bulletin_ref,
                                )
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                                hs_path = os.path.join(OUTPUT_DIR, f"HS_HV1T_QTRI_{timestamp}.docx")
                                hs_file = create_forecast_dossier(hs_data, output_path=hs_path)
                                st.success(f"Đã tạo thành công: {hs_file}")
                                with open(hs_file, "rb") as f:
                                    st.download_button(
                                        "⬇ Tải hồ sơ dự báo tháng (DOCX)", data=f, file_name=hs_file,
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key="download_hs_monthly",
                                    )
                            except Exception as e:
                                st.error(f"Lỗi khi tạo hồ sơ: {e}")
                                st.code(traceback.format_exc())

        # ==========================================
        # BẢN TIN HẢI VĂN THỜI HẠN MÙA (HVHM)
        # ==========================================
        _SEASONAL_WIDGET_KEYS = [
            "s_sec1", "s_sec2", "s_sec2w", "s_sec2i", "s_sec3", "s_sec3w", "s_sec3i",
        ]
        with st.expander("🌤️ Bản tin hải văn thời hạn MÙA (HVHM)", expanded=False):
            st.caption(
                "Bảng 1 (2 tháng qua) tính thật từ số liệu thực đo trong file Excel. "
                "Bảng 2 (thủy triều 3 tháng tới, Nước lớn/Nước ròng từng tháng) tính "
                "thật từ mô hình điều hòa triều ngoại suy ~90 ngày. Các đoạn nhận định "
                "sóng/XTNĐ/khí hậu không có nguồn số liệu thật trong dự án — là giá trị "
                "khởi điểm, dự báo viên cần sửa lại theo nghiệp vụ trước khi xuất."
            )
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                s_start_month = st.number_input("Tháng đầu kỳ dự báo (3 tháng)", min_value=1, max_value=12,
                                                  value=(datetime.now().month % 12) + 1, key="s_start_month")
            with col_s2:
                s_start_year = st.number_input("Năm", min_value=2020, max_value=2100,
                                                 value=datetime.now().year, key="s_start_year")

            col_sc, col_sr = st.columns([2, 1])
            with col_sc:
                if st.button("🔄 Tính dữ liệu bản tin mùa"):
                    with st.spinner("Đang tính toán..."):
                        try:
                            for k in _SEASONAL_WIDGET_KEYS:
                                st.session_state.pop(k, None)
                            st.session_state["seasonal_data"] = build_seasonal_data(
                                df, start_month=int(s_start_month), start_year=int(s_start_year),
                                tide_corrections=tide_corrections,
                                forecaster=forecaster, issue_time=issue_time,
                            )
                        except Exception as e:
                            st.error(f"Lỗi khi tính dữ liệu: {e}")
                            st.code(traceback.format_exc())
            with col_sr:
                if st.button("↺ Bỏ tính toán", key="s_reset"):
                    st.session_state.pop("seasonal_data", None)
                    for k in _SEASONAL_WIDGET_KEYS:
                        st.session_state.pop(k, None)
                    st.rerun()

            if "seasonal_data" in st.session_state:
                sd = st.session_state["seasonal_data"]
                st.markdown(f"**Xem trước & chỉnh sửa — {sd.get('title_period', '')}:**")
                sd['sec1_text'] = st.text_area(
                    "1. Phân tích 02 tháng qua", value=sd.get('sec1_text', ''), key="s_sec1", height=70,
                )

                st.markdown(f"**Bảng 1 — Đặc trưng tại {sd.get('table1_station_name', '')}**")
                t1_display_rows = []
                for row in sd.get('table1_rows', []):
                    if row:
                        r = dict(row)
                        if r.get('hmax') is not None:
                            r['hmax (m)'] = r.pop('hmax') / 100.0
                        if r.get('hmin') is not None:
                            r['hmin (m)'] = r.pop('hmin') / 100.0
                        t1_display_rows.append(r)
                    else:
                        t1_display_rows.append(row)
                t1_df = pd.DataFrame(t1_display_rows, index=sd.get('table1_labels', []))
                st.dataframe(t1_df, use_container_width=True)

                sd['sec2_text'] = st.text_area(
                    f"2. Dự báo hải văn {sd.get('forecast_period_label', '')}",
                    value=sd.get('sec2_text', ''), key="s_sec2", height=70,
                )
                sd['sec2_warning_text'] = st.text_area(
                    "2. Cảnh báo hiện tượng hải văn nguy hiểm", value=sd.get('sec2_warning_text', ''),
                    key="s_sec2w", height=70,
                )
                sd['sec2_impact_text'] = st.text_area(
                    "2. Khả năng tác động", value=sd.get('sec2_impact_text', ''),
                    key="s_sec2i", height=70,
                )

                st.markdown("**Bảng 2 — Dự báo thủy triều 3 tháng tới**")
                for name, key in sd.get('regions', []):
                    month_rows = sd.get('table2_data', {}).get(key, [])
                    forecast_months = sd.get('forecast_months', [])
                    m_labels = [f"Tháng {mo}/{yr}" for yr, mo in forecast_months]
                    st.caption(name)
                    m2_display_rows = []
                    for row in month_rows:
                        r = dict(row)
                        if r.get('hx') is not None:
                            r['hx (m)'] = r.pop('hx') / 100.0
                        if r.get('hm') is not None:
                            r['hm (m)'] = r.pop('hm') / 100.0
                        m2_display_rows.append(r)
                    st.dataframe(pd.DataFrame(m2_display_rows, index=m_labels), use_container_width=True)

                sd['sec3_text'] = st.text_area(
                    f"3. Xu thế hải văn {sd.get('xu_the_period_label', '')}",
                    value=sd.get('sec3_text', ''), key="s_sec3", height=70,
                )
                sd['sec3_warning_text'] = st.text_area(
                    "3. Cảnh báo triều cường / hiện tượng nguy hiểm", value=sd.get('sec3_warning_text', ''),
                    key="s_sec3w", height=70,
                )
                sd['sec3_impact_text'] = st.text_area(
                    "3. Khả năng tác động", value=sd.get('sec3_impact_text', ''),
                    key="s_sec3i", height=70,
                )

                col_sx1, col_sx2 = st.columns(2)
                with col_sx1:
                    if st.button("📄 Xuất bản tin mùa (.docx)"):
                        with st.spinner("Đang tạo bản tin..."):
                            try:
                                sd['leader_name'] = leader_name
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                                s_path = os.path.join(OUTPUT_DIR, f"HVHM_QTRI_{timestamp}.docx")
                                s_file = create_qtri_seasonal_bulletin(
                                    sd, forecaster, issue_time, output_path=s_path
                                )
                                st.session_state["seasonal_bulletin_ref"] = os.path.basename(s_file)
                                st.success(f"Đã tạo thành công: {s_file}")
                                with open(s_file, "rb") as f:
                                    st.download_button(
                                        "⬇ Tải bản tin mùa (DOCX)", data=f, file_name=s_file,
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key="download_seasonal",
                                    )
                            except Exception as e:
                                st.error(f"Lỗi khi tạo bản tin: {e}")
                                st.code(traceback.format_exc())
                with col_sx2:
                    if st.button("📁 Xuất hồ sơ dự báo (HS_) đi kèm", key="hs_seasonal_btn"):
                        with st.spinner("Đang tạo hồ sơ..."):
                            try:
                                bulletin_ref = st.session_state.get("seasonal_bulletin_ref", "")
                                hs_data = build_seasonal_dossier_data(
                                    sd, shift_leader=shift_leader, forecasters=forecaster,
                                    bulletin_file_ref=bulletin_ref,
                                )
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                                hs_path = os.path.join(OUTPUT_DIR, f"HS_HVHM_QTRI_{timestamp}.docx")
                                hs_file = create_forecast_dossier(hs_data, output_path=hs_path)
                                st.success(f"Đã tạo thành công: {hs_file}")
                                with open(hs_file, "rb") as f:
                                    st.download_button(
                                        "⬇ Tải hồ sơ dự báo mùa (DOCX)", data=f, file_name=hs_file,
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key="download_hs_seasonal",
                                    )
                            except Exception as e:
                                st.error(f"Lỗi khi tạo hồ sơ: {e}")
                                st.code(traceback.format_exc())

        # 3. Tạo và xuất bản tin Word (.docx)
        if st.button("📄 TẠO BẢN TIN"):
            with st.spinner("Đang tạo DOCX..."):
                # Cập nhật thông tin giao diện vào dictionary dữ liệu
                area_data['forecasters'] = forecaster
                area_data['issue_time'] = issue_time
                area_data['leader_name'] = leader_name

                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                output_path = os.path.join(OUTPUT_DIR, f"HVHN_QTRI_{timestamp}.docx")

                # Gọi hàm xuất bản tin, lưu vào thư mục outputs/ (không lẫn vào mã nguồn)
                filename = create_qtri_bulletin(
                    area_data,
                    forecaster,
                    issue_time,
                    output_path=output_path
                )

            st.success(f"Đã tạo thành công: {filename}")

            with open(filename, "rb") as f:
                st.download_button(
                    "⬇ Tải bản tin DOCX",
                    data=f,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
        st.code(traceback.format_exc())
