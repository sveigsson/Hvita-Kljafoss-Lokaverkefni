import csv
import math
from datetime import date
from statistics import mean, median


GAUGE_ID = 37
HEITI = "Hvítá við Kljáfoss"
RUNOFF_FILE = f"lamah_ice/D_gauges/2_timeseries/daily_filtered/ID_{GAUGE_ID}.csv"
CATCHMENT_ATTRIBUTES_FILE = "lamah_ice/A_basins_total_upstrm/1_attributes/Catchment_attributes.csv"
FDC_OUTPUT_FILE = "lidur_5_langaeislina_kljafoss.svg"
START_DATE = date(1993, 10, 1)
END_DATE = date(2023, 9, 30)


def lesa_rennsli(skra):
    rennsli = []
    total_rows = 0
    missing_rows = 0

    with open(skra, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            dagur = date(int(row["YYYY"]), int(row["MM"]), int(row["DD"]))
            if not (START_DATE <= dagur <= END_DATE):
                continue

            total_rows += 1
            qobs = row["qobs"].strip()

            if not qobs:
                missing_rows += 1
                continue

            q = float(qobs)
            if q < 0:
                missing_rows += 1
                continue

            rennsli.append((dagur, q))

    return rennsli, total_rows, missing_rows


def lesa_vatnasvidseiginleika(skra, gauge_id):
    with open(skra, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if int(row["id"]) == gauge_id:
                return {
                    "glac_fra": float(row["glac_fra"]),
                    "lake_fra": float(row["lake_fra"]),
                    "wetl_fra": float(row["wetl_fra"]),
                    "frac_snow": float(row["frac_snow"]),
                }

    return None


def percentile(gildi, p):
    """Linear interpolation percentile, p fra 0 til 100."""
    rodud = sorted(gildi)
    if not rodud:
        raise ValueError("Engin rennslisgildi fundust.")

    stadsetning = (len(rodud) - 1) * p / 100
    neðra = int(stadsetning)
    efra = min(neðra + 1, len(rodud) - 1)
    hlutfall = stadsetning - neðra

    return rodud[neðra] + (rodud[efra] - rodud[neðra]) * hlutfall


def reikna_langaeislinu(q):
    q_lækkandi = sorted(q, reverse=True)
    n = len(q_lækkandi)
    exceedance = [(i + 1) / (n + 1) * 100 for i in range(n)]

    return exceedance, q_lækkandi


def ladson_baseflow_filter(q, alpha=0.98):
    if not q:
        return []

    quickflow = [0.0] * len(q)
    baseflow = [q[0]]

    for i in range(1, len(q)):
        quickflow[i] = alpha * quickflow[i - 1] + ((1 + alpha) / 2) * (q[i] - q[i - 1])
        quickflow[i] = max(0.0, min(quickflow[i], q[i]))
        baseflow.append(q[i] - quickflow[i])

    return baseflow


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


def teikna_langaeislinu(exceedance, q_lækkandi, q5, q50, q95, skra):
    width = 1000
    height = 650
    margin_left = 95
    margin_right = 35
    margin_top = 75
    margin_bottom = 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    y_max = nice_axis_max(max(q_lækkandi) * 1.05)

    def x_to_svg(x):
        return margin_left + (x / 100) * plot_width

    def y_to_svg(y):
        return margin_top + (1 - y / y_max) * plot_height

    points = " ".join(
        f"{x_to_svg(x):.2f},{y_to_svg(y):.2f}"
        for x, y in zip(exceedance, q_lækkandi)
    )

    x_ticks = [0, 20, 40, 60, 80, 100]
    y_step = y_max / 5
    y_ticks = [i * y_step for i in range(6)]
    markerar = [(5, q5, "Q5"), (50, q50, "Q50"), (95, q95, "Q95")]

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        'text { font-family: Arial, sans-serif; fill: #1f2933; }',
        '.axis { stroke: #1f2933; stroke-width: 1.5; }',
        '.grid { stroke: #d7dde3; stroke-width: 1; }',
        '.guide { stroke: #9aa5b1; stroke-width: 1; stroke-dasharray: 6 6; }',
        '.curve { fill: none; stroke: #1f77b4; stroke-width: 3; stroke-linejoin: round; stroke-linecap: round; }',
        '.marker { fill: #d62728; stroke: white; stroke-width: 2; }',
        '</style>',
        f'<text x="{width / 2}" y="35" font-size="24" font-weight="700" text-anchor="middle">Langæislína rennslis</text>',
        f'<text x="{width / 2}" y="61" font-size="16" text-anchor="middle">{HEITI}, {START_DATE} til {END_DATE}</text>',
    ]

    for tick in x_ticks:
        x = x_to_svg(tick)
        svg.append(f'<line class="grid" x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" y2="{height - margin_bottom}"/>')
        svg.append(f'<text x="{x:.2f}" y="{height - margin_bottom + 28}" font-size="13" text-anchor="middle">{tick}</text>')

    for tick in y_ticks:
        y = y_to_svg(tick)
        svg.append(f'<line class="grid" x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}"/>')
        svg.append(f'<text x="{margin_left - 12}" y="{y + 4:.2f}" font-size="13" text-anchor="end">{tick:.0f}</text>')

    svg.append(f'<line class="axis" x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}"/>')
    svg.append(f'<line class="axis" x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}"/>')
    svg.append(f'<polyline class="curve" points="{points}"/>')

    for x, y, label in markerar:
        sx = x_to_svg(x)
        sy = y_to_svg(y)
        text_anchor = "start"
        label_x = sx + 12
        if x > 85:
            text_anchor = "end"
            label_x = sx - 12
        svg.append(f'<line class="guide" x1="{sx:.2f}" y1="{margin_top}" x2="{sx:.2f}" y2="{height - margin_bottom}"/>')
        svg.append(f'<line class="guide" x1="{margin_left}" y1="{sy:.2f}" x2="{width - margin_right}" y2="{sy:.2f}"/>')
        svg.append(f'<circle class="marker" cx="{sx:.2f}" cy="{sy:.2f}" r="6"/>')
        svg.append(
            f'<text x="{label_x:.2f}" y="{sy - 10:.2f}" font-size="14" font-weight="700" '
            f'text-anchor="{text_anchor}">{label} = {y:.1f} m3/s</text>'
        )

    svg.append(f'<text x="{width / 2}" y="{height - 25}" font-size="15" text-anchor="middle">Hlutfall tíma sem rennsli er jafnt eða meira (%)</text>')
    svg.append(
        f'<text x="24" y="{height / 2}" font-size="15" text-anchor="middle" '
        'transform="rotate(-90 24 325)">Daglegt rennsli, Q (m3/s)</text>'
    )
    svg.append("</svg>")

    with open(skra, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


def prosent(gildi):
    return f"{gildi * 100:.1f}%"


def main():
    rennsli, total_rows, missing_rows = lesa_rennsli(RUNOFF_FILE)
    dagar = [dagur for dagur, _ in rennsli]
    q = [qobs for _, qobs in rennsli]

    q5 = percentile(q, 95)
    q50 = percentile(q, 50)
    q95 = percentile(q, 5)
    q5_q95_ratio = q5 / q95
    baseflow = ladson_baseflow_filter(q)
    bfi = sum(baseflow) / sum(q)

    exceedance, q_lækkandi = reikna_langaeislinu(q)
    teikna_langaeislinu(exceedance, q_lækkandi, q5, q50, q95, FDC_OUTPUT_FILE)

    eiginleikar = lesa_vatnasvidseiginleika(CATCHMENT_ATTRIBUTES_FILE, GAUGE_ID)

    print("Liður 5: Langaeislina rennslis / Flow duration curve")
    print("-" * 66)
    print(f"Vatnsfall og mælir: {HEITI} (id={GAUGE_ID})")
    print(f"Tímabil mælinga: {START_DATE} til {END_DATE}")
    print(f"Fjöldi raða í mælitíma: {total_rows}")
    print(f"Fjöldi gildra daglegra rennslisgilda notaður: {len(q)}")
    print(f"Fjöldi daga án gilds qobs sem var sleppt: {missing_rows}")
    print(f"Meðalrennsli: {mean(q):.2f} m3/s")
    print(f"Miðgildi rennslis: {median(q):.2f} m3/s")
    print()

    print("Einkennandi rennsli úr langaeislínu")
    print(f"Q5  (hárennsli, rennsli sem er náð eða farið yfir 5% tímans):  {q5:.2f} m3/s")
    print(f"Q50 (miðgildi, náð eða farið yfir 50% tímans):                {q50:.2f} m3/s")
    print(f"Q95 (lágrennsli, náð eða farið yfir 95% tímans):              {q95:.2f} m3/s")
    print(f"Q5/Q95 hlutfall: {q5_q95_ratio:.1f}")
    print(f"Mynd vistuð í: {FDC_OUTPUT_FILE}")
    print()

    print("Túlkun")
    print(
        "Langaeislínan fellur tiltölulega jafnt frekar en að vera mjög brött yfir "
        f"allan ferilinn. Q5/Q95 hlutfallið er {q5_q95_ratio:.1f}, sem þýðir að hárennslisdagar "
        "eru tæplega tvöfalt vatnsmeiri en dæmigert lágrennsli. Rennslið er því "
        "sveiflukennt að einhverju marki, en samanborið við mjög brött vatnsföll "
        "bendir ferillinn til tiltölulega stöðugs og vel miðlaðs rennslis."
    )
    print(
        "Q50 lýsir dæmigerðu daglegu rennsli, Q5 lýsir vatnsmiklum dögum sem "
        "tengjast líklega úrkomu, leysingu eða jökulbráðnun, og Q95 lýsir "
        "grunnástandi þegar rennsli er lágt en hverfur ekki."
    )

    if eiginleikar is not None:
        print(
            "Vatnasviðseiginleikar styðja þessa túlkun: jökulhlutfall er "
            f"{prosent(eiginleikar['glac_fra'])}, stöðuvatnahlutfall "
            f"{prosent(eiginleikar['lake_fra'])}, votlendi "
            f"{prosent(eiginleikar['wetl_fra'])}, snjóhlutfall úrkomu "
            f"{prosent(eiginleikar['frac_snow'])} og reiknað baseflow-index "
            f"fyrir tímabilið er {bfi:.3f}."
        )

    print(
        "Stöðuvötn og votlendi geta dempað snögg rennslisviðbrögð, en hér er "
        "stöðuvatnahlutfallið lítið. Jöklar og snjór geta bæði aukið sumar- og "
        "leysingarrennsli og dreift vatni yfir lengri tíma. Hátt baseflow-index "
        "bendir líka til þess að grunnvatn og gegndræp jarðlög haldi uppi "
        "lágrennsli og geri neðri hluta ferilsins flatari en ella."
    )


if __name__ == "__main__":
    main()
