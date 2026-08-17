"""Compatibility shim for Streamlit Cloud (Linux).

The app was originally written to run on Windows and calls os.startfile()
when the user clicks the 'Mở thư mục chứa báo cáo' button. Linux does not
provide os.startfile. Defining a harmless no-op keeps the legacy button from
crashing the web app; generated files remain available through Streamlit's
download buttons.
"""
import os
import sys

if not hasattr(os, "startfile") and sys.platform != "win32":
    def _startfile_linux_compat(_path):
        return None

    os.startfile = _startfile_linux_compat
