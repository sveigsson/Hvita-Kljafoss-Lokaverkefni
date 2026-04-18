"""
Lið 6 - Flóðagreining
Vatnsfall: Hvítá, Kljáfoss (ID 37)
Tímabil:   1. október 1993 – 30. september 2023 (30 ár)

1. Flood seasonality – hvenær verða stærstu flóðin?
2. Frequency analysis – Gumbel, Log-Normal 3, Log-Pearson 3
   - Gringorten plotting positions
   - Q10, Q50, Q100
   - 90% confidence interval með bootstrap (N=2000)
"""

import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

# ---------------------------------------------------------------------------
# Stillingar
# ---------------------------------------------------------------------------
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(SCRIPT_DIR, "lamah_ice")
GAUGE_ID    = 37
START       = "1993-10-01"
END         = "2023-09-30"
N_BOOT      = 2000          # Bootstrap endurtekningar
CI_LEVEL    = 0.90          # 90% confidence interval
RNG_SEED    = 42
FIG_SEASON  = os.path.join(SCRIPT_DIR, "figures", "Lidur_6a_flood_seasonality.png")
FIG_FREQ    = os.path.join(SCRIPT_DIR, "figures", "Lidur_6b_flood_frequency.png")

MONTHS_IS   = ["Jan", "Feb", "Mar", "Apr", "Maí", "Jún",
               "Júl", "Ágú", "Sep", "Okt", "Nóv", "Des"]
RETURN_PERIODS = [2, 5, 10, 20, 50, 100, 200]

# ---------------------------------------------------------------------------
# 1. Les og undirbý gögn
# ---------------------------------------------------------------------------
gauge_path = os.path.join(DATA_DIR, "D_gauges", "2_timeseries", "daily",
                          f"ID_{GAUGE_ID}.csv")
q_raw = pd.read_csv(gauge_path, sep=";")

q = q_raw.copy()
q["date"] = pd.to_datetime(
    q[["YYYY", "MM", "DD"]].rename(columns={"YYYY": "year", "MM": "month", "DD": "day"})
)
q = q[(q["date"] >= START) & (q["date"] <= END)].copy()
q["vatnsár"] = q["date"].apply(lambda d: d.year if d.month >= 10 else d.year - 1)

# ---------------------------------------------------------------------------
# 2. Annual peaks – hæsta rennsli hvers vatnsárs
# ---------------------------------------------------------------------------
peak_idx   = q.groupby("vatnsár")["qobs"].idxmax()
peaks_df   = q.loc[peak_idx, ["date", "qobs", "MM", "vatnsár"]].copy()
peaks_df   = peaks_df.sort_values("vatnsár").reset_index(drop=True)
peaks      = peaks_df["qobs"].values
n          = len(peaks)

print(f"Annual peaks: n = {n} ár")
print(f"  Hæsta:   {peaks.max():.1f} m³/s  ({peaks_df.loc[peaks_df['qobs'].idxmax(),'date'].date()})")
print(f"  Lægsta:  {peaks.min():.1f} m³/s")
print(f"  Meðaltal: {peaks.mean():.1f} m³/s")

# ---------------------------------------------------------------------------
# 3. Flood seasonality
# ---------------------------------------------------------------------------
month_counts = peaks_df["MM"].value_counts().reindex(range(1, 13), fill_value=0)

# ---------------------------------------------------------------------------
# 4. Gringorten plotting positions
#    P_i = (i - 0.44) / (n + 0.12),  i = 1 … n  (raðað hækkandi)
# ---------------------------------------------------------------------------
sorted_peaks = np.sort(peaks)
ranks        = np.arange(1, n + 1)
prob_emp     = (ranks - 0.44) / (n + 0.12)         # F(x) – non-exceedance
T_emp        = 1.0 / (1.0 - prob_emp)               # Return period

# ---------------------------------------------------------------------------
# 5. Líkindadreifingar
# ---------------------------------------------------------------------------

def fit_gumbel(data):
    loc, scale = stats.gumbel_r.fit(data)
    return loc, scale

def gumbel_quantile(T, loc, scale):
    p = 1.0 - 1.0 / T
    return stats.gumbel_r.ppf(p, loc=loc, scale=scale)

def fit_ln3(data):
    """3-stika Log-Normal: lognorm.fit gefur (s, loc, scale)"""
    s, loc, scale = stats.lognorm.fit(data, floc=None)
    return s, loc, scale

def ln3_quantile(T, s, loc, scale):
    p = 1.0 - 1.0 / T
    return stats.lognorm.ppf(p, s=s, loc=loc, scale=scale)

def fit_lp3(data):
    """Log-Pearson 3: Pearson III á log10(Q)"""
    log_data = np.log10(data)
    skew, loc, scale = stats.pearson3.fit(log_data)
    return skew, loc, scale

def lp3_quantile(T, skew, loc, scale):
    p = 1.0 - 1.0 / T
    log_q = stats.pearson3.ppf(p, skew, loc=loc, scale=scale)
    return 10.0 ** log_q

# Passa dreifingar
gumb_params = fit_gumbel(sorted_peaks)
ln3_params  = fit_ln3(sorted_peaks)
lp3_params  = fit_lp3(sorted_peaks)

# RMSE samanborið við Gringorten empirical gildi
def rmse_cdf(dist_ppf_func, params, T_emp, sorted_peaks):
    fitted = dist_ppf_func(T_emp, *params)
    return np.sqrt(np.mean((sorted_peaks - fitted) ** 2))

rmse_gumb = rmse_cdf(gumbel_quantile, gumb_params, T_emp, sorted_peaks)
rmse_ln3  = rmse_cdf(ln3_quantile,   ln3_params,  T_emp, sorted_peaks)
rmse_lp3  = rmse_cdf(lp3_quantile,   lp3_params,  T_emp, sorted_peaks)

print(f"\n--- RMSE samanburður við Gringorten ---")
print(f"  Gumbel:       {rmse_gumb:.2f} m³/s")
print(f"  Log-Normal 3: {rmse_ln3:.2f} m³/s")
print(f"  Log-Pearson 3:{rmse_lp3:.2f} m³/s")

rmse_dict = {"Gumbel": rmse_gumb, "LN3": rmse_ln3, "LP3": rmse_lp3}
best_dist = min(rmse_dict, key=rmse_dict.get)
print(f"\n  Besta dreifing: {best_dist}")

# ---------------------------------------------------------------------------
# 6. Q10, Q50, Q100 – allar þrjár dreifingar
# ---------------------------------------------------------------------------
T_design = [10, 50, 100]
print(f"\n--- Hönnunarflóð (m³/s) ---")
print(f"{'Dreifing':<16} {'Q10':>8} {'Q50':>8} {'Q100':>8}")
print("-" * 42)
for name, qfunc, params in [
    ("Gumbel",        gumbel_quantile, gumb_params),
    ("Log-Normal 3",  ln3_quantile,    ln3_params),
    ("Log-Pearson 3", lp3_quantile,    lp3_params),
]:
    vals = [qfunc(T, *params) for T in T_design]
    print(f"{name:<16} {vals[0]:>8.1f} {vals[1]:>8.1f} {vals[2]:>8.1f}")

# ---------------------------------------------------------------------------
# 7. Bootstrap 90% CI á bestu dreifingu
# ---------------------------------------------------------------------------
rng = np.random.default_rng(RNG_SEED)
boot_quantiles = {T: [] for T in T_design}

if best_dist == "Gumbel":
    fit_fn = fit_gumbel
    q_fn   = gumbel_quantile
elif best_dist == "LN3":
    fit_fn = fit_ln3
    q_fn   = ln3_quantile
else:
    fit_fn = fit_lp3
    q_fn   = lp3_quantile

for _ in range(N_BOOT):
    sample = rng.choice(peaks, size=n, replace=True)
    try:
        p = fit_fn(np.sort(sample))
        for T in T_design:
            boot_quantiles[T].append(q_fn(T, *p))
    except Exception:
        pass

alpha = (1.0 - CI_LEVEL) / 2.0
print(f"\n--- 90% Bootstrap CI ({best_dist}) ---")
print(f"{'T (ár)':<10} {'Q (m³/s)':>10} {'Neðri':>10} {'Efri':>10}")
print("-" * 44)
if best_dist == "Gumbel":
    best_params = gumb_params
elif best_dist == "LN3":
    best_params = ln3_params
else:
    best_params = lp3_params

for T in T_design:
    bq = np.array(boot_quantiles[T])
    q_est = q_fn(T, *best_params)
    lo = np.percentile(bq, alpha * 100)
    hi = np.percentile(bq, (1 - alpha) * 100)
    print(f"{T:<10} {q_est:>10.1f} {lo:>10.1f} {hi:>10.1f}")

sys.stdout.flush()

# ---------------------------------------------------------------------------
# 8. Myndir
# ---------------------------------------------------------------------------
os.makedirs(os.path.join(SCRIPT_DIR, "figures"), exist_ok=True)

# -- 8a. Flood seasonality --
fig1, ax = plt.subplots(figsize=(10, 5))
colors = ["#4C9BE8" if m not in [12, 1, 2, 3] else "#E84C4C"
          for m in range(1, 13)]
bars = ax.bar(range(1, 13), month_counts.values, color=colors,
              edgecolor="white", linewidth=0.5)
ax.set_xticks(range(1, 13))
ax.set_xticklabels(MONTHS_IS, fontsize=10)
ax.set_ylabel("Fjöldi annual peaks", fontsize=11)
ax.set_title("Flood seasonality – Hvítá, Kljáfoss (ID 37)\n"
             "Rautt = vetrarflóð (Des–Mar), Blátt = aðrir mánuðir", fontsize=12)
ax.grid(axis="y", linestyle="--", alpha=0.5)
ax.spines[["top", "right"]].set_visible(False)
for bar, val in zip(bars, month_counts.values):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                str(val), ha="center", va="bottom", fontsize=10)
plt.tight_layout()
plt.savefig(FIG_SEASON, dpi=150, bbox_inches="tight")
print(f"\nMynd vistuð: {FIG_SEASON}")
plt.show()

# -- 8b. Flood frequency curve --
T_plot = np.logspace(np.log10(1.01), np.log10(500), 200)

fig2, ax = plt.subplots(figsize=(11, 6))

# Empirical points (Gringorten)
ax.scatter(T_emp, sorted_peaks, color="black", zorder=5, s=40,
           label="Empirical (Gringorten)", marker="o")

# Dreifingalínur
ax.plot(T_plot, [gumbel_quantile(T, *gumb_params) for T in T_plot],
        color="#E84C4C", linewidth=2,
        label=f"Gumbel (RMSE={rmse_gumb:.1f})")
ax.plot(T_plot, [ln3_quantile(T, *ln3_params) for T in T_plot],
        color="#4C9BE8", linewidth=2,
        label=f"Log-Normal 3 (RMSE={rmse_ln3:.1f})")
ax.plot(T_plot, [lp3_quantile(T, *lp3_params) for T in T_plot],
        color="#2CA02C", linewidth=2,
        label=f"Log-Pearson 3 (RMSE={rmse_lp3:.1f})")

# Bootstrap CI á bestu dreifingu
T_ci = np.logspace(np.log10(1.5), np.log10(500), 100)
ci_lo, ci_hi = [], []
for T in T_ci:
    bq = []
    for _ in range(500):
        sample = rng.choice(peaks, size=n, replace=True)
        try:
            p = fit_fn(np.sort(sample))
            bq.append(q_fn(T, *p))
        except Exception:
            pass
    if bq:
        ci_lo.append(np.percentile(bq, alpha * 100))
        ci_hi.append(np.percentile(bq, (1 - alpha) * 100))
    else:
        ci_lo.append(np.nan)
        ci_hi.append(np.nan)

color_best = {"Gumbel": "#E84C4C", "LN3": "#4C9BE8", "LP3": "#2CA02C"}[best_dist]
ax.fill_between(T_ci, ci_lo, ci_hi, alpha=0.2, color=color_best,
                label=f"90% CI ({best_dist})")

# Q10, Q50, Q100 merkingar
for T, ls in [(10, "--"), (50, ":"), (100, "-.")]:
    qval = q_fn(T, *best_params)
    ax.axvline(T, color="gray", linestyle=ls, linewidth=1, alpha=0.7)
    ax.text(T * 1.05, ax.get_ylim()[0] + 10,
            f"Q{T}={qval:.0f}", fontsize=8, color="gray", va="bottom")

ax.set_xscale("log")
ax.set_xlabel("Endurkomutími (ár)", fontsize=11)
ax.set_ylabel("Rennsli (m³/s)", fontsize=11)
ax.set_title("Flóðatíðnigreining – Hvítá, Kljáfoss (ID 37)\n"
             "Gumbel · Log-Normal 3 · Log-Pearson 3  |  1993–2023", fontsize=12)
ax.legend(fontsize=9)
ax.grid(True, which="both", linestyle="--", alpha=0.4)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig(FIG_FREQ, dpi=150, bbox_inches="tight")
print(f"Mynd vistuð: {FIG_FREQ}")

sys.stdout.flush()
plt.show()
