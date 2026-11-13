"""
Step 5: figures and tables for the paper.

Builds every figure from the pipeline's own outputs, so rerunning run_all.py
regenerates them with current numbers. Each figure is saved as a 300-dpi PNG
(for Word / Google Docs) and a PDF (vector, for LaTeX / print) in figures/,
and tables are saved as CSV in tables/. Captions with source notes are written
to figures/figure_captions.md.

Style: print-first, white background, one accent color per job, colorblind-safe
palette, thin marks, light gridlines, no dual axes.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import statsmodels.api as sm
import statsmodels.formula.api as smf

import config
import salary_analysis as sa

# ---------------- style ----------------
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
GRAY_MID = "#f0efec"
WIDTH = 6.5            # inches: full text width of a letter-size page
SOURCE = "Data: Baseball-Reference; Cot's Baseball Contracts (Baseball Prospectus)."

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "pdf.fonttype": 42,
})

CAPTIONS = []


def save(fig, name, caption):
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(config.FIGURES_DIR / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    CAPTIONS.append((name, caption))
    print(f"   saved {name}")


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


# ---------------- data ----------------
def load():
    raw = pd.read_csv(config.MERGED_FILE)
    df = sa.prepare(raw)
    return raw, df, int(df["Year"].max())


# ---------------- figures ----------------
def fig_payroll_over_time(raw):
    d = raw.assign(P=raw["Cots_OD_Payroll"] / 1e6)
    years = sorted(d["Year"].unique())
    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    data = [d.loc[d["Year"] == y, "P"] for y in years]
    pos = np.arange(len(years))
    ax.boxplot(data, positions=pos, widths=0.55, patch_artist=True, showfliers=True,
               boxprops=dict(facecolor="#cde2fb", edgecolor=BLUE, linewidth=0.8),
               medianprops=dict(color=BLUE, linewidth=1.6),
               whiskerprops=dict(color=BLUE, linewidth=0.8), capprops=dict(color=BLUE, linewidth=0.8),
               flierprops=dict(marker="o", markersize=3.5, markerfacecolor="white",
                               markeredgecolor=BLUE, markeredgewidth=0.8))
    means = [x.mean() for x in data]
    ax.plot(pos, means, color=ORANGE, lw=1.6, marker="o", ms=4, label="League average", zorder=3)
    ax.set_xticks(pos, [str(y) for y in years])
    ax.set_ylabel("Opening Day payroll ($M, nominal)")
    ax.set_ylim(0, None)
    gap = years.index(2021) - 0.5 if 2021 in years else None
    if gap is not None:
        ax.axvline(gap, color=AXIS, lw=0.8, ls=(0, (3, 3)))
        ax.text(gap, ax.get_ylim()[1] * 0.97, "2020 excluded", ha="center", va="top",
                fontsize=7, color=MUTED, bbox=dict(fc="white", ec="none", pad=1))
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", frameon=False)
    save(fig, "fig01_payroll_over_time",
         f"Opening Day payroll by season, {years[0]}–{years[-1]}. Boxes show the middle 50% of "
         f"teams, the line inside each box the median, and the orange line the league average "
         f"(${means[0]:.0f}M in {years[0]}, ${means[-1]:.0f}M in {years[-1]}). The shortened 2020 "
         f"season is excluded. {SOURCE}")


def fig_payroll_shares():
    b = pd.read_csv(config.PAYROLL_BY_POSITION_FILE)
    groups = {
        "Starting pitchers": ["Pay_SP"], "Relief pitchers": ["Pay_RP"],
        "Outfield (LF/CF/RF)": ["Pay_OF_All"], "First base": ["Pay_1B"],
        "Third base": ["Pay_3B"], "Shortstop": ["Pay_SS"], "Second base": ["Pay_2B"],
        "Catcher": ["Pay_C"], "Designated hitter": ["Pay_DH"],
        "Other (released, buyouts, trade cash, utility)": ["Pay_Other", "Pay_UTIL"],
    }
    total = b["Pay_Total"].sum()
    share = pd.Series({k: b[v].sum().sum() / total * 100 for k, v in groups.items()})
    other = share.filter(like="Other")
    share = pd.concat([share.drop(other.index).sort_values(ascending=False), other])
    fig, ax = plt.subplots(figsize=(WIDTH, 3.4))
    y = np.arange(len(share))[::-1]
    ax.barh(y, share.values, height=0.62, color=BLUE, edgecolor="white", linewidth=1)
    for yi, v in zip(y, share.values):
        ax.text(v + 0.4, yi, f"{v:.1f}%", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, share.index)
    ax.set_xlabel("Share of Opening Day payroll, all team-seasons (%)")
    ax.set_xlim(0, share.max() * 1.15)
    ax.grid(axis="y", visible=False)
    yrs = f"{b['Year'].min()}–{b['Year'].max()}"
    save(fig, "fig02_payroll_share_by_position",
         f"Share of Opening Day payroll by position, pooled over all team-seasons ({yrs}). "
         f"Each player's salary is assigned to his primary position as listed by Cot's. "
         f"Pitchers received {share['Starting pitchers'] + share['Relief pitchers']:.0f}% of payroll. {SOURCE}")


def fig_wins_vs_war(raw):
    m = sm.OLS(raw["W"], sm.add_constant(raw["TotalWAR"])).fit()
    a, b = m.params
    fig, ax = plt.subplots(figsize=(WIDTH, 3.8))
    ax.scatter(raw["TotalWAR"], raw["W"], s=14, color=BLUE, alpha=0.55, edgecolor="white", linewidth=0.4)
    xs = np.linspace(min(0, raw["TotalWAR"].min()), raw["TotalWAR"].max(), 100)
    ax.plot(xs, a + b * xs, color=ORANGE, lw=2)
    ax.axhline(a, color=AXIS, lw=0.8, ls=(0, (3, 3)))
    ax.text(raw["TotalWAR"].max(), a + 1, f"Replacement level ≈ {a:.0f} wins", ha="right",
            va="bottom", fontsize=7.5, color=INK2)
    ax.text(0.02, 0.97, f"Wins = {a:.1f} + {b:.2f} × WAR\nR² = {m.rsquared:.3f}, N = {int(m.nobs)}",
            transform=ax.transAxes, va="top", fontsize=8.5, color=INK,
            bbox=dict(fc="white", ec=GRID, boxstyle="round,pad=0.4"))
    ax.set_xlabel("Total team WAR")
    ax.set_ylabel("Wins")
    save(fig, "fig03_wins_vs_war",
         f"Team wins against total team WAR, {raw['Year'].min()}–{raw['Year'].max()} "
         f"(N = {int(m.nobs)} team-seasons). Each additional WAR is associated with {b:.2f} more "
         f"wins (95% CI {m.conf_int().iloc[1, 0]:.2f}–{m.conf_int().iloc[1, 1]:.2f}); the intercept "
         f"implies about {a:.0f} wins for a replacement-level team. {SOURCE}")


def fig_positional_coefficients(raw):
    cols = config.REGRESSION_POS_COLS
    m = sm.OLS(raw["W"], sm.add_constant(raw[cols])).fit()
    names = {"1B": "First base", "2B": "Second base", "3B": "Third base", "C": "Catcher",
             "CF": "Center field", "DH": "Designated hitter", "LF": "Left field",
             "RF": "Right field", "SS": "Shortstop", "SP": "Starting pitchers", "RP": "Relief pitchers"}
    t = pd.DataFrame({"b": m.params[cols], "lo": m.conf_int().loc[cols, 0],
                      "hi": m.conf_int().loc[cols, 1]}).sort_values("b")
    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    y = np.arange(len(t))
    excl = (t["lo"] > 1) | (t["hi"] < 1)
    for yi, (_, r), e in zip(y, t.iterrows(), excl):
        c = ORANGE if e else BLUE
        ax.plot([r.lo, r.hi], [yi, yi], color=c, lw=1.6, solid_capstyle="round")
        ax.plot(r.b, yi, "o", color=c, ms=6, mec="white", mew=0.8)
    ax.axvline(1, color=INK2, lw=0.9, ls=(0, (3, 3)))
    ax.text(1.01, len(t) - 0.4, "1 WAR = 1 win", fontsize=7.5, color=INK2, va="bottom")
    ax.set_yticks(y, [names[c] for c in t.index])
    ax.set_xlabel("Wins per WAR at each position (coefficient and 95% CI)")
    ax.set_ylim(-0.7, len(t) + 0.3)
    ax.grid(axis="y", visible=False)
    if excl.any():
        ax.plot([], [], "o-", color=ORANGE, label="95% CI excludes 1")
        ax.plot([], [], "o-", color=BLUE, label="95% CI includes 1")
        ax.legend(loc="lower right", frameon=False)
    save(fig, "fig04_war_value_by_position",
         f"Wins associated with one WAR at each position, from a regression of wins on WAR at all "
         f"eleven positions (R² = {m.rsquared:.3f}, N = {int(m.nobs)}). Lines are 95% confidence "
         f"intervals. Most positions are consistent with one win per WAR; relief pitchers sit "
         f"above it. The model fits no better than total WAR alone (adjusted R² {m.rsquared_adj:.3f}). {SOURCE}")


def fig_correlation(raw):
    order = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP", "TotalWAR", "W"]
    labels = order[:-2] + ["Total WAR", "Wins"]
    c = raw[order].corr()
    mask = np.triu(np.ones_like(c, dtype=bool), k=0)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("div", ["#e34948", GRAY_MID, BLUE])
    fig, ax = plt.subplots(figsize=(WIDTH, 5.4))
    shown = np.where(mask, np.nan, c.values)
    shown, c_plot = shown[1:, :-1], None  # drop the empty first row / last column
    im = ax.imshow(shown, cmap=cmap, vmin=-1, vmax=1)
    for i in range(1, len(order)):
        for j in range(len(order) - 1):
            if not mask[i, j]:
                v = c.values[i, j]
                ax.text(j, i - 1, f"{v:.2f}".replace("-0.00", "0.00"), ha="center", va="center", fontsize=7,
                        color="white" if abs(v) > 0.6 else INK)
    ax.set_xticks(range(len(order) - 1), labels[:-1], rotation=45, ha="right")
    ax.set_yticks(range(len(order) - 1), labels[1:])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("Pearson correlation")
    cb.outline.set_visible(False)
    save(fig, "fig05_correlation_matrix",
         f"Correlations among positional WAR, total WAR, and wins (N = {len(raw)} team-seasons). "
         f"Total WAR correlates {c.loc['TotalWAR', 'W']:.2f} with wins; positions are nearly "
         f"independent of one another (no pair above "
         f"{c.loc[order[:11], order[:11]].where(~np.eye(11, dtype=bool)).max().max():.2f}). {SOURCE}")


def fig_payroll_vs_war(df, base):
    m = smf.ols("TotalWAR ~ Payroll", df).fit(cov_type="HC1")
    xs = pd.DataFrame({"Payroll": np.linspace(df["Payroll"].min(), df["Payroll"].max(), 100)})
    pr = m.get_prediction(xs).summary_frame(alpha=0.05)
    fig, ax = plt.subplots(figsize=(WIDTH, 3.8))
    ax.scatter(df["Payroll"], df["TotalWAR"], s=14, color=BLUE, alpha=0.55, edgecolor="white", linewidth=0.4)
    ax.fill_between(xs["Payroll"], pr["mean_ci_lower"], pr["mean_ci_upper"], color=ORANGE, alpha=0.18, lw=0)
    ax.plot(xs["Payroll"], pr["mean"], color=ORANGE, lw=2)
    resid = df["TotalWAR"] - m.predict(df)
    lab = pd.concat([df.loc[resid.nlargest(2).index], df.loc[resid.nsmallest(1).index],
                     df.loc[[df["Payroll"].idxmax()]]]).drop_duplicates(subset=["Year", "Team"])
    for _, r in lab.iterrows():
        short = r["Team"].split()[-1]
        if short == "Guardians" and r["Year"] < 2022:
            short = "Indians"
        ax.annotate(f"{r['Year']} {short}", (r["Payroll"], r["TotalWAR"]), xytext=(6, 4),
                    textcoords="offset points", fontsize=7.5, color=INK2,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    b = m.params["Payroll"]
    ax.text(0.98, 0.04, f"+{b * 10:.2f} WAR per \\$10M  (≈ \\${1 / b:.1f}M per WAR)\nR² = {m.rsquared:.3f}",
            transform=ax.transAxes, va="bottom", ha="right", fontsize=8.5,
            bbox=dict(fc="white", ec=GRID, boxstyle="round,pad=0.4"))
    ax.set_xlabel(f"Opening Day payroll ($M, {base} dollars)")
    ax.set_ylabel("Total team WAR")
    lo, hi = m.conf_int().loc["Payroll"]
    save(fig, "fig06_payroll_vs_war",
         f"Total team WAR against Opening Day payroll in {base} dollars (N = {int(m.nobs)}). "
         f"The line is the fitted regression with its 95% confidence band: about ${1 / b:.1f}M per WAR "
         f"(95% CI ${1 / hi:.1f}M–${1 / lo:.1f}M). Payroll explains only {m.rsquared * 100:.0f}% of "
         f"the variation in WAR. Payroll is scaled to {base} dollars by league-average payroll growth. {SOURCE}")


def fig_mediation(df):
    p_war = smf.ols("TotalWAR ~ Payroll", df).fit(cov_type="HC1")
    war_w = smf.ols("W ~ TotalWAR", df).fit(cov_type="HC1")
    tot = smf.ols("W ~ Payroll", df).fit(cov_type="HC1")
    both = smf.ols("W ~ Payroll + TotalWAR", df).fit(cov_type="HC1")
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    ax.set_xlim(0, 12); ax.set_ylim(0, 5.2); ax.axis("off")
    W, H = 2.2, 1.0
    boxes = {"Payroll": (0.2, 1.6), "Total WAR": (4.9, 3.9), "Wins": (9.6, 1.6)}
    for name, (x, y) in boxes.items():
        ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.08",
                                    fc="#cde2fb", ec=BLUE, lw=1))
        ax.text(x + W / 2, y + H / 2, name, ha="center", va="center", fontsize=10,
                weight="bold", color=INK)
    def arrow(p1, p2, color, ls="-"):
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12,
                                     color=color, lw=1.6, linestyle=ls, shrinkA=4, shrinkB=4))
    arrow((2.5, 2.7), (4.8, 4.2), BLUE)
    arrow((7.2, 4.2), (9.5, 2.7), BLUE)
    arrow((2.5, 2.1), (9.5, 2.1), MUTED, ls=(0, (4, 3)))
    ax.text(3.45, 3.75, f"{p_war.params['Payroll']:.3f} WAR\nper \\$1M{stars(p_war.pvalues['Payroll'])}",
            ha="right", va="center", fontsize=8.5, color=INK)
    ax.text(8.55, 3.75, f"{war_w.params['TotalWAR']:.2f} wins\nper WAR{stars(war_w.pvalues['TotalWAR'])}",
            ha="left", va="center", fontsize=8.5, color=INK)
    ax.text(6.0, 2.3, f"Direct effect, controlling for WAR: {both.params['Payroll']:.4f} "
            f"(p = {both.pvalues['Payroll']:.2f})", ha="center", va="bottom", fontsize=8.5, color=INK2)
    ax.text(6.0, 1.15, f"Total effect without WAR: {tot.params['Payroll']:.4f} wins per \\$1M"
            f"{stars(tot.pvalues['Payroll'])}", ha="center", va="top", fontsize=8.5, color=INK2)
    save(fig, "fig07_payroll_war_wins_chain",
         f"Payroll is associated with wins only through WAR. Solid arrows show the two links "
         f"(payroll → WAR, WAR → wins). The dashed arrow shows payroll's direct association with "
         f"wins once WAR is controlled for, which is indistinguishable from zero; without WAR, the "
         f"total association is {tot.params['Payroll']:.4f} wins per $1M. Robust (HC1) standard errors; "
         f"*** p < 0.01. N = {int(both.nobs)}. {SOURCE}")


def fig_war_per_10m(df, base):
    rows = []
    def add(label, model, term, section):
        b = model.params[term] * 10
        lo, hi = model.conf_int().loc[term] * 10
        rows.append((section, label, b, lo, hi, model.pvalues[term]))
    add("All payroll", smf.ols("TotalWAR ~ Payroll", df).fit(cov_type="HC1"), "Payroll", "Team")
    hp = smf.ols("TotalWAR ~ Hit_Pay + Pit_Pay", df).fit(cov_type="HC1")
    add("Pitcher payroll", hp, "Pit_Pay", "Hitters vs pitchers")
    add("Hitter payroll", hp, "Hit_Pay", "Hitters vs pitchers")
    labels = {"Starters": "Starting pitchers", "Relievers": "Relief pitchers", "Catcher": "Catcher",
              "Infield": "Infield", "Outfield": "Outfield", "DH": "Designated hitter"}
    for g in ["Starters", "Relievers", "Catcher", "Infield", "Outfield", "DH"]:
        add(labels[g], smf.ols(f"{g}_WAR ~ {g}_Pay", df).fit(cov_type="HC1"), f"{g}_Pay", "Position group")
    t = pd.DataFrame(rows, columns=["section", "label", "b", "lo", "hi", "p"])
    fig, ax = plt.subplots(figsize=(WIDTH, 3.9))
    y, ticks, labs = 0, [], []
    for sec in ["Team", "Hitters vs pitchers", "Position group"]:
        sub = t[t.section == sec]
        ax.text(-0.02, y - 0.05, sec, transform=ax.get_yaxis_transform(), ha="right", va="bottom",
                fontsize=8, weight="bold", color=INK)
        y -= 0.75
        for _, r in sub.iterrows():
            c = BLUE if r.lo > 0 else MUTED
            ax.plot([r.lo, r.hi], [y, y], color=c, lw=1.6, solid_capstyle="round")
            ax.plot(r.b, y, "o", color=c, ms=6, mec="white", mew=0.8)
            ticks.append(y); labs.append(r.label)
            y -= 0.75
        y -= 0.35
    ax.axvline(0, color=INK2, lw=0.9)
    ax.set_yticks(ticks, labs)
    ax.set_ylim(y + 0.4, 0.3)
    ax.set_xlabel(f"WAR per additional $10M of payroll ({base} dollars), with 95% CI")
    ax.grid(axis="y", visible=False)
    ax.plot([], [], "o-", color=MUTED, label="CI includes zero")
    ax.legend(loc="lower right", frameon=False)
    hit, pit = t.loc[t.label == "Hitter payroll"].iloc[0], t.loc[t.label == "Pitcher payroll"].iloc[0]
    test = hp.t_test("Hit_Pay - Pit_Pay = 0").pvalue
    save(fig, "fig08_war_per_10m",
         f"WAR associated with an additional $10M of payroll. Team: total WAR on total payroll. "
         f"Hitters vs pitchers: total WAR on hitter and pitcher payroll together (pitchers "
         f"{pit.b:.2f}, hitters {hit.b:.2f}; test of equal slopes p = {float(test):.2f}). Position group: "
         f"each group's WAR on that group's own payroll, attenuated by the mismatch between salary "
         f"positions and where WAR is earned. Gray = 95% CI includes zero. Robust (HC1) standard errors. {SOURCE}")


def fig_robustness(df, base):
    specs = [("Pooled OLS", "TotalWAR ~ Payroll"), ("Team fixed effects", "TotalWAR ~ Payroll + C(Team)"),
             ("Year fixed effects", "TotalWAR ~ Payroll + C(Year)")]
    rows = []
    for lab, f in specs:
        r = smf.ols(f, df).fit(cov_type="HC1")
        rows.append((lab, *(np.r_[r.params["Payroll"], r.conf_int().loc["Payroll"]] * 10)))
    by = []
    for yr, d in df.groupby("Year"):
        r = smf.ols("TotalWAR ~ Payroll", d).fit(cov_type="HC1")
        by.append((yr, *(np.r_[r.params["Payroll"], r.conf_int().loc["Payroll"]] * 10)))
    by = pd.DataFrame(by, columns=["Year", "b", "lo", "hi"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(WIDTH, 3.0), sharey=True,
                                 gridspec_kw={"width_ratios": [1, 2.4], "wspace": 0.08})
    pooled = rows[0][1]
    for ax in (a1, a2):
        ax.axhline(0, color=INK2, lw=0.9)
        ax.axhline(pooled, color=ORANGE, lw=1, ls=(0, (3, 3)))
        ax.grid(axis="x", visible=False)
    for i, (lab, b, lo, hi) in enumerate(rows):
        a1.plot([i, i], [lo, hi], color=BLUE, lw=1.6, solid_capstyle="round")
        a1.plot(i, b, "o", color=BLUE, ms=6, mec="white", mew=0.8)
    a1.set_xticks(range(len(rows)), ["Pooled", "Team FE", "Year FE"], fontsize=7.5)
    a1.set_xlim(-0.6, len(rows) - 0.4)
    a1.set_title("A. Specification", loc="left", fontsize=9, color=INK)
    a1.set_ylabel(f"WAR per $10M ({base} dollars)")
    xs = np.arange(len(by))
    for x, r in zip(xs, by.itertuples()):
        a2.plot([x, x], [r.lo, r.hi], color=BLUE, lw=1.4, solid_capstyle="round")
        a2.plot(x, r.b, "o", color=BLUE, ms=5, mec="white", mew=0.8)
    a2.set_xticks(xs, [str(y) for y in by["Year"]], rotation=45, fontsize=7.5)
    a2.set_title("B. Each season separately (30 teams)", loc="left", fontsize=9, color=INK)
    a2.plot([], [], color=ORANGE, lw=1, ls=(0, (3, 3)), label="Pooled estimate")
    a2.legend(loc="upper left", frameon=False)
    top = max(by["hi"].max(), max(r[3] for r in rows))
    a1.set_ylim(None, top + 0.35)
    save(fig, "fig09_robustness",
         f"Robustness of the payroll–WAR estimate. Panel A: pooled estimate ({pooled:.2f} WAR per $10M, "
         f"dashed line) and with team or year fixed effects. Panel B: the same regression run on each "
         f"season alone; single seasons are noisy (range {by.b.min():.2f}–{by.b.max():.2f}), which "
         f"supports pooling. Bars are 95% confidence intervals (robust HC1 standard errors). {SOURCE}")


def fig_win_spread(raw):
    sd = raw["W"].std()
    r = np.corrcoef(raw["Cots_OD_Payroll_Rel"], raw["W"])[0, 1]
    no_pay = sd * np.sqrt(1 - r * r)
    luck = 81 / np.sqrt(162)          # SD of wins for a .500 team over 162 games
    vals = [("Actual spread of wins", sd), ("If payroll differences\nwere removed", no_pay),
            ("Luck alone\n(every team .500)", luck)]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    y = np.arange(len(vals))[::-1]
    colors = [BLUE, BLUE, MUTED]
    ax.barh(y, [v for _, v in vals], height=0.55, color=colors, edgecolor="white", linewidth=1)
    for yi, (_, v) in zip(y, vals):
        ax.text(v + 0.15, yi, f"{v:.1f} wins", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y, [l for l, _ in vals])
    ax.set_xlabel("Standard deviation of team wins")
    ax.set_xlim(0, sd * 1.18)
    ax.grid(axis="y", visible=False)
    save(fig, "fig10_win_spread",
         f"How much of the spread in team wins payroll can explain. The actual standard deviation of "
         f"wins is {sd:.1f}. Payroll (relative to the league average) explains {r * r * 100:.0f}% of "
         f"the variance in wins, so removing payroll differences entirely would lower the spread only "
         f"to about {no_pay:.1f} wins. Pure luck over 162 games produces {luck:.1f}. {SOURCE}")


# ---------------- tables ----------------
def fmt(model, term, robust_note=False):
    if term not in model.params:
        return ""
    b, se = model.params[term], model.bse[term]
    d = 3 if abs(b) >= 0.01 else 4          # keep tiny coefficients visible
    return f"{b:.{d}f}{stars(model.pvalues[term])} ({se:.{d}f})"


def tables(raw, df, base):
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    # Table 1: descriptive statistics
    desc = pd.DataFrame({
        "Wins": raw["W"], "Total WAR": raw["TotalWAR"],
        "Hitter WAR": df["Hit_WAR"], "Pitcher WAR": df["Pit_WAR"],
        "Payroll ($M, nominal)": raw["Cots_OD_Payroll"] / 1e6,
        f"Payroll ($M, {base} dollars)": df["Payroll"],
        f"Hitter payroll ($M, {base} $)": df["Hit_Pay"],
        f"Pitcher payroll ($M, {base} $)": df["Pit_Pay"],
    }).describe().T[["count", "mean", "std", "min", "50%", "max"]]
    desc.columns = ["N", "Mean", "SD", "Min", "Median", "Max"]
    desc["N"] = desc["N"].astype(int)
    desc.round(2).to_csv(config.TABLES_DIR / "table1_descriptive_statistics.csv")

    # Table 2: WAR -> wins
    m1 = sm.OLS(raw["W"], sm.add_constant(raw[["TotalWAR"]])).fit()
    cols = config.REGRESSION_POS_COLS
    m2 = sm.OLS(raw["W"], sm.add_constant(raw[cols])).fit()
    t2 = pd.DataFrame({"(1) Total WAR": [fmt(m1, t) for t in ["const", "TotalWAR"] + cols],
                       "(2) Positional WAR": [fmt(m2, t) for t in ["const", "TotalWAR"] + cols]},
                      index=["Intercept", "Total WAR"] + cols)
    stats = pd.DataFrame({"(1) Total WAR": [f"{m1.rsquared:.3f}", f"{m1.rsquared_adj:.3f}", f"{m1.aic:.0f}", int(m1.nobs)],
                          "(2) Positional WAR": [f"{m2.rsquared:.3f}", f"{m2.rsquared_adj:.3f}", f"{m2.aic:.0f}", int(m2.nobs)]},
                         index=["R²", "Adjusted R²", "AIC", "N"])
    pd.concat([t2, stats]).to_csv(config.TABLES_DIR / "table2_war_to_wins.csv")

    # Table 3: salary models
    f = lambda x: smf.ols(x, df).fit(cov_type="HC1")
    ms = {"(1) WAR": f("TotalWAR ~ Payroll"), "(2) WAR, team FE": f("TotalWAR ~ Payroll + C(Team)"),
          "(3) WAR, year FE": f("TotalWAR ~ Payroll + C(Year)"), "(4) Wins": f("W ~ Payroll"),
          "(5) Wins": f("W ~ Payroll + TotalWAR"), "(6) WAR": f("TotalWAR ~ Hit_Pay + Pit_Pay")}
    terms = [("Payroll ($M)", "Payroll"), ("Total WAR", "TotalWAR"),
             ("Hitter payroll ($M)", "Hit_Pay"), ("Pitcher payroll ($M)", "Pit_Pay"), ("Intercept", "Intercept")]
    t3 = pd.DataFrame({k: [fmt(m, t) for _, t in terms] for k, m in ms.items()}, index=[l for l, _ in terms])
    extra = pd.DataFrame({k: ["Yes" if "Team" in m.model.formula else "No",
                              "Yes" if "Year" in m.model.formula else "No",
                              f"{m.rsquared:.3f}", int(m.nobs)] for k, m in ms.items()},
                         index=["Team fixed effects", "Year fixed effects", "R²", "N"])
    pd.concat([t3, extra]).to_csv(config.TABLES_DIR / "table3_salary_models.csv")
    print("   saved tables 1-3")


def write_captions(base):
    lines = ["# Figure captions", "",
             f"Payroll in dollar terms of {base} unless marked nominal. Regression tables report "
             "coefficients with standard errors in parentheses; * p < 0.10, ** p < 0.05, *** p < 0.01. "
             "Salary models (Table 3) use robust (HC1) standard errors; WAR-to-wins models (Table 2) "
             "use conventional standard errors.", ""]
    for i, (name, cap) in enumerate(CAPTIONS, 1):
        lines += [f"**Figure {i}** ({name}). {cap}", ""]
    (config.FIGURES_DIR / "figure_captions.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    raw, df, base = load()
    print(f"Building figures ({len(raw)} team-seasons, dollars in {base} terms)")
    fig_payroll_over_time(raw)
    fig_payroll_shares()
    fig_wins_vs_war(raw)
    fig_positional_coefficients(raw)
    fig_correlation(raw)
    fig_payroll_vs_war(df, base)
    fig_mediation(df)
    fig_war_per_10m(df, base)
    fig_robustness(df, base)
    fig_win_spread(raw)
    tables(raw, df, base)
    write_captions(base)
    print(f"Saved figures to {config.FIGURES_DIR} and tables to {config.TABLES_DIR}")


if __name__ == "__main__":
    main()
