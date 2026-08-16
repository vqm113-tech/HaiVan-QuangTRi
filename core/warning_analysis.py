# ==========================================
# core/warning_analysis.py
# HẢI VĂN QUẢNG TRỊ 5.0
# ==========================================


# ==========================================
# CẢNH BÁO SÓNG
# ==========================================

def wave_warning(hmax):

    if hmax >= 4:

        return "Sóng biển cao 4-6m, biển động rất mạnh."

    elif hmax >= 2:

        return "Sóng biển cao 2-4m, biển động."

    elif hmax >= 1.5:

        return "Biển động nhẹ."

    else:

        return ""


# ==========================================
# CẢNH BÁO DÒNG CHẢY
# ==========================================

def current_warning(vmax):

    if vmax >= 1.5:

        return "Dòng chảy mạnh."

    elif vmax >= 1:

        return "Dòng chảy tương đối mạnh."

    else:

        return ""


# ==========================================
# CẢNH BÁO GIÓ
# ==========================================

def wind_warning(wind_level):

    if wind_level >= 7:

        return "Gió mạnh cấp 7 trở lên."

    elif wind_level >= 6:

        return "Gió mạnh cấp 6."

    else:

        return ""


# ==========================================
# PHÂN TÍCH HIỆN TƯỢNG NGUY HIỂM
# ==========================================

def analyze_danger(

        wave_data,

        current_data,

        weather_data

):

    hs = [

        x["Hs"]

        for x in wave_data

    ]

    vmax = [

        x["Speed"]

        for x in current_data

    ]

    hmax = max(hs)

    vmax = max(vmax)

    danger = []


    # SÓNG

    text = wave_warning(hmax)

    if text != "":

        danger.append(text)


    # DÒNG CHẢY

    text = current_warning(vmax)

    if text != "":

        danger.append(text)


    # DÔNG

    for x in weather_data:

        if "dông" in x["Thời_tiết"].lower():

            danger.append(

                "Trong cơn dông có khả năng xuất hiện lốc xoáy và gió giật mạnh."

            )

            break


    # KHÔNG CÓ GÌ ĐÁNG KỂ

    if len(danger) == 0:

        return (

            "Không có hiện tượng nguy hiểm đáng chú ý."

        )


    return " ".join(

        list(

            dict.fromkeys(

                danger

            )

        )

    )