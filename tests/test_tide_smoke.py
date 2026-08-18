import os
import pytest
import pandas as pd

from bulletin.area_data import forecast_tide_from_observed


def test_predict_tide_smoke():
    """Smoke test: run forecast_tide_from_observed on the bundled sample Excel.

    - Requires: pip install -r requirements.txt (at least pandas, scipy, numpy)
    - Run locally: pytest -q tests/test_tide_smoke.py

    This test asserts the wrapper returns 10 forecast days and 4 tide series
    (Hx, Hx_time, Hm, Hm_time) each of length 10. If the test fails with an
    exception from the code (insufficient data to fit), inspect the Excel
    sample or run the wrapper manually to see the debug message.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sample_path = os.path.join(repo_root, 'data', 'sample', 'solieu.xlsx')

    if not os.path.exists(sample_path):
        pytest.skip(f"Sample file not found: {sample_path}")

    df = pd.read_excel(sample_path)

    # Call wrapper which performs QC + predict_tide internally
    dates, tide = forecast_tide_from_observed(df, station_key='cua_viet', forecast_days=10)

    assert isinstance(dates, list), "dates must be a list"
    assert len(dates) == 10, f"expected 10 forecast days, got {len(dates)}"

    for key in ('tide_hx', 'tide_hx_time', 'tide_hm', 'tide_hm_time'):
        assert key in tide, f"missing key in tide result: {key}"
        assert isinstance(tide[key], list), f"tide[{key}] must be a list"
        assert len(tide[key]) == 10, f"expected 10 values for {key}, got {len(tide[key])}"
