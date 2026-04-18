"""
Lið 4 - Tenging við grunnlíkingu vatnafræðinnar (Water Balance)
Vatnsfall: Hvítá, Kljáfoss (ID 37)
Tímabil:   1. október 1993 – 30. september 2023 (30 ár)

Grunnlíking vatnafræðinnar:
    P = Q + ET + ΔS

    P  = úrkoma (mm/dag) – mælt með CARRA endurgreiningu
    Q  = rennsli (mm/dag) – mælt, umreiknað með flatarmáli vatnasviðs
    ET = raunveruleg uppgufun (mm/dag) – reiknað með CARRA
    ΔS = breyting í geymslu (mm/dag) – leifar (residual): P - Q - ET

Óvissa:
    Q  – mælt á mælistöð, nokkuð nákvæmt (rating curve óvissa ~5–15%)
    P  – CARRA endurgreining, líkansgögn – óvissa í flóknu landslagi (~10–20%)
    ET – CARRA líkan, erfiðast að meta – stærsta óvissan (~20–40%)
    ΔS – samanlagðar allar villur + jökulmassi (Langjökull minnkar)
"""

import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Stillingar
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "lamah_ice")
GAUGE_ID   = 37
START      = "1993-10-01"
END        = "2023-09-30"
AREA_KM2   = 1719.981   # Flatarmál vatnasviðs (km²)
FIG_OUT    = os.path.join(SCRIPT_DIR, "figures", "Lidur_4_vatnajafnvaegi.png")

MONTHS_IS  = ["Jan", "Feb", "Mar", "Apr", "Maí", "Jún",
              "Júl", "Ágú", "Sep", "Okt", "Nóv", "Des"]

# ---------------------------------------------------------------------------
# 1. Les gögn
# ---------------------------------------------------------------------------
gauge_path = os.path.join(DATA_DIR, "D_gauges", "2_timeseries", "daily",
                          f"ID_{GAUGE_ID}.csv")
met_path   = os.path.join(DATA_DIR, "A_basins_total_upstrm", "2_timeseries",
                          "daily", "meteorological_data", f"ID_{GAUGE_ID}.csv")

q_raw = pd.read_csv(gauge_path, sep=";")
m_raw = pd.read_csv(met_path, sep=";")

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

# ---------------------------------------------------------------------------
# 2. Umreikningur Q úr m³/s í mm/dag
#    Q [mm/dag] = Q [m³/s] × 86400 [s/dag] / (A [m²]) × 1000 [mm/m]
# ---------------------------------------------------------------------------
AREA_M2 = AREA_KM2 * 1e6
q["Q_mm"] = q["qobs"] * 86400 / AREA_M2 * 1000

# ---------------------------------------------------------------------------
# 3. Sameina Q og veðurgögn
# ---------------------------------------------------------------------------
df = m[["date", "MM", "YYYY", "prec_carra", "total_et_carra"]].copy()
df = df.merge(q[["date", "Q_mm"]], on="date", how="inner")
df = df.rename(columns={"prec_carra": "P", "total_et_carra": "ET"})

# ΔS = P - Q - ET  (jákvætt = geymsla eykst, neikvætt = geymsla minnkar)
df["dS"] = df["P"] - df["Q_mm"] - df["ET"]

# Vatnsár (1. okt – 30. sep)
df["vatnsár"] = df["date"].apply(
    lambda d: d.year if d.month >= 10 else d.year - 1
)

print(f"Gögn: {len(df)} dagar  ({df['date'].min().date()} – {df['date'].max().date()})")

# ---------------------------------------------------------------------------
# 4. Árleg vatnajafnvægi
# ---------------------------------------------------------------------------
annual = df.groupby("vatnsár")[["P", "Q_mm", "ET", "dS"]].sum()
annual.columns = ["P_mm", "Q_mm", "ET_mm", "dS_mm"]

print("\n--- Meðalgildi yfir 30 ár (mm/ár) ---")
print(f"  Úrkoma   P  = {annual['P_mm'].mean():.1f} mm/ár  [CARRA – reiknað]")
print(f"  Rennsli  Q  = {annual['Q_mm'].mean():.1f} mm/ár  [mælt]")
print(f"  Uppgufun ET = {annual['ET_mm'].mean():.1f} mm/ár  [CARRA – reiknað]")
print(f"  Geymsla  ΔS = {annual['dS_mm'].mean():.1f} mm/ár  [leifar: P - Q - ET]")
print(f"\n  Rennslisthlutfall Q/P = {(annual['Q_mm']/annual['P_mm']).mean():.3f}")

# ---------------------------------------------------------------------------
# 5. Mánaðarleg climatology
# ---------------------------------------------------------------------------
monthly = df.groupby("MM")[["P", "Q_mm", "ET", "dS"]].mean()
months  = np.arange(1, 13)

# ---------------------------------------------------------------------------
# 6. Myndir
# ---------------------------------------------------------------------------
os.makedirs(os.path.join(SCRIPT_DIR, "figures"), exist_ok=True)

fig, axes = plt.subplots(2, 1, figsize=(12, 10))
fig.suptitle(
    "Vatnajafnvægi – Hvítá, Kljáfoss (ID 37)\n"
    "Grunnlíking: P = Q + ET + ΔS  |  CARRA endurgreining  |  1993–2023",
    fontsize=13, fontweight="bold"
)

# -- Efri hluti: Árleg þróun --
ax1 = axes[0]
ax1.fill_between(annual.index, annual["P_mm"], alpha=0.2, color="#4C9BE8")
ax1.plot(annual.index, annual["P_mm"],  color="#4C9BE8", linewidth=2,
         marker="o", markersize=4, label="P – Úrkoma")
ax1.plot(annual.index, annual["Q_mm"],  color="#2E6DA4", linewidth=2,
         marker="s", markersize=4, label="Q – Rennsli (mælt)")
ax1.plot(annual.index, annual["ET_mm"], color="#E84C4C", linewidth=2,
         marker="^", markersize=4, label="ET – Uppgufun (CARRA)")
ax1.plot(annual.index, annual["dS_mm"], color="#555555", linewidth=1.5,
         linestyle="--", marker="x", markersize=4, label="ΔS – Geymslubreyting")
ax1.axhline(0, color="black", linewidth=0.7, linestyle=":")
ax1.set_ylabel("mm/ár", fontsize=11)
ax1.set_title("Árlegt vatnajafnvægi", fontsize=11)
ax1.legend(fontsize=9, ncol=2)
ax1.grid(axis="y", linestyle="--", alpha=0.5)
ax1.spines[["top", "right"]].set_visible(False)

# -- Neðri hluti: Mánaðarleg climatology (staflað súlurit) --
ax2 = axes[1]
bar_width = 0.6

ax2.bar(months, monthly["Q_mm"], bar_width,
        color="#2E6DA4", label="Q – Rennsli")
ax2.bar(months, monthly["ET"], bar_width,
        bottom=monthly["Q_mm"],
        color="#E84C4C", label="ET – Uppgufun")
ax2.bar(months, monthly["dS"].clip(lower=0), bar_width,
        bottom=monthly["Q_mm"] + monthly["ET"],
        color="#90C090", label="ΔS+ (geymsluaukning)")
ax2.bar(months, monthly["dS"].clip(upper=0), bar_width,
        bottom=monthly["Q_mm"] + monthly["ET"],
        color="#C09090", label="ΔS− (geymsluminnkun)")
ax2.plot(months, monthly["P"], color="#333333", linewidth=2.2,
         marker="o", markersize=5, label="P – Úrkoma")

ax2.set_xticks(months)
ax2.set_xticklabels(MONTHS_IS, fontsize=10)
ax2.set_xlim(0.5, 12.5)
ax2.set_ylabel("mm/dag", fontsize=11)
ax2.set_title("Mánaðarleg meðalgildi", fontsize=11)
ax2.legend(fontsize=9, ncol=3)
ax2.grid(axis="y", linestyle="--", alpha=0.5)
ax2.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
plt.savefig(FIG_OUT, dpi=150, bbox_inches="tight")
print(f"\nMynd vistuð: {FIG_OUT}")

# ---------------------------------------------------------------------------
# 7. Óvissumat
# ---------------------------------------------------------------------------

sys.stdout.flush()

plt.show()
