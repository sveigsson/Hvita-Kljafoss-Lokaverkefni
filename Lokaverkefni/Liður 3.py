import csv
import math
from datetime import date
from statistics import mean, median


GAUGE_ID = 37
HEITI = "Hvítá við Kljáfoss"
RUNOFF_FILE = f"lamah_ice/D_gauges/2_timeseries/daily_filtered/ID_{GAUGE_ID}.csv"
HYDRO_INDICES_FILE = "lamah_ice/D_gauges/1_attributes/hydro_indices_1981_2018.csv"
BASEFLOW_OUTPUT_FILE = "lidur_3_baseflow_kljafoss.csv"
BASEFLOW_SVG_FILE = "lidur_3_baseflow_recession_kljafoss.svg"

START_DATE = date(1993, 10, 1)
END_DATE = date(2023, 9, 30)


def lesa_rennsli(skra):
    rennsli = []

    with open(skra, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            dagur = date(int(row["YYYY"]), int(row["MM"]), int(row["DD"]))
            if not (START_DATE <= dagur <= END_DATE):
                continue

            qobs = row["qobs"].strip()
            if not qobs:
                continue

            q = float(qobs)
            if q >= 0:
                rennsli.append((dagur, q))

    return rennsli


def lesa_lamah_bfi(skra, gauge_id):
    with open(skra, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if int(row["id"]) == gauge_id:
                return float(row["baseflow_index_ladson"])

    return None


def ladson_baseflow_filter(q, alpha=0.98):
    """Recursive digital filter, oft kenndur vid Lyne-Hollick/Ladson."""
    if not q:
        return []

    quickflow = [0.0] * len(q)
    baseflow = [q[0]]

    for i in range(1, len(q)):
        quickflow[i] = alpha * quickflow[i - 1] + ((1 + alpha) / 2) * (q[i] - q[i - 1])
        quickflow[i] = max(0.0, min(quickflow[i], q[i]))
        baseflow.append(q[i] - quickflow[i])

    return baseflow


def recession_segments(q, min_length=5):
    segments = []
    i = 0

    while i < len(q) - 1:
        if q[i] > 0 and q[i + 1] > 0 and q[i + 1] < q[i]:
            start = i
            while i < len(q) - 1 and q[i] > 0 and q[i + 1] > 0 and q[i + 1] < q[i]:
                i += 1
            end = i

            if end - start + 1 >= min_length:
                segments.append((start, end))

        i += 1

    return segments


def recession_constant(q, segments):
    k_values = []

    for start, end in segments:
        x = list(range(end - start + 1))
        y = [math.log(q[i]) for i in range(start, end + 1)]

        x_mean = mean(x)
        y_mean = mean(y)
        denominator = sum((xi - x_mean) ** 2 for xi in x)

        if denominator == 0:
            continue

        slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / denominator

        if slope < 0:
            k_values.append(math.exp(slope))

    return k_values


def skrifa_baseflow_sundurgreiningu(skra, rennsli, baseflow):
    with open(skra, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["date", "qobs_m3_s", "baseflow_m3_s", "quickflow_m3_s"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for (dagur, qobs), bf in zip(rennsli, baseflow):
            writer.writerow(
                {
                    "date": dagur.isoformat(),
                    "qobs_m3_s": f"{qobs:.3f}",
                    "baseflow_m3_s": f"{bf:.3f}",
                    "quickflow_m3_s": f"{qobs - bf:.3f}",
                }
            )


def moving_average(values, window):
    averaged = []
    running_sum = 0.0
    queue = []

    for value in values:
        queue.append(value)
        running_sum += value
        if len(queue) > window:
            running_sum -= queue.pop(0)
        averaged.append(running_sum / len(queue))

    return averaged


def nice_axis_max(value):
    if value <= 0:
        return 1

    magnitude = 10 ** math.floor(math.log10(value))
    normalized = value / magnitude

    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10

    return nice * magnitude


def recession_profile(q, segments, max_days=10, min_segments=10):
    by_day = {}
    for start, end in segments:
        if q[start] <= 0:
            continue

        for offset, index in enumerate(range(start, min(end, start + max_days) + 1)):
            by_day.setdefault(offset, []).append(q[index] / q[start])

    profile = []
    counts = {}
    for offset in range(max_days + 1):
        values = by_day.get(offset, [])
        counts[offset] = len(values)
        if len(values) >= min_segments:
            profile.append((offset, median(values)))

    return profile, counts


def teikna_baseflow_og_recession(dagar, q, baseflow, segments, k_median, bfi, skra):
    width = 1100
    height = 810
    margin_left = 85
    margin_right = 45
    margin_top = 100
    panel_gap = 85
    panel_height = 245
    plot_width = width - margin_left - margin_right

    q_smooth = moving_average(q, 30)
    bf_smooth = moving_average(baseflow, 30)
    x_values = list(range(len(q)))
    y_max = nice_axis_max(max(q_smooth) * 1.08)

    top1 = margin_top
    bottom1 = top1 + panel_height
    top2 = bottom1 + panel_gap
    bottom2 = top2 + panel_height

    def x_to_svg(index):
        return margin_left + (index / (len(q) - 1)) * plot_width

    def y1_to_svg(value):
        return top1 + (1 - value / y_max) * panel_height

    def y2_to_svg(value):
        log_min = math.log(recession_y_min)
        log_max = math.log(1.05)
        log_value = math.log(max(value, recession_y_min))
        return top2 + (1 - (log_value - log_min) / (log_max - log_min)) * panel_height

    def year_index(year):
        target = date(year, 1, 1)
        return min(range(len(dagar)), key=lambda i: abs((dagar[i] - target).days))

    year_ticks = [year for year in range(1995, 2025, 5) if START_DATE.year <= year <= END_DATE.year]
    q_points = " ".join(f"{x_to_svg(i):.2f},{y1_to_svg(value):.2f}" for i, value in zip(x_values, q_smooth))
    bf_points = " ".join(f"{x_to_svg(i):.2f},{y1_to_svg(value):.2f}" for i, value in zip(x_values, bf_smooth))

    profile, profile_counts = recession_profile(q, segments)
    recession_x_max = max(day for day, _ in profile)
    recession_y_min = max(
        0.05,
        min([value for _, value in profile] + [k_median ** recession_x_max]) * 0.9,
    )
    recession_points = " ".join(
        f"{margin_left + (day / recession_x_max) * plot_width:.2f},{y2_to_svg(value):.2f}"
        for day, value in profile
    )
    fitted_points = " ".join(
        f"{margin_left + (day / recession_x_max) * plot_width:.2f},{y2_to_svg(k_median ** day):.2f}"
        for day in (0, recession_x_max)
    )

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        'text { font-family: Arial, sans-serif; fill: #1f2933; }',
        '.axis { stroke: #1f2933; stroke-width: 1.3; }',
        '.grid { stroke: #d7dde3; stroke-width: 1; }',
        '.q { fill: none; stroke: #1f77b4; stroke-width: 2.2; }',
        '.bf { fill: none; stroke: #2ca02c; stroke-width: 2.5; }',
        '.rec { fill: none; stroke: #4b5563; stroke-width: 2.4; }',
        '.fit { fill: none; stroke: #d62728; stroke-width: 2.6; stroke-dasharray: 8 6; }',
        '.legend-line { stroke-width: 3; stroke-linecap: round; }',
        '</style>',
        f'<text x="{width / 2}" y="34" font-size="24" font-weight="700" text-anchor="middle">Grunnrennsli og recession-greining</text>',
        f'<text x="{width / 2}" y="59" font-size="16" text-anchor="middle">{HEITI}, {START_DATE} til {END_DATE}</text>',
        f'<text x="{margin_left}" y="{top1 - 17}" font-size="15" font-weight="700">Baseflow separation, 30 daga hlaupandi meðaltal</text>',
        f'<text x="{width - margin_right}" y="{top1 - 17}" font-size="13" text-anchor="end">BFI = {bfi:.3f}</text>',
    ]

    for tick in year_ticks:
        i = year_index(tick)
        x = x_to_svg(i)
        svg.append(f'<line class="grid" x1="{x:.2f}" y1="{top1}" x2="{x:.2f}" y2="{bottom1}"/>')
        svg.append(f'<text x="{x:.2f}" y="{bottom1 + 24}" font-size="12" text-anchor="middle">{tick}</text>')

    for fraction in (0, 0.25, 0.5, 0.75, 1):
        value = y_max * fraction
        y = y1_to_svg(value)
        svg.append(f'<line class="grid" x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}"/>')
        svg.append(f'<text x="{margin_left - 10}" y="{y + 4:.2f}" font-size="12" text-anchor="end">{value:.0f}</text>')

    svg.append(f'<line class="axis" x1="{margin_left}" y1="{bottom1}" x2="{width - margin_right}" y2="{bottom1}"/>')
    svg.append(f'<line class="axis" x1="{margin_left}" y1="{top1}" x2="{margin_left}" y2="{bottom1}"/>')
    svg.append(f'<polyline class="q" points="{q_points}"/>')
    svg.append(f'<polyline class="bf" points="{bf_points}"/>')
    svg.append(f'<line class="legend-line q" x1="{margin_left}" y1="{bottom1 + 48}" x2="{margin_left + 35}" y2="{bottom1 + 48}"/>')
    svg.append(f'<text x="{margin_left + 45}" y="{bottom1 + 52}" font-size="13">Heildarrennsli</text>')
    svg.append(f'<line class="legend-line bf" x1="{margin_left + 170}" y1="{bottom1 + 48}" x2="{margin_left + 205}" y2="{bottom1 + 48}"/>')
    svg.append(f'<text x="{margin_left + 215}" y="{bottom1 + 52}" font-size="13">Grunnrennsli</text>')

    svg.append(f'<text x="24" y="{(top1 + bottom1) / 2}" font-size="14" text-anchor="middle" transform="rotate(-90 24 {(top1 + bottom1) / 2})">Rennsli (m3/s)</text>')
    svg.append(f'<text x="{margin_left}" y="{top2 - 17}" font-size="15" font-weight="700">Recession constant</text>')
    svg.append(f'<text x="{width - margin_right}" y="{top2 - 17}" font-size="13" text-anchor="end">Median k = {k_median:.3f} á dag</text>')

    day_ticks = list(range(0, recession_x_max + 1, 5))
    if day_ticks[-1] != recession_x_max:
        day_ticks.append(recession_x_max)

    for day in day_ticks:
        x = margin_left + (day / recession_x_max) * plot_width
        svg.append(f'<line class="grid" x1="{x:.2f}" y1="{top2}" x2="{x:.2f}" y2="{bottom2}"/>')
        svg.append(f'<text x="{x:.2f}" y="{bottom2 + 24}" font-size="12" text-anchor="middle">{day}</text>')

    y2_ticks = [value for value in (1.0, 0.9, 0.8, 0.7, 0.6) if value >= recession_y_min]
    lower_tick = round(recession_y_min, 2)
    if lower_tick not in y2_ticks:
        y2_ticks.append(lower_tick)

    for value in y2_ticks:
        y = y2_to_svg(value)
        svg.append(f'<line class="grid" x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}"/>')
        svg.append(f'<text x="{margin_left - 10}" y="{y + 4:.2f}" font-size="12" text-anchor="end">{value:.1f}</text>')

    svg.append(f'<line class="axis" x1="{margin_left}" y1="{bottom2}" x2="{width - margin_right}" y2="{bottom2}"/>')
    svg.append(f'<line class="axis" x1="{margin_left}" y1="{top2}" x2="{margin_left}" y2="{bottom2}"/>')
    svg.append(f'<polyline class="rec" points="{recession_points}"/>')
    svg.append(f'<polyline class="fit" points="{fitted_points}"/>')
    svg.append(f'<text x="{width / 2}" y="{height - 24}" font-size="14" text-anchor="middle">Dagar frá upphafi recession-lotu</text>')
    svg.append(f'<text x="24" y="{(top2 + bottom2) / 2}" font-size="14" text-anchor="middle" transform="rotate(-90 24 {(top2 + bottom2) / 2})">Q / Q0, log-kvarði</text>')
    svg.append(f'<line class="legend-line rec" x1="{margin_left}" y1="{bottom2 + 48}" x2="{margin_left + 35}" y2="{bottom2 + 48}"/>')
    svg.append(f'<text x="{margin_left + 45}" y="{bottom2 + 52}" font-size="13">Miðgildi mældra recession-lota</text>')
    svg.append(f'<line class="legend-line fit" x1="{margin_left + 275}" y1="{bottom2 + 48}" x2="{margin_left + 310}" y2="{bottom2 + 48}"/>')
    svg.append(f'<text x="{margin_left + 320}" y="{bottom2 + 52}" font-size="13">Metin hnignun samkvæmt k</text>')
    svg.append("</svg>")

    with open(skra, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


def prosent(gildi):
    return f"{gildi * 100:.1f}%"


def main():
    rennsli = lesa_rennsli(RUNOFF_FILE)
    dagar = [dagur for dagur, _ in rennsli]
    q = [qobs for _, qobs in rennsli]
    fjoldi_daga_i_timabili = (END_DATE - START_DATE).days + 1
    fjoldi_daga_an_gilds_rennslis = fjoldi_daga_i_timabili - len(q)

    baseflow = ladson_baseflow_filter(q)
    bfi = sum(baseflow) / sum(q)
    lamah_bfi = lesa_lamah_bfi(HYDRO_INDICES_FILE, GAUGE_ID)
    skrifa_baseflow_sundurgreiningu(BASEFLOW_OUTPUT_FILE, rennsli, baseflow)

    segments = recession_segments(q)
    k_values = recession_constant(q, segments)
    k_median = median(k_values)
    k_mean = mean(k_values)
    half_life = math.log(0.5) / math.log(k_median)
    teikna_baseflow_og_recession(dagar, q, baseflow, segments, k_median, bfi, BASEFLOW_SVG_FILE)

    print("Liður 3: Baseflow separation og recession analysis")
    print("-" * 60)
    print(f"Vatnsfall og mælir: {HEITI} (id={GAUGE_ID})")
    print(f"Tímabil: {START_DATE} til {END_DATE}")
    print(f"Fjöldi daga í tímabili: {fjoldi_daga_i_timabili}")
    print(f"Fjöldi gildra rennslisgilda notaður: {len(q)}")
    print(f"Fjöldi daga án gilds qobs sem var sleppt: {fjoldi_daga_an_gilds_rennslis}")
    print(f"Meðalrennsli: {mean(q):.2f} m3/s")
    print()

    print("Baseflow separation")
    print(f"Reiknað BFI með Ladson/Lyne-Hollick filter: {bfi:.3f} ({prosent(bfi)})")
    if lamah_bfi is not None:
        print(
            "Eldri viðmiðun í LamaH-Ice, baseflow_index_ladson "
            f"(1981-2018): {lamah_bfi:.3f} ({prosent(lamah_bfi)})"
        )
    print(f"Sundurgreind röð vistuð í: {BASEFLOW_OUTPUT_FILE}")
    print(f"Mynd vistuð í: {BASEFLOW_SVG_FILE}")
    print()

    print("Recession analysis")
    print(f"Fjöldi recession-lota, minnst 5 dagar: {len(segments)}")
    print(f"Median recession constant, k: {k_median:.3f} á dag")
    print(f"Meðaltal recession constant, k: {k_mean:.3f} á dag")
    print(f"Helmingunartími rennslis í dæmigerðri recession-lotu: {half_life:.1f} dagar")
    print()

    print("Túlkun")
    print(
        "BFI er hátt, um 0.86-0.88. Það bendir til þess að stór hluti rennslis "
        "komi sem hægfara grunnrennsli eða seinkað framlag úr vatnsgeymum "
        "vatnasviðsins, frekar en eingöngu sem snöggt yfirborðsafrennsli."
    )
    print(
        "Recession constant k er einnig hátt. Þegar k er nálægt 1 fellur rennsli "
        "hægt á þurrkatímum, sem bendir til sterkrar miðlunar og langrar tæmingar "
        "úr grunnvatni, jarðlögum, vötnum, votlendi eða jökul-/snjógeymslu."
    )
    print(
        "Jarðfræðigögnin fyrir id=37 sýna m.a. töluvert hlutfall ungs/basísks "
        "gosbergs og hreyfanlegra setlaga, auk umtalsverðs jökulhlutfalls. "
        "Gropið hraun og laus jarðlög geta aukið írennsli og grunnvatnsmiðlun, "
        "sem samræmist háu BFI. Jöklar og snjór geta líka jafnað rennsli yfir "
        "sumar og haust og styrkt hægfara recession-mynstur."
    )


if __name__ == "__main__":
    main()
