"""
Lið 2 - Árstaðasveifla (Climatology)
Vatnsfall: Hvítá, Kljáfoss (ID 37)
Tímabil:   1. október 1993 – 30. september 2023 (30 ár)

Þetta skript les gögn beint úr lamah_ice möppunni og teiknar meðaltalsar
(climatology) fyrir rennsli (Q), úrkomu (P) og hitastig (T).
"""

import os
import sys

# Tryggja að íslenskir stafir birtist rétt í Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ---------------------------------------------------------------------------
# Stillingar
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # Mappa skriptunnar
DATA_DIR  = os.path.join(SCRIPT_DIR, "lamah_ice")        # Staðsetning gagnamöppunnar
GAUGE_ID  = 37                                            # Hvítá, Kljáfoss
START     = "1993-10-01"
END       = "2023-09-30"
FIG_OUT   = os.path.join(SCRIPT_DIR, "figures", "Lidur_2_arstadasveifla.png")

MONTHS_IS = ["Jan", "Feb", "Mar", "Apr", "Maí", "Jún",
             "Júl", "Ágú", "Sep", "Okt", "Nóv", "Des"]

# ---------------------------------------------------------------------------
# 1. Les gögn úr möppu
# ---------------------------------------------------------------------------
gauge_path = os.path.join(DATA_DIR, "D_gauges", "2_timeseries", "daily",
                          f"ID_{GAUGE_ID}.csv")
met_path   = os.path.join(DATA_DIR, "A_basins_total_upstrm", "2_timeseries",
                          "daily", "meteorological_data", f"ID_{GAUGE_ID}.csv")

q_raw = pd.read_csv(gauge_path, sep=";")
m_raw = pd.read_csv(met_path, sep=";")

# ---------------------------------------------------------------------------
# 2. Búa til dagsetningardálk og sía á rétt tímabil
# ---------------------------------------------------------------------------
def make_date(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(
        df[["YYYY", "MM", "DD"]].rename(
            columns={"YYYY": "year", "MM": "month", "DD": "day"}
        )
    )
    return df

q = make_date(q_raw)
m = make_date(m_raw)

mask_q = (q["date"] >= START) & (q["date"] <= END)
mask_m = (m["date"] >= START) & (m["date"] <= END)

q = q[mask_q].copy()
m = m[mask_m].copy()

print(f"Rennslisgögn:  {len(q)} dagar  ({q['date'].min().date()} – {q['date'].max().date()})")
print(f"Veðurgögn:     {len(m)} dagar  ({m['date'].min().date()} – {m['date'].max().date()})")

# ---------------------------------------------------------------------------
# 3. Mánaðarleg meðalgildi (climatology)
# ---------------------------------------------------------------------------
# Rennsli (m³/s) – nota qobs
q_clim = q.groupby("MM")["qobs"].mean()

# Úrkoma (mm/dag) – CARRA endurgreining
p_clim = m.groupby("MM")["prec_carra"].mean()

# Hitastig (°C) – CARRA endurgreining
t_clim = m.groupby("MM")["2m_temp_carra"].mean()

# Öryggisbil (±1 std) fyrir rennsli og hitastig til glöggvunar
q_std  = q.groupby("MM")["qobs"].std()
t_std  = m.groupby("MM")["2m_temp_carra"].std()
p_std  = m.groupby("MM")["prec_carra"].std()

months = np.arange(1, 13)

# ---------------------------------------------------------------------------
# 4. Mynd
# ---------------------------------------------------------------------------
os.makedirs(os.path.join(SCRIPT_DIR, "figures"), exist_ok=True)

fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
fig.suptitle(
    "Árstaðasveifla – Hvítá, Kljáfoss (ID 37)\n"
    "Tímabil: 1993–2023  |  Dagleg gögn, CARRA endurgreining",
    fontsize=13, fontweight="bold", y=0.98
)

bar_color  = "#4C9BE8"
line_color = "#E84C4C"
q_color    = "#2E6DA4"

# -- Efri hluti: Rennsli --
ax1 = axes[0]
ax1.fill_between(months,
                 q_clim - q_std, q_clim + q_std,
                 alpha=0.25, color=q_color, label="±1 std")
ax1.plot(months, q_clim, color=q_color, linewidth=2.2, marker="o",
         markersize=5, label="Meðalrennsli")
ax1.set_ylabel("Rennsli Q  (m³/s)", fontsize=11)
ax1.legend(fontsize=9, loc="upper left")
ax1.grid(axis="y", linestyle="--", alpha=0.5)
ax1.set_ylim(bottom=0)
ax1.yaxis.set_minor_locator(mticker.AutoMinorLocator())

# -- Miðhluti: Úrkoma --
ax2 = axes[1]
bars = ax2.bar(months, p_clim, color=bar_color, alpha=0.85,
               edgecolor="white", linewidth=0.5, label="Meðalúrkoma")
ax2.errorbar(months, p_clim, yerr=p_std, fmt="none",
             ecolor="steelblue", elinewidth=1, capsize=3, alpha=0.6)
ax2.set_ylabel("Úrkoma P  (mm/dag)", fontsize=11)
ax2.legend(fontsize=9, loc="upper left")
ax2.grid(axis="y", linestyle="--", alpha=0.5)
ax2.set_ylim(bottom=0)

# -- Neðri hluti: Hitastig --
ax3 = axes[2]
ax3.fill_between(months,
                 t_clim - t_std, t_clim + t_std,
                 alpha=0.2, color=line_color, label="±1 std")
ax3.plot(months, t_clim, color=line_color, linewidth=2.2, marker="o",
         markersize=5, label="Meðalhitastig")
ax3.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
ax3.set_ylabel("Hitastig T  (°C)", fontsize=11)
ax3.legend(fontsize=9, loc="upper left")
ax3.grid(axis="y", linestyle="--", alpha=0.5)
ax3.yaxis.set_minor_locator(mticker.AutoMinorLocator())

# x-ás stillingar
ax3.set_xticks(months)
ax3.set_xticklabels(MONTHS_IS, fontsize=10)
ax3.set_xlim(0.5, 12.5)

for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(FIG_OUT, dpi=150, bbox_inches="tight")
print(f"\nMynd vistuð: {FIG_OUT}")

# ---------------------------------------------------------------------------
# 5. Prenta töflu með mánaðarlegum meðalgildum
# ---------------------------------------------------------------------------
clim_df = pd.DataFrame({
    "Mánuður":       MONTHS_IS,
    "Q_mean (m³/s)": q_clim.values.round(1),
    "Q_std (m³/s)":  q_std.values.round(1),
    "P_mean (mm/d)": p_clim.values.round(2),
    "T_mean (°C)":   t_clim.values.round(2),
})
print("\n--- Mánaðarlegar meðaltölur (climatology) ---")
print(clim_df.to_string(index=False))

plt.show()
