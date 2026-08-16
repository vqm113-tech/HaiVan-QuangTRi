# ==========================================
# core/ai_forecaster.py
# HẢI VĂN QUẢNG TRỊ 5.0
# ==========================================

from core.weather_analysis import (
    generate_weather_3days
)

from core.sea_weather_text import (
    generate_weather_summary,
    generate_marine_comment,
    analyze_impact
)

from core.warning_analysis import (
    analyze_danger
)

from core.longterm_analysis import (
    generate_longterm_comment
)


# ==========================================
# BỘ NÃO DỰ BÁO
# ==========================================

def generate_ai_forecast(

        tide_data,

        wave_data,

        current_data

):

    # =====================
    # THỜI TIẾT BIỂN
    # =====================

    weather_3days = generate_weather_3days(
        wave_data
    )

    weather_text = generate_weather_summary(
        weather_3days
    )

    # =====================
    # NHẬN XÉT HẢI VĂN 3 NGÀY
    # =====================

    marine_text = generate_marine_comment(

        tide_data,

        wave_data,

        current_data

    )

    # =====================
    # HIỆN TƯỢNG NGUY HIỂM
    # =====================

    danger_text = analyze_danger(

        wave_data,

        current_data,

        weather_3days

    )

    # =====================
    # KHẢ NĂNG TÁC ĐỘNG
    # =====================

    impact_text = analyze_impact(

        wave_data,

        current_data

    )

    # =====================
    # XU THẾ NGÀY 4-10
    # =====================

    longterm_text = generate_longterm_comment(

        tide_data,

        wave_data,

        current_data

    )

    # =====================
    # KẾT QUẢ
    # =====================

    return {

        "weather_3days": weather_3days,

        "weather_text": weather_text,

        "marine_text": marine_text,

        "danger_text": danger_text,

        "impact_text": impact_text,

        "longterm_text": longterm_text

    }