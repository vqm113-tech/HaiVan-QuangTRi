"""Streamlit Cloud compatibility for the legacy Windows report-folder button.

The original app calls os.startfile(OUTPUT_DIR). On Linux/Streamlit Cloud,
there is no Windows File Explorer, so this compatibility layer turns that
button into a small download area for files generated in OUTPUT_DIR.
"""
import mimetypes
import os
import sys
from pathlib import Path


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
                mime_type = mimetypes.guess_type(file_path.name)[0]
                if not mime_type:
                    mime_type = "application/octet-stream"

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
