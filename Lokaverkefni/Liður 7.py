import csv
import math
from collections import defaultdict
from datetime import date
from statistics import mean, median


GAUGE_ID = 37
HEITI = "Hvítá við Kljáfoss"
RUNOFF_FILE = f"lamah_ice/D_gauges/2_timeseries/daily_filtered/ID_{GAUGE_ID}.csv"
SUMMARY_OUTPUT_FILE = "lidur_7_leitnigreining_kljafoss.csv"
TREND_SVG_FILE = "lidur_7_leitnigreining_kljafoss.svg"
MIN_COVERAGE = 0.80
START_DATE = date(1993, 10, 1)
END_DATE = date(2023, 9, 30)

SEASONS = {
    "Vor": (3, 4, 5),
    "Sumar": (6, 7, 8),
    "Haust": (9, 10, 11),
    "Vetur": (12, 1, 2),
}


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


def dagar_i_ari(ar):
    return 366 if (ar % 4 == 0 and (ar % 100 != 0 or ar % 400 == 0)) else 365


def season_year(dagur):
    if dagur.month == 12:
        return dagur.year + 1
    return dagur.year


def water_year(dagur):
    if dagur.month >= 10:
        return dagur.year + 1
    return dagur.year


def expected_days_in_season(ar, season):
    if season == "Vor":
        return 31 + 30 + 31
    if season == "Sumar":
        return 30 + 31 + 31
    if season == "Haust":
        return 30 + 31 + 30
    if season == "Vetur":
        return 31 + (29 if dagar_i_ari(ar) == 366 else 28) + 31
    raise ValueError(f"Oþekkt arstið: {season}")


def aggregate_annual_mean(rennsli):
    by_year = defaultdict(list)
    for dagur, q in rennsli:
        by_year[water_year(dagur)].append(q)

    series = []
    for ar in sorted(by_year):
        coverage = len(by_year[ar]) / dagar_i_ari(ar)
        if coverage >= MIN_COVERAGE:
            series.append((ar, mean(by_year[ar]), coverage, len(by_year[ar])))

    return series


def aggregate_seasonal_mean(rennsli):
    by_season = {season: defaultdict(list) for season in SEASONS}

    for dagur, q in rennsli:
        for season, months in SEASONS.items():
            if dagur.month in months:
                by_season[season][season_year(dagur)].append(q)
                break

    seasonal_series = {}
    for season in SEASONS:
        rows = []
        expected = None
        for ar in sorted(by_season[season]):
            expected = expected_days_in_season(ar, season)
            coverage = len(by_season[season][ar]) / expected
            if coverage >= MIN_COVERAGE:
                rows.append((ar, mean(by_season[season][ar]), coverage, len(by_season[season][ar])))
        seasonal_series[season] = rows

    return seasonal_series


def sign(x):
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def average_ranks(values):
    indexed = sorted((value, i) for i, value in enumerate(values))
    ranks = [0.0] * len(values)
    i = 0

    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][0] == indexed[i][0]:
            j += 1

        avg_rank = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            ranks[indexed[k][1]] = avg_rank
        i = j + 1

    return ranks


def autocorrelation(values, lag):
    n = len(values)
    avg = mean(values)
    denominator = sum((value - avg) ** 2 for value in values)
    if denominator == 0:
        return 0.0

    numerator = sum((values[i] - avg) * (values[i + lag] - avg) for i in range(n - lag))
    return numerator / denominator


def normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def mann_kendall_s(values):
    s = 0
    for i in range(len(values) - 1):
        for j in range(i + 1, len(values)):
            s += sign(values[j] - values[i])
    return s


def tied_groups(values):
    counts = defaultdict(int)
    for value in values:
        counts[value] += 1
    return [count for count in counts.values() if count > 1]


def original_variance_s(values):
    n = len(values)
    tie_term = sum(t * (t - 1) * (2 * t + 5) for t in tied_groups(values))
    return (n * (n - 1) * (2 * n + 5) - tie_term) / 18


def modified_mann_kendall(values):
    """Hamed og Ramachandra Rao (1998) variance correction fyrir autocorrelation."""
    n = len(values)
    if n < 4:
        return None

    s = mann_kendall_s(values)
    var_s = original_variance_s(values)
    ranks = average_ranks(values)
    significant_limit = 1.96 / math.sqrt(n)
    significant_autocorr = []

    for lag in range(1, n):
        rho = autocorrelation(ranks, lag)
        if abs(rho) > significant_limit:
            significant_autocorr.append((lag, rho))

    correction_sum = sum(
        (n - lag) * (n - lag - 1) * (n - lag - 2) * rho
        for lag, rho in significant_autocorr
    )
    correction_factor = 1 + (2 / (n * (n - 1) * (n - 2))) * correction_sum
    correction_factor = max(correction_factor, 1.0)
    modified_var_s = var_s * correction_factor

    if s > 0:
        z = (s - 1) / math.sqrt(modified_var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(modified_var_s)
    else:
        z = 0.0

    p_value = 2 * (1 - normal_cdf(abs(z)))

    return {
        "s": s,
        "z": z,
        "p_value": p_value,
        "correction_factor": correction_factor,
        "significant_lags": significant_autocorr,
    }


def theil_sen(x, y):
    slopes = []
    for i in range(len(x) - 1):
        for j in range(i + 1, len(x)):
            if x[j] != x[i]:
                slopes.append((y[j] - y[i]) / (x[j] - x[i]))

    slope = median(slopes)
    intercepts = [yi - slope * xi for xi, yi in zip(x, y)]
    intercept = median(intercepts)

    return slope, intercept


def trend_result(name, series):
    x = [row[0] for row in series]
    y = [row[1] for row in series]
    slope, intercept = theil_sen(x, y)
    mk = modified_mann_kendall(y)
    percent_per_decade = (slope * 10 / mean(y)) * 100

    return {
        "name": name,
        "n": len(series),
        "start_year": x[0],
        "end_year": x[-1],
        "mean_q": mean(y),
        "slope": slope,
        "slope_decade": slope * 10,
        "percent_per_decade": percent_per_decade,
        "intercept": intercept,
        "p_value": mk["p_value"],
        "z": mk["z"],
        "significant": mk["p_value"] < 0.05,
        "direction": "aukning" if slope > 0 else "minnkun" if slope < 0 else "engin breyting",
        "correction_factor": mk["correction_factor"],
        "significant_lags": ", ".join(str(lag) for lag, _ in mk["significant_lags"]) or "-",
        "series": series,
    }


def write_summary(results, skra):
    fieldnames = [
        "flokkur",
        "n",
        "upphafsar",
        "lokaar",
        "medalrennsli_m3_s",
        "theil_sen_m3_s_per_year",
        "theil_sen_m3_s_per_decade",
        "prosent_per_decade",
        "mk_z",
        "mk_p",
        "marktakt_p_0_05",
        "stefna",
        "variance_correction_factor",
        "significant_autocorrelation_lags",
    ]

    with open(skra, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "flokkur": result["name"],
                    "n": result["n"],
                    "upphafsar": result["start_year"],
                    "lokaar": result["end_year"],
                    "medalrennsli_m3_s": f"{result['mean_q']:.3f}",
                    "theil_sen_m3_s_per_year": f"{result['slope']:.5f}",
                    "theil_sen_m3_s_per_decade": f"{result['slope_decade']:.3f}",
                    "prosent_per_decade": f"{result['percent_per_decade']:.2f}",
                    "mk_z": f"{result['z']:.3f}",
                    "mk_p": f"{result['p_value']:.4f}",
                    "marktakt_p_0_05": "ja" if result["significant"] else "nei",
                    "stefna": result["direction"],
                    "variance_correction_factor": f"{result['correction_factor']:.3f}",
                    "significant_autocorrelation_lags": result["significant_lags"],
                }
            )


def svg_polyline(series, slope, intercept, x_to_svg, y_to_svg):
    points = " ".join(f"{x_to_svg(x):.2f},{y_to_svg(y):.2f}" for x, y, _, _ in series)
    years = [row[0] for row in series]
    trend_points = " ".join(
        f"{x_to_svg(x):.2f},{y_to_svg(intercept + slope * x):.2f}"
        for x in (min(years), max(years))
    )
    return points, trend_points


def write_trend_svg(results, skra):
    result = results[0]
    series = result["series"]
    width = 1000
    height = 620
    margin_left = 85
    margin_right = 45
    margin_top = 85
    margin_bottom = 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    years = [row[0] for row in series]
    values = [row[1] for row in series]
    x_min = min(years)
    x_max = max(years)
    y_min = min(values) * 0.95
    y_max = max(values) * 1.05
    if y_max == y_min:
        y_max += 1

    def x_to_svg(x):
        return margin_left + ((x - x_min) / (x_max - x_min)) * plot_width

    def y_to_svg(y):
        return margin_top + (1 - (y - y_min) / (y_max - y_min)) * plot_height

    trend_points = " ".join(
        f"{x_to_svg(x):.2f},{y_to_svg(result['intercept'] + result['slope'] * x):.2f}"
        for x in (x_min, x_max)
    )
    significant_text = "marktæk" if result["significant"] else "ekki marktæk"

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        'text { font-family: Arial, sans-serif; fill: #1f2933; }',
        '.axis { stroke: #1f2933; stroke-width: 1.4; }',
        '.grid { stroke: #d7dde3; stroke-width: 1; }',
        '.point { fill: #1f77b4; stroke: white; stroke-width: 1.5; }',
        '.legend-point { fill: #1f77b4; stroke: white; stroke-width: 1.5; }',
        '.trend { stroke: #d62728; stroke-width: 3; stroke-dasharray: 8 6; }',
        '</style>',
        f'<text x="{width / 2}" y="34" font-size="24" font-weight="700" text-anchor="middle">Leitnigreining ársmeðalrennslis</text>',
        f'<text x="{width / 2}" y="59" font-size="16" text-anchor="middle">{HEITI}, {START_DATE} til {END_DATE}</text>',
    ]

    for tick in range(((x_min + 4) // 5) * 5, x_max + 1, 5):
        x = x_to_svg(tick)
        svg.append(f'<line class="grid" x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" y2="{height - margin_bottom}"/>')
        svg.append(f'<text x="{x:.2f}" y="{height - margin_bottom + 26}" font-size="12" text-anchor="middle">{tick}</text>')

    for fraction in (0, 0.25, 0.5, 0.75, 1):
        y_value = y_min + fraction * (y_max - y_min)
        y = y_to_svg(y_value)
        svg.append(f'<line class="grid" x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}"/>')
        svg.append(f'<text x="{margin_left - 10}" y="{y + 4:.2f}" font-size="12" text-anchor="end">{y_value:.0f}</text>')

    svg.append(f'<line class="axis" x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}"/>')
    svg.append(f'<line class="axis" x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}"/>')
    svg.append(f'<polyline class="trend" points="{trend_points}"/>')

    for year, value, _, _ in series:
        svg.append(f'<circle class="point" cx="{x_to_svg(year):.2f}" cy="{y_to_svg(value):.2f}" r="5"/>')

    svg.append(
        f'<text x="24" y="{height / 2}" font-size="15" text-anchor="middle" '
        f'transform="rotate(-90 24 {height / 2})">Meðalrennsli (m3/s)</text>'
    )
    svg.append(f'<text x="{width / 2}" y="{height - 28}" font-size="15" text-anchor="middle">Vatnsár</text>')
    svg.append(f'<circle class="legend-point" cx="{margin_left}" cy="{height - 50}" r="5"/>')
    svg.append(f'<text x="{margin_left + 14}" y="{height - 46}" font-size="13">Ársmeðalrennsli</text>')
    svg.append(f'<line class="trend" x1="{margin_left + 160}" y1="{height - 50}" x2="{margin_left + 200}" y2="{height - 50}"/>')
    svg.append(f'<text x="{margin_left + 212}" y="{height - 46}" font-size="13">Theil-Sen leitnilína</text>')
    svg.append("</svg>")

    with open(skra, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


def format_p(p_value):
    return "<0.001" if p_value < 0.001 else f"{p_value:.3f}"


def print_result(result):
    significant = "marktæk" if result["significant"] else "ekki marktæk"
    print(
        f"{result['name']:<8} "
        f"Theil-Sen: {result['slope_decade']:+6.2f} m3/s/áratug "
        f"({result['percent_per_decade']:+5.2f}%/áratug), "
        f"p={format_p(result['p_value'])}, {significant}, "
        f"stefna: {result['direction']}"
    )


def main():
    rennsli, total_rows, missing_rows = lesa_rennsli(RUNOFF_FILE)
    annual = aggregate_annual_mean(rennsli)
    seasonal = aggregate_seasonal_mean(rennsli)

    results = [trend_result("Vatnsár", annual)]
    for season in ("Vor", "Sumar", "Haust", "Vetur"):
        results.append(trend_result(season, seasonal[season]))

    write_summary(results, SUMMARY_OUTPUT_FILE)
    write_trend_svg(results, TREND_SVG_FILE)

    dagar = [dagur for dagur, _ in rennsli]
    print("Liður 7: Leitnigreining rennslis")
    print("-" * 66)
    print(f"Vatnsfall og mælir: {HEITI} (id={GAUGE_ID})")
    print(f"Tímabil mælinga: {START_DATE} til {END_DATE}")
    print(f"Fjöldi raða í mælitíma: {total_rows}")
    print(f"Fjöldi gildra daglegra rennslisgilda notaður: {len(rennsli)}")
    print(f"Fjöldi daga án gilds qobs sem var sleppt: {missing_rows}")
    print(f"Lágmarksgagnaþekja fyrir ár/árstíð: {MIN_COVERAGE * 100:.0f}%")
    print()

    print("Theil-Sen leitni og modified Mann-Kendall marktækni")
    for result in results:
        print_result(result)
    print()

    significant_results = [result for result in results if result["significant"]]
    if significant_results:
        strongest = max(significant_results, key=lambda item: abs(item["percent_per_decade"]))
        print("Túlkun")
        print(
            "Niðurstöðurnar sýna tölfræðilega marktæka leitni í a.m.k. einum flokki "
            "við p<0.05. Sterkasta hlutfallslega marktæka breytingin er í "
            f"{strongest['name'].lower()}, þar sem rennsli sýnir {strongest['direction']} "
            f"um {strongest['slope_decade']:+.2f} m3/s á áratug "
            f"({strongest['percent_per_decade']:+.2f}% á áratug)."
        )
    else:
        print("Túlkun")
        print(
            "Engin árleg eða árstíðabundin leitni er tölfræðilega marktæk við p<0.05 "
            "samkvæmt modified Mann-Kendall prófinu. Theil-Sen hallarnir sýna þó "
            "stefnu breytinga, en óvissan er nógu mikil til að ekki sé hægt að "
            "fullyrða um marktæka aukningu eða minnkun."
        )

    annual_result = results[0]
    print(
        f"Á ársgrunni er hallinn {annual_result['slope_decade']:+.2f} m3/s á áratug "
        f"og p-gildið {format_p(annual_result['p_value'])}, þannig árlega leitnin er "
        f"{'marktæk' if annual_result['significant'] else 'ekki marktæk'}."
    )
    print(
        "Árstíðaniðurstöðurnar má túlka sem vísbendingu um hvar breytingar koma helst "
        "fram innan ársins. Jöklar og snjóbráðnun geta haft mest áhrif á sumar og "
        "haust, en grunnvatnsmiðlun getur dempað leitni í vetrar- og lágrennsli. "
        "Modified Mann-Kendall leiðréttir dreifni prófsins fyrir raðfylgni, sem er "
        "mikilvægt í vatnafræðilegum tímaraðum."
    )
    print()
    print(f"Samantekt vistuð í: {SUMMARY_OUTPUT_FILE}")
    print(f"Mynd vistuð í: {TREND_SVG_FILE}")


if __name__ == "__main__":
    main()
