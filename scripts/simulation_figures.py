"""
Step 8: figures for the competitive balance metrics and the cap/floor simulation.

Builds on the outputs of balance_metrics.py and simulate.py, in the same style
as figures.py (300-dpi PNG and vector PDF in figures/). Figures are numbered
after the analysis figures (11 onward), and captions with source notes go to
figures/simulation_figure_captions.md.

Unless a figure says otherwise, results are for the main specification: MLB's
2027 proposal scaled to each season, floor clubs buying only talent the cap
releases, leftover talent placed by cap room, at $14.4M per WAR.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import config
import figures as base          # shared style, colors, save()
import simulate
import team_names
import thresholds

BLUE, ORANGE, AQUA = base.BLUE, base.ORANGE, base.AQUA
INK, INK2, MUTED, GRID, AXIS = base.INK, base.INK2, base.MUTED, base.GRID, base.AXIS
WIDTH = base.WIDTH
SOURCE = ("Data: Baseball-Reference; Cot's Baseball Contracts (Baseball Prospectus). "
          "Simulation: 2,000 seasons per real season, 2019–2026.")

SCENARIOS = list(simulate.SCENARIOS)
SCENARIO_COLOR = {"Status quo": MUTED, "Cap only": BLUE, "Floor only": AQUA, "Cap + floor": ORANGE}
MAIN = simulate.MAIN
MAIN_PRICE = MAIN["Price_M_per_WAR"]
FIRST_FIGURE = 11
EXAMPLE_SEASON = 2024


def load():
    res = pd.read_csv(simulate.SIMULATION_FILE)
    clear = pd.read_csv(simulate.CLEARING_FILE)
    teams = pd.read_csv(simulate.TEAM_WAR_FILE)
    balance = pd.read_csv(config.RESULTS_DIR / "balance_by_season.csv")
    return res, clear, teams, balance


def pick(df, **fixed):
    """Rows matching the main specification, with any field overridden."""
    spec = {k: v for k, v in MAIN.items() if k in df.columns}
    spec.update(fixed)
    keep = np.ones(len(df), dtype=bool)
    for k, v in spec.items():
        if v is not None:
            keep &= (df[k] == v).values
    return df[keep]


def by_scenario(res, value):
    """Mean over seasons at the main price, plus the range across prices."""
    allp = pick(res, Price_M_per_WAR=None)
    per_price = allp.groupby(["Scenario", "Price_M_per_WAR"])[value].mean().unstack()
    out = pd.DataFrame({"main": per_price[MAIN_PRICE],
                        "lo": per_price.min(axis=1), "hi": per_price.max(axis=1)})
    return out.reindex(SCENARIOS)


CAPTIONS = []


def save(fig, name, caption):
    base.save(fig, name, caption)
    CAPTIONS.append((name, caption))


# ---------------------------------------------------------------- figures
def fig_headline(res, balance):
    ns = by_scenario(res, "NollScully")
    gap = by_scenario(res, "Playoff_Gap_Q4_Q1") * 100
    actual = balance.loc[balance.Year >= 2019, "NollScully"].mean()

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(WIDTH, 2.9), sharey=True,
                                 gridspec_kw={"wspace": 0.08})
    y = np.arange(len(SCENARIOS))[::-1]
    for ax, t, fmt in ((a1, ns, "{:.2f}"), (a2, gap, "{:.1f}")):
        for yi, sc in zip(y, SCENARIOS):
            r = t.loc[sc]
            ax.barh(yi, r.main, height=0.6, color=SCENARIO_COLOR[sc], edgecolor="white", linewidth=1)
            ax.plot([r.lo, r.hi], [yi + 0.38, yi + 0.38], color=INK2, lw=1.1, solid_capstyle="round")
            for end in (r.lo, r.hi):
                ax.plot([end, end], [yi + 0.31, yi + 0.45], color=INK2, lw=1.1)
            ax.text(r.main - (0.01 if ax is a1 else 0.6), yi - 0.02, fmt.format(r.main), va="center",
                    ha="right", fontsize=8, color="white", weight="bold")
        ax.grid(axis="y", visible=False)
    a1.set_yticks(y, SCENARIOS)
    a1.axvline(actual, color=INK2, lw=0.9, ls=(0, (3, 3)), zorder=0.9)   # behind the bars
    a1.text(actual + 0.005, len(SCENARIOS) - 0.25, f"actual\n2019–26: {actual:.2f}", fontsize=7,
            color=INK2, va="bottom", ha="left")
    a1.set_xlim(1.8, ns.hi.max() + 0.15)
    a1.set_xlabel("Noll-Scully ratio (lower = more balanced)")
    a1.set_title("A. Within-season balance", loc="left", fontsize=9)
    a2.set_xlim(0, gap.hi.max() + 6)
    a2.set_xlabel("Playoff rate gap, top vs bottom payroll quartile (pts)")
    a2.set_title("B. Playoff access", loc="left", fontsize=9)
    a1.set_ylim(-0.6, len(SCENARIOS) + 0.35)

    sq, cf = ns.loc["Status quo", "main"], ns.loc["Cap + floor", "main"]
    gsq, gcf = gap.loc["Status quo", "main"], gap.loc["Cap + floor", "main"]
    save(fig, f"fig{FIRST_FIGURE}_simulation_headline",
         f"Competitive balance under each payroll rule (main specification). Panel A: Noll-Scully "
         f"ratio, the spread of winning percentage relative to pure luck; cap + floor lowers it from "
         f"{sq:.2f} to {cf:.2f} ({(cf - sq) / sq * 100:+.0f}%). The dashed line is the actual "
         f"2019–2026 average ({actual:.2f}); the simulated status quo sits slightly above it. "
         f"Panel B: percentage-point gap in playoff rate between clubs in the top and bottom "
         f"payroll quartiles; cap + floor narrows it from {gsq:.1f} to {gcf:.1f} points. Bars are "
         f"at $14.4M per WAR; lines span results at $11M–$20M per WAR. {SOURCE}")


def fig_playoff_by_quartile(res):
    m = pick(res).groupby("Scenario")[[f"Playoff_Rate_Q{q}" for q in (1, 2, 3, 4)]].mean() * 100
    m = m.reindex(SCENARIOS)
    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    width = 0.19
    x = np.arange(4)
    for i, sc in enumerate(SCENARIOS):
        ax.bar(x + (i - 1.5) * width, m.loc[sc].values, width=width * 0.92,
               color=SCENARIO_COLOR[sc], label=sc, edgecolor="white", linewidth=0.8)
    for xi in x:
        for sc, dx in (("Status quo", -1.5), ("Cap + floor", 1.5)):
            v = m.loc[sc].iloc[xi]
            ax.text(xi + dx * width, v + 0.8, f"{v:.0f}", ha="center", fontsize=7, color=INK2)
    ax.set_xticks(x, ["Lowest\npayroll quartile", "Second", "Third", "Highest\npayroll quartile"])
    ax.set_ylabel("Simulated playoff rate (%)")
    ax.set_ylim(0, m.values.max() * 1.15)
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=4, loc="upper left", frameon=False, fontsize=7.5)
    lo_sq, lo_cf = m.loc["Status quo"].iloc[0], m.loc["Cap + floor"].iloc[0]
    hi_sq, hi_cf = m.loc["Status quo"].iloc[3], m.loc["Cap + floor"].iloc[3]
    save(fig, f"fig{FIRST_FIGURE + 1}_playoff_rate_by_quartile",
         f"Simulated playoff rate by club payroll quartile under each rule (main specification, "
         f"$14.4M per WAR). Quartiles are each club's status-quo CBT payroll rank within its season. "
         f"Cap + floor raises the lowest quartile from {lo_sq:.0f}% to {lo_cf:.0f}% and lowers the "
         f"highest from {hi_sq:.0f}% to {hi_cf:.0f}%; a floor alone leaves rates unchanged because, in "
         f"the main specification, floor clubs can buy only talent a cap releases. {SOURCE}")


def fig_binding(clear):
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.9), sharey=True, gridspec_kw={"wspace": 0.08})
    lim = {}
    for ax, basis, title in ((axes[0], thresholds.SCALED, "A. Scaled to each season (main)"),
                             (axes[1], thresholds.FIXED, "B. Fixed 2027 dollars")):
        c = pick(clear, Thresholds=basis, Scenario="Cap + floor").sort_values("Year")
        lim[basis] = c
        x = np.arange(len(c))
        ax.bar(x, c.Clubs_Over_Cap, color=BLUE, width=0.6, label="Over the cap", edgecolor="white")
        ax.bar(x, -c.Clubs_Below_Floor, color=ORANGE, width=0.6, label="Under the floor", edgecolor="white")
        for xi, (o, u) in enumerate(zip(c.Clubs_Over_Cap, c.Clubs_Below_Floor)):
            if o:
                ax.text(xi, o + 0.4, str(int(o)), ha="center", fontsize=7, color=INK2)
            ax.text(xi, -u - 0.4, str(int(u)), ha="center", va="top", fontsize=7, color=INK2)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xticks(x, [str(y) for y in c.Year], rotation=45, fontsize=7.5)
        ax.set_title(title, loc="left", fontsize=9)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Clubs bound by the rule")
    ticks = np.arange(-20, 21, 5)
    axes[0].set_yticks(ticks, [str(abs(t)) for t in ticks])
    axes[0].set_ylim(-24, 17)
    axes[1].legend(loc="upper left", frameon=False, fontsize=7.5)
    s, f = lim[thresholds.SCALED], lim[thresholds.FIXED]
    save(fig, f"fig{FIRST_FIGURE + 2}_clubs_bound_by_season",
         f"Clubs over the cap (up) and under the floor (down) each season, CBT payroll, MLB's 2027 "
         f"proposal. Panel A restates the proposal as multiples of league-average payroll "
         f"(cap 1.14x, floor 0.80x) and applies them to each season: {int(s.Clubs_Over_Cap.min())}–"
         f"{int(s.Clubs_Over_Cap.max())} clubs over the cap and {int(s.Clubs_Below_Floor.min())}–"
         f"{int(s.Clubs_Below_Floor.max())} under the floor every season. Panel B applies the fixed "
         f"2027 dollar amounts to past payrolls, which puts {int(f.Clubs_Below_Floor.max())} clubs under "
         f"the floor in the earliest seasons because payrolls were lower then, not because the rule "
         f"binds harder. {SOURCE}")


def fig_talent_movement(teams, season=EXAMPLE_SEASON):
    t = pick(teams, Scenario="Cap + floor", Year=season).sort_values("CBT_Payroll_M", ascending=False)
    cap, floor = t.Cap_M.iloc[0], t.Floor_M.iloc[0]
    status = np.where(t.CBT_Payroll_M > cap, "Over the cap",
                      np.where(t.CBT_Payroll_M < floor, "Under the floor", "Between"))
    colors = {"Over the cap": BLUE, "Between": MUTED, "Under the floor": ORANGE}
    fig, ax = plt.subplots(figsize=(WIDTH, 6.4))
    y = np.arange(len(t))[::-1]
    ax.barh(y, t.WAR_Change, height=0.7, color=[colors[s] for s in status], edgecolor="white")
    for yi, v in zip(y, t.WAR_Change):
        ax.text(v + (0.15 if v >= 0 else -0.15), yi, f"{v:+.1f}", va="center",
                ha="left" if v >= 0 else "right", fontsize=7, color=INK2)
    labels = [f"{team.replace('Los Angeles', 'LA')}  (${p:.0f}M)"
              for team, p in zip(t.Team, t.CBT_Payroll_M)]
    ax.set_yticks(y, labels, fontsize=7.5)
    ax.axvline(0, color=INK2, lw=0.8)
    # Separators at the cap and the floor
    n_over = int((status == "Over the cap").sum())
    n_under = int((status == "Under the floor").sum())
    for pos, text in ((len(t) - n_over - 0.5, f"cap ${cap:.1f}M"), (n_under - 0.5, f"floor ${floor:.1f}M")):
        ax.axhline(pos, color=AXIS, lw=0.8, ls=(0, (3, 3)))
        ax.text(t.WAR_Change.min() - 1.3, pos - 0.12, text, va="top", ha="left", fontsize=7.5,
                color=INK2)
    ax.set_xlim(t.WAR_Change.min() - 1.5, t.WAR_Change.max() + 1.5)
    ax.set_ylim(-0.6, len(t) - 0.4)
    ax.set_xlabel("Change in WAR under cap + floor")
    ax.grid(axis="y", visible=False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=colors[s], label=s) for s in ("Over the cap", "Between", "Under the floor")],
              loc="lower left", frameon=False, fontsize=7.5)
    lost = t.loc[status == "Over the cap", "WAR_Change"].sum()
    top = t.iloc[0]
    save(fig, f"fig{FIRST_FIGURE + 3}_talent_movement_{season}",
         f"Simulated change in each club's WAR under cap + floor, {season} (main specification; CBT "
         f"payroll in parentheses). Clubs over the ${cap:.1f}M cap shed {abs(lost):.1f} WAR in total, "
         f"led by the {top.Team} ({top.WAR_Change:+.1f}); clubs under the ${floor:.1f}M floor gain what "
         f"their mandated spending buys, and talent left over goes to clubs between the thresholds in "
         f"proportion to their room under the cap. One WAR is worth about one win. {SOURCE}")


def fig_gap_by_season(res):
    m = pick(res).pivot_table(index="Year", columns="Scenario", values="Playoff_Gap_Q4_Q1") * 100
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    x = np.arange(len(m))
    for xi, (_, r) in zip(x, m.iterrows()):
        ax.plot([xi, xi], [r["Status quo"], r["Cap + floor"]], color=AXIS, lw=2, zorder=1)
    ax.scatter(x, m["Status quo"], s=36, color=MUTED, zorder=2, label="Status quo", edgecolor="white")
    ax.scatter(x, m["Cap + floor"], s=36, color=ORANGE, zorder=3, label="Cap + floor", edgecolor="white")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(x, [str(y) for y in m.index])
    ax.set_ylabel("Playoff rate gap, top vs\nbottom payroll quartile (pts)")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False)
    lo, hi = m["Cap + floor"].idxmin(), m["Cap + floor"].idxmax()
    save(fig, f"fig{FIRST_FIGURE + 4}_playoff_gap_by_season",
         f"Playoff rate gap between top- and bottom-quartile payroll clubs, by season, under the "
         f"status quo and cap + floor (main specification). The rule narrows the gap in every season, "
         f"but by very different amounts: under cap + floor the gap ranges from "
         f"{m.loc[lo, 'Cap + floor']:.1f} points in {lo} (low-payroll clubs ahead) to "
         f"{m.loc[hi, 'Cap + floor']:.1f} in {hi}, because each season starts from that year's real "
         f"rosters and payrolls. {SOURCE}")


def fig_robustness(res):
    rows = []
    for proposal in thresholds.PROPOSALS:
        for basis in thresholds.THRESHOLD_BASES:
            for supply in simulate.FLOOR_SUPPLY:
                sub = res[(res.Proposal == proposal) & (res.Thresholds == basis) & (res.Floor_Supply == supply)]
                g = sub.groupby(["Scenario", "Price_M_per_WAR"]).Playoff_Gap_Q4_Q1.mean().unstack() * 100
                label = (f"{proposal.replace('MLB ', '').replace(' proposal', '')}, "
                         f"{'scaled' if basis == thresholds.SCALED else 'fixed $'}, "
                         f"{'capped clubs only' if supply == simulate.CAPPED_ONLY else 'open market'}")
                is_main = (proposal == MAIN["Proposal"] and basis == MAIN["Thresholds"]
                           and supply == MAIN["Floor_Supply"])
                rows.append((label + ("  (main)" if is_main else ""), g, is_main))
    sq = pick(res, Scenario="Status quo").groupby("Year").Playoff_Gap_Q4_Q1.mean().mean() * 100

    fig, ax = plt.subplots(figsize=(WIDTH, 3.8))
    y = np.arange(len(rows))[::-1]
    for yi, (label, g, is_main) in zip(y, rows):
        for sc, dy in (("Cap only", 0.15), ("Cap + floor", -0.15), ("Floor only", 0.0)):
            if sc == "Floor only":
                continue
            r = g.loc[sc]
            ax.plot([r.min(), r.max()], [yi + dy, yi + dy], color=SCENARIO_COLOR[sc], lw=1.4)
            ax.plot(r[MAIN_PRICE], yi + dy, "o", color=SCENARIO_COLOR[sc], ms=5.5, mec="white", mew=0.7)
        fo = g.loc["Floor only"]
        ax.plot(fo[MAIN_PRICE], yi, "D", color=AQUA, ms=4, mec="white", mew=0.6)
    ax.axvline(sq, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.text(sq - 0.4, -0.55, f"status quo\n{sq:.0f}", fontsize=7, color=INK2, ha="right", va="bottom")
    ax.set_yticks(y, [r[0] for r in rows], fontsize=7.5)
    for tick, (_, _, is_main) in zip(ax.get_yticklabels(), rows):
        if is_main:
            tick.set_fontweight("bold")
    ax.set_ylim(-0.7, len(rows) - 0.1)
    lowest = min(g.loc[["Cap only", "Cap + floor"]].values.min() for _, g, _ in rows)
    ax.set_xlim(min(0, lowest) - 1, sq + 6)
    ax.set_xlabel("Playoff rate gap, top vs bottom payroll quartile (pts)")
    ax.grid(axis="y", visible=False)
    ax.plot([], [], "o-", color=BLUE, label="Cap only")
    ax.plot([], [], "o-", color=ORANGE, label="Cap + floor")
    ax.plot([], [], "D", color=AQUA, label="Floor only")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False, fontsize=7.5)
    save(fig, f"fig{FIRST_FIGURE + 5}_simulation_robustness",
         f"Playoff rate gap under each rule across every specification: MLB's 2027 or 2028 proposal, "
         f"thresholds scaled to each season or fixed in dollars, and floor clubs buying only talent the "
         f"cap releases or competing for talent on the open market. Dots are at $14.4M per WAR; lines "
         f"span $11M–$20M. Under scaled thresholds, a cap (with or without a floor) narrows the gap by "
         f"about half in every specification, while a floor alone narrows it only when floor clubs can "
         f"bid talent away from other clubs (open market). "
         f"Fixed-dollar thresholds with an open-market floor produce the largest effects, because they put "
         f"most clubs under the floor in early seasons. The dashed line is the status quo ({sq:.0f} points). "
         f"{SOURCE}")


# ------------------------------------------------------------------ table
TABLE_FILE = config.TABLES_DIR / "table4_simulation_results.csv"
TABLE_NOTE = []


def actual_row(teams, balance):
    """Actual 2019-2026 MLB, measured the same way as the simulated rows:
    Noll-Scully and SD of wins averaged over seasons, playoff rates by each
    club's CBT payroll quartile within its season."""
    sq = pick(teams, Scenario="Status quo")[["Year", "Team", "Payroll_Quartile"]]
    playoffs = pd.read_csv(config.RAW_DIR / "playoffs" / "playoffs.csv")
    playoffs["Team"] = playoffs["Team"].apply(team_names.normalize_team_name)
    made = set(zip(playoffs["Year"], playoffs["Team"]))
    sq = sq.assign(Playoffs=[(y, t) in made for y, t in zip(sq["Year"], sq["Team"])])
    rates = sq.groupby("Payroll_Quartile")["Playoffs"].mean()
    seasons = balance[balance["Year"].isin(sq["Year"].unique())]
    row = {"NollScully": seasons["NollScully"].mean(), "SD_Wins": seasons["SD_Wins"].mean()}
    row.update({f"Playoff_Rate_Q{q}": rates[q] for q in range(1, 5)})
    row["Playoff_Gap_Q4_Q1"] = rates[4] - rates[1]
    return row


def table_results(res, teams, balance):
    """Table 4: balance and playoff access under each rule (main specification),
    with the actual 2019-2026 league for comparison."""
    measures = ["NollScully", "SD_Wins"] + [f"Playoff_Rate_Q{q}" for q in range(1, 5)] \
        + ["Playoff_Gap_Q4_Q1"]
    main = pick(res).groupby("Scenario")[measures].mean().reindex(SCENARIOS)
    gap = by_scenario(res, "Playoff_Gap_Q4_Q1") * 100
    ns = by_scenario(res, "NollScully")

    actual = actual_row(teams, balance)
    rows = [("Actual MLB, 2019-2026", actual, None, None)] + \
           [(sc, main.loc[sc], ns.loc[sc], gap.loc[sc]) for sc in SCENARIOS]

    out = []
    for label, r, ns_rng, gap_rng in rows:
        out.append({
            "": label,
            "Noll-Scully": f"{r['NollScully']:.2f}",
            "SD of wins": f"{r['SD_Wins']:.1f}",
            **{f"Playoff rate, payroll Q{q}": f"{r[f'Playoff_Rate_Q{q}'] * 100:.1f}%"
               for q in range(1, 5)},
            "Playoff gap, Q4 - Q1 (pts)": f"{r['Playoff_Gap_Q4_Q1'] * 100:.1f}",
            "Noll-Scully, $11M-$20M per WAR": "" if ns_rng is None
                else f"{ns_rng['lo']:.2f}-{ns_rng['hi']:.2f}",
            "Playoff gap, $11M-$20M per WAR": "" if gap_rng is None
                else f"{gap_rng['lo']:.1f}-{gap_rng['hi']:.1f}",
        })
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_csv(TABLE_FILE, index=False)

    sq, cf = main.loc["Status quo"], main.loc["Cap + floor"]
    TABLE_NOTE.append(
        f"**Table 4** ({TABLE_FILE.stem}). Competitive balance and playoff access under each "
        f"rule, 2019-2026 (main specification, {SEASONS_TEXT}). Simulated rows are means over "
        f"seasons of {simulate.SEASONS_SIMULATED:,} simulated 162-game seasons each at "
        f"${MAIN_PRICE}M per WAR; the last two columns give the range across $11M, $14.4M and "
        f"$20M per WAR. Payroll quartiles are each club's CBT payroll quartile within its season "
        f"under the status quo (Q1 lowest). The first row is the actual league, measured the "
        f"same way. Noll-Scully is the SD of win percentage divided by the SD luck alone "
        f"produces over 162 games (1.0 = perfect balance). The simulated status quo "
        f"(Noll-Scully {sq['NollScully']:.2f}; gap {sq['Playoff_Gap_Q4_Q1'] * 100:.1f} points) is "
        f"close to the actual league ({actual['NollScully']:.2f}; "
        f"{actual['Playoff_Gap_Q4_Q1'] * 100:.1f} points). Cap + floor lowers Noll-Scully to "
        f"{cf['NollScully']:.2f} and the playoff gap to {cf['Playoff_Gap_Q4_Q1'] * 100:.1f} "
        f"points. {SOURCE}")


SEASONS_TEXT = "seasons 2019, 2021-2026"


def write_captions():
    lines = ["# Simulation figure and table captions", "",
             "Main specification unless noted: MLB's 2027 proposal ($245.3M cap / $171.2M floor) "
             "restated as multiples of league-average CBT payroll and applied to each season; floor "
             "clubs buy only talent the cap releases; leftover talent goes to clubs between the "
             "thresholds in proportion to their room under the cap; $14.4M per WAR.", ""]
    for i, (name, cap) in enumerate(CAPTIONS, FIRST_FIGURE):
        lines += [f"**Figure {i}** ({name}). {cap}", ""]
    for note in TABLE_NOTE:
        lines += [note, ""]
    (config.FIGURES_DIR / "simulation_figure_captions.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    res, clear, teams, balance = load()
    print("Building simulation figures")
    fig_headline(res, balance)
    fig_playoff_by_quartile(res)
    fig_binding(clear)
    fig_talent_movement(teams)
    fig_gap_by_season(res)
    fig_robustness(res)
    table_results(res, teams, balance)
    write_captions()
    print(f"Saved simulation figures and captions to {config.FIGURES_DIR}")
    print(f"Saved {TABLE_FILE.name} to {config.TABLES_DIR}")


if __name__ == "__main__":
    main()
