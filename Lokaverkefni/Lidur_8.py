"""
Lið 8 - Greining á rennslisatburði
Vatnsfall: Hvítá, Kljáfoss (ID 37)
Tímabil:   Einn af 5 hæstu flóðum 1993–2023

Markmið: Tengja saman úrkomu, hitastig og rennslissvörun fyrir raunverulegan atburð.
Glugginn er 15 dagar fyrir topp og 25 dagar eftir topp (40 dagar samtals).

Mælikvarðar sem merktir eru á mynd:
  - Time-to-peak:          Frá upphafi rennslisaukningar að Qmax
  - Recession time:        Frá Qpeak þangað til rennsli snýr aftur að grunngildi
  - Excess rain release:   Frá síðasta rigningardegi þangað til rennsli snýr aftur
                           að grunngildi
"""

import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ---------------------------------------------------------------------------
# Stillingar
# ---------------------------------------------------------------------------
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(SCRIPT_DIR, "lamah_ice")
GAUGE_ID      = 37
START         = "1993-10-01"
END           = "2023-09-30"

WINDOW_BEFORE = 15    # dagar fyrir topp
WINDOW_AFTER  = 25    # dagar eftir topp
BASELINE_DAYS = 5     # fyrstu N dagar í glugga til að meta grunnrennsli
RETURN_TOL    = 1.05  # rennsli telst „aftur á grunngildi" þegar Q <= Q_base * 1.05
RAIN_THRESH   = 0.5   # mm/dag – lágmark til að dagur teljist rigningardagur

FIG_OUT = os.path.join(SCRIPT_DIR, "figures", "Lidur_8_atburdur.png")

# ---------------------------------------------------------------------------
# 1. Les og undirbý gögn
# ---------------------------------------------------------------------------
gauge_path = os.path.join(DATA_DIR, "D_gauges", "2_timeseries", "daily",
                          f"ID_{GAUGE_ID}.csv")
met_path   = os.path.join(DATA_DIR, "A_basins_total_upstrm", "2_timeseries",
                          "daily", "meteorological_data", f"ID_{GAUGE_ID}.csv")

q_raw = pd.read_csv(gauge_path, sep=";")
m_raw = pd.read_csv(met_path,   sep=";")

def make_date(df):
    df = df.copy()
    df["date"] = pd.to_datetime(
        df[["YYYY", "MM", "DD"]].rename(
            columns={"YYYY": "year", "MM": "month", "DD": "day"}
        )
    )
    return df

q = make_date(q_raw)
m = make_date(m_raw)

q = q[(q["date"] >= START) & (q["date"] <= END)].copy()
m = m[(m["date"] >= START) & (m["date"] <= END)].copy()

# Sameina í eitt DataFrame
df = m[["date", "MM", "YYYY", "prec_carra", "2m_temp_carra"]].copy()
df = df.merge(q[["date", "qobs"]], on="date", how="inner")
df = df.rename(columns={"prec_carra": "P", "2m_temp_carra": "T", "qobs": "Q"})
df = df.sort_values("date").reset_index(drop=True)

# ---------------------------------------------------------------------------
# 2. Finna 5 hæstu flóðin (annual peaks)
# ---------------------------------------------------------------------------
df["vatnsár"] = df["date"].apply(lambda d: d.year if d.month >= 10 else d.year - 1)
peak_idx  = df.groupby("vatnsár")["Q"].idxmax()
peaks_df  = df.loc[peak_idx, ["date", "Q", "vatnsár"]].copy()
peaks_df  = peaks_df.sort_values("Q", ascending=False).reset_index(drop=True)

print("=" * 55)
print("LIÐ 8 – GREINING Á RENNSLISATBURÐI")
print("=" * 55)
print("\nTop 5 flóð (annual peaks):")
for i, row in peaks_df.head(5).iterrows():
    print(f"  {i+1}. {row['date'].date()}  Q = {row['Q']:.1f} m³/s")

# ---------------------------------------------------------------------------
# 3. Velja atburð – stærsta flóðið
# ---------------------------------------------------------------------------
event_row = peaks_df.iloc[0]
peak_date = event_row["date"]
peak_Q    = event_row["Q"]

print(f"\nValinn atburður: {peak_date.date()}  Qmax = {peak_Q:.1f} m³/s")

# Sía í gluggann
win_start = peak_date - pd.Timedelta(days=WINDOW_BEFORE)
win_end   = peak_date + pd.Timedelta(days=WINDOW_AFTER)
ev = df[(df["date"] >= win_start) & (df["date"] <= win_end)].copy().reset_index(drop=True)

# ---------------------------------------------------------------------------
# 4. Reikna mælikvarðar
# ---------------------------------------------------------------------------

# Grunnrennsli: meðal Q í fyrstu BASELINE_DAYS dögum gluggans
# Q_thresh = Q_base * 1.05 = "aftur á grunngildi" (5% vikmörk frá Q_base)
Q_base   = ev["Q"].iloc[:BASELINE_DAYS].mean()
Q_thresh = Q_base * RETURN_TOL

print(f"\nGrunnrennsli  Q_base   = {Q_base:.1f} m³/s")
print(f"Þröskuldur    Q_thresh = {Q_thresh:.1f} m³/s  (Q_base × {RETURN_TOL}, ~5% vikmörk)")

# Dagsetning og staðsetning topps í glugga
peak_i      = ev["Q"].idxmax()
peak_date_e = ev.loc[peak_i, "date"]

# --- Time-to-peak ---
# Leitum aftur frá toppnum að síðasta degi þar sem Q <= Q_thresh
before_peak = ev.loc[:peak_i]
candidates  = before_peak[before_peak["Q"] <= Q_thresh]
rise_date   = candidates.iloc[-1]["date"] if len(candidates) > 0 else ev.iloc[0]["date"]
time_to_peak = (peak_date_e - rise_date).days

# --- Recession time ---
# Leitum frá toppnum að fyrsta degi þar sem Q <= Q_thresh
after_peak         = ev.loc[peak_i:]
rec_candidates     = after_peak[after_peak["Q"] <= Q_thresh]
recession_end_date = rec_candidates.iloc[0]["date"] if len(rec_candidates) > 0 else ev.iloc[-1]["date"]
recession_time     = (recession_end_date - peak_date_e).days

# --- Excess rain release time ---
# Byrjar þegar stóri rigningaratburðurinn er búinn: peak + 3 dagar
# Endar þegar rennsli snýr aftur að grunngildi: recession_end_date
excess_rain_start = peak_date_e + pd.Timedelta(days=3)
excess_rain_time  = (recession_end_date - excess_rain_start).days

print(f"\nTime-to-peak:          {time_to_peak} dagar  ({rise_date.date()} → {peak_date_e.date()})")
print(f"Recession time:        {recession_time} dagar  ({peak_date_e.date()} → {recession_end_date.date()})")
print(f"Excess rain release:   {excess_rain_time} dagar  ({excess_rain_start.date()} → {recession_end_date.date()})")

# ---------------------------------------------------------------------------
# 5. Mynd
# ---------------------------------------------------------------------------
os.makedirs(os.path.join(SCRIPT_DIR, "figures"), exist_ok=True)

fig, axes = plt.subplots(3, 1, figsize=(13, 11), sharex=True,
                         gridspec_kw={"height_ratios": [3, 2, 2]})
fig.suptitle(
    f"Rennslisatburður – Hvítá, Kljáfoss (ID 37)\n"
    f"Atburður: {peak_date_e.strftime('%d. %B %Y')}  |  "
    f"Qmax = {peak_Q:.0f} m³/s  |  "
    f"Glugginn: {WINDOW_BEFORE} d fyrir – {WINDOW_AFTER} d eftir topp",
    fontsize=12, fontweight="bold", y=0.99
)

dates = ev["date"].values

# ── Efri hluti: Rennsli Q ──────────────────────────────────────────────────
ax1 = axes[0]
ax1.plot(dates, ev["Q"], color="#2E6DA4", linewidth=2.5, label="Q (m³/s)", zorder=4)
ax1.axhline(Q_base,   color="gray",      linestyle=":",  linewidth=1.2,
            label=f"Q_base = {Q_base:.0f} m³/s")
ax1.axhline(Q_thresh, color="lightgray", linestyle="--", linewidth=1.0,
            label=f"Q_thresh = {Q_thresh:.0f} m³/s")

# Toppmerki
ax1.scatter([peak_date_e], [peak_Q], color="#E84C4C", zorder=6, s=90,
            label=f"Qmax = {peak_Q:.0f} m³/s")

# Lóðréttar línur við lykilstígar
for d, c, ls in [(rise_date,         "#555555", ":"),
                 (peak_date_e,       "#E84C4C", "--"),
                 (recession_end_date,"#2CA02C", ":")]:
    ax1.axvline(d, color=c, linestyle=ls, linewidth=1.3, alpha=0.8, zorder=3)

# Time-to-peak ör
y_ttp = peak_Q * 0.80
ax1.annotate(
    "", xy=(peak_date_e, y_ttp), xytext=(rise_date, y_ttp),
    arrowprops=dict(arrowstyle="<->", color="#555555", lw=1.5)
)
ax1.text(
    rise_date + (peak_date_e - rise_date) / 2, y_ttp * 1.04,
    f"Time-to-peak: {time_to_peak} d",
    ha="center", va="bottom", fontsize=9, color="#555555",
    bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, ec="none")
)

# Recession ör
y_rec = peak_Q * 0.45
ax1.annotate(
    "", xy=(recession_end_date, y_rec), xytext=(peak_date_e, y_rec),
    arrowprops=dict(arrowstyle="<->", color="#2CA02C", lw=1.5)
)
ax1.text(
    peak_date_e + (recession_end_date - peak_date_e) / 2, y_rec * 1.05,
    f"Recession: {recession_time} d",
    ha="center", va="bottom", fontsize=9, color="#2CA02C",
    bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, ec="none")
)

ax1.set_ylabel("Rennsli Q  (m³/s)", fontsize=11)
ax1.legend(fontsize=9, loc="upper right", ncol=2)
ax1.grid(axis="y", linestyle="--", alpha=0.4)
ax1.set_ylim(bottom=0)
ax1.spines[["top", "right"]].set_visible(False)

# ── Miðhluti: Úrkoma P ────────────────────────────────────────────────────
ax2 = axes[1]
ax2.bar(dates, ev["P"], color="#4C9BE8", alpha=0.85,
        label="P (mm/dag)", width=0.8)

ax2.axvline(excess_rain_start, color="#E87C4C", linestyle="--", linewidth=1.5,
            label=f"Lok úrkomu / excess rain byrjar ({excess_rain_start.date()})")
ax2.axvline(recession_end_date, color="#2CA02C", linestyle=":", linewidth=1.3,
            alpha=0.8)
ax2.axvline(peak_date_e, color="#E84C4C", linestyle="--", linewidth=1.3, alpha=0.7)

# Excess rain release ör – frá daginum eftir lok úrkomu að grunngildi
P_max_plot = max(ev["P"].max(), 2.0)
y_exc = P_max_plot * 0.75
ax2.annotate(
    "", xy=(recession_end_date, y_exc), xytext=(excess_rain_start, y_exc),
    arrowprops=dict(arrowstyle="<->", color="#E87C4C", lw=1.5)
)
ax2.text(
    excess_rain_start + (recession_end_date - excess_rain_start) / 2, y_exc * 1.08,
    f"Excess rain release: {excess_rain_time} d",
    ha="center", va="bottom", fontsize=9, color="#E87C4C",
    bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, ec="none")
)

ax2.set_ylabel("Úrkoma P  (mm/dag)", fontsize=11)
ax2.legend(fontsize=9, loc="upper left")
ax2.grid(axis="y", linestyle="--", alpha=0.4)
ax2.set_ylim(bottom=0)
ax2.spines[["top", "right"]].set_visible(False)

# ── Neðri hluti: Hitastig T ───────────────────────────────────────────────
ax3 = axes[2]
ax3.plot(dates, ev["T"], color="#C0392B", linewidth=2, label="T (°C)")
ax3.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
ax3.fill_between(dates, ev["T"], 0,
                 where=(ev["T"] >= 0), alpha=0.15, color="#C0392B",
                 label="T > 0°C (bráðnun möguleg)")
ax3.fill_between(dates, ev["T"], 0,
                 where=(ev["T"] < 0), alpha=0.15, color="#4C9BE8",
                 label="T < 0°C")

ax3.axvline(peak_date_e, color="#E84C4C", linestyle="--",
            linewidth=1.3, alpha=0.7)

ax3.set_ylabel("Hitastig T  (°C)", fontsize=11)
ax3.legend(fontsize=9, loc="upper right")
ax3.grid(axis="y", linestyle="--", alpha=0.4)
ax3.spines[["top", "right"]].set_visible(False)

# x-ás – dagsetning
ax3.xaxis.set_major_locator(mdates.DayLocator(interval=5))
ax3.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
fig.autofmt_xdate(rotation=30, ha="right")

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(FIG_OUT, dpi=150, bbox_inches="tight")
print(f"\nMynd vistuð: {FIG_OUT}")

sys.stdout.flush()
plt.show()
