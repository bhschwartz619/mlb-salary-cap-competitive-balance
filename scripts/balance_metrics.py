"""
Step 6: competitive balance metrics, and who a cap/floor would actually bind.

Three jobs, all from files the pipeline already produces or that live in data/raw.

1. The within-season baseline. Every simulated scenario gets compared against
   actual MLB, so actual MLB needs its own numbers first. Per season:
     SD of win%        raw spread of team quality
     Noll-Scully       that spread divided by the spread luck alone would
                       produce over a 162-game season (0.5 / sqrt(G)).
                       1.0 = a league of identical teams; higher = less balance.
     Gini (wins)       inequality of wins across the 30 teams
     Gini (payroll)    the same for Opening Day payroll
     Payroll CV        payroll SD / payroll mean, a scale-free spread measure

2. Who a cap and floor would bind. Counts teams above the cap and below the
   floor in a given season, and the dollars each side would move.

   Caveat worth keeping in the methods section: MLB's proposed thresholds are
   defined on CBT payroll (AAV over the 40-man roster plus benefits), which
   runs 12-20% above Opening Day payroll and varies by team with contract
   structure. Until CBT payroll is parsed from Cot's sheets, this reports the
   OD-basis count plus two scaled approximations, so the sensitivity is visible
   rather than hidden.

3. Dynamic balance, from playoff appearances. Within-season spread can stay
   flat while the same clubs monopolize October, and only these measures catch
   it. Distinct franchises per rolling window, concentration of appearances,
   repeat-appearance rate, and postseason rate by payroll quartile. Skipped
   with a message if data/raw/playoffs/playoffs.csv is absent.
"""
import numpy as np
import pandas as pd

import config
import team_names

# MLB's reported 2027 proposal, $M. Change these to test other thresholds.
CAP_M = 245.3
FLOOR_M = 171.2

# CBT payroll runs above Opening Day payroll. Until it is parsed, the binding
# counts are reported on the OD basis and at these two scalings of it.
CBT_SCALINGS = (1.00, 1.12, 1.20)

# Rolling window, in seasons, for "how many different clubs reached October".
WINDOW = 3

RAW_PLAYOFFS_FILE = config.RAW_DIR / "playoffs" / "playoffs.csv"

BALANCE_BY_SEASON_FILE = config.RESULTS_DIR / "balance_by_season.csv"
CAP_FLOOR_BINDING_FILE = config.RESULTS_DIR / "cap_floor_binding.csv"
PLAYOFF_CONCENTRATION_FILE = config.RESULTS_DIR / "playoff_concentration.csv"
PLAYOFF_BY_PAYROLL_FILE = config.RESULTS_DIR / "playoff_rate_by_payroll.csv"

# How far a club got. Ordered worst to best; used to rank and to flag rounds.
RESULT_ORDER = ["WC", "DS", "CS", "WS", "Champion"]


def gini(values):
    """Gini coefficient. 0 = everyone equal, 1 = one team has everything."""
    x = np.sort(np.asarray(values, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return np.nan
    return 2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum()) - (n + 1) / n


def hhi(counts):
    """Herfindahl-Hirschman index of shares. Higher = more concentrated."""
    total = np.sum(counts)
    if total == 0:
        return np.nan
    shares = np.asarray(counts, dtype=float) / total
    return float(np.sum(shares ** 2))


def balance_by_season(df):
    """One row per season: how unequal were wins, and how unequal was payroll?"""
    rows = []
    for year, season in df.groupby("Year"):
        games = season["G"].mean()
        sd_winpct = season["WinPct"].std(ddof=1)
        # Spread a league of identical teams would still show from luck alone
        ideal_sd = 0.5 / np.sqrt(games)
        rows.append({
            "Year": year,
            "Teams": len(season),
            "SD_WinPct": sd_winpct,
            "Ideal_SD": ideal_sd,
            "NollScully": sd_winpct / ideal_sd,
            "SD_Wins": season["W"].std(ddof=1),
            "Gini_Wins": gini(season["W"]),
            "Gini_Payroll": gini(season["Cots_OD_Payroll"]),
            "Payroll_CV": (season["Cots_OD_Payroll"].std(ddof=1)
                           / season["Cots_OD_Payroll"].mean()),
        })
    return pd.DataFrame(rows)


def cap_floor_binding(df, cap_m=CAP_M, floor_m=FLOOR_M, scalings=CBT_SCALINGS):
    """For each season and each payroll basis: who binds, and by how much."""
    rows = []
    for year, season in df.groupby("Year"):
        for scaling in scalings:
            payroll = season["Cots_OD_Payroll"] / 1e6 * scaling
            over = payroll > cap_m
            under = payroll < floor_m
            rows.append({
                "Year": year,
                "Basis": "Opening Day" if scaling == 1.0 else f"OD x{scaling:.2f}",
                "Scaling": scaling,
                "Teams_Over_Cap": int(over.sum()),
                "Teams_Below_Floor": int(under.sum()),
                "Teams_Unaffected": int((~over & ~under).sum()),
                "Dollars_Cut_M": float((payroll[over] - cap_m).sum()),
                "Dollars_Added_M": float((floor_m - payroll[under]).sum()),
            })
    binding = pd.DataFrame(rows)
    binding["Net_Change_M"] = binding["Dollars_Added_M"] - binding["Dollars_Cut_M"]
    return binding


def load_playoffs(df):
    """Read playoff appearances, normalize names, and check they match the panel.

    Returns None if the file is absent, so the rest of the step still runs.
    """
    if not RAW_PLAYOFFS_FILE.exists():
        return None
    playoffs = pd.read_csv(RAW_PLAYOFFS_FILE)
    playoffs["Team"] = playoffs["Team"].map(team_names.normalize_team_name)

    unknown_results = set(playoffs["Result"]) - set(RESULT_ORDER)
    if unknown_results:
        raise ValueError(f"Unexpected Result values in playoffs.csv: {sorted(unknown_results)}")

    # Every playoff club must exist in that season's panel, or a join will
    # silently drop it and every rate below would be wrong.
    panel = set(zip(df["Year"], df["Team"]))
    missing = [(y, t) for y, t in zip(playoffs["Year"], playoffs["Team"])
               if (y, t) not in panel]
    if missing:
        raise ValueError(f"Playoff teams not found in the merged panel: {missing[:10]}")

    return playoffs


def playoff_concentration(playoffs, df, window=WINDOW):
    """Does the same set of clubs keep reaching October?"""
    seasons = sorted(playoffs["Year"].unique())
    appearances = playoffs.groupby("Team").size()

    rows = []
    for i, year in enumerate(seasons):
        in_window = seasons[max(0, i - window + 1):i + 1]
        clubs = playoffs[playoffs["Year"].isin(in_window)]["Team"]
        prior = set(playoffs[playoffs["Year"] == seasons[i - 1]]["Team"]) if i else set()
        this_year = set(playoffs[playoffs["Year"] == year]["Team"])
        rows.append({
            "Year": year,
            "Playoff_Teams": len(this_year),
            "Distinct_Last_%d" % window: clubs.nunique(),
            "Repeat_From_Prior_Year": len(this_year & prior) if i else np.nan,
            "Repeat_Rate": len(this_year & prior) / len(this_year) if i else np.nan,
        })

    summary = pd.DataFrame(rows)
    # Whole-sample figures, attached as attributes for the report
    summary.attrs["distinct_overall"] = playoffs["Team"].nunique()
    summary.attrs["teams_in_league"] = df["Team"].nunique()
    summary.attrs["hhi_appearances"] = hhi(appearances.values)
    summary.attrs["hhi_even"] = 1.0 / df["Team"].nunique()
    summary.attrs["never_qualified"] = sorted(set(df["Team"]) - set(playoffs["Team"]))
    summary.attrs["most_appearances"] = appearances.sort_values(ascending=False).head(5)
    return summary


def playoff_rate_by_payroll(playoffs, df, quartiles=4):
    """Does spending buy October? Payroll quartile is taken within each season,
    so inflation across the sample does not matter."""
    panel = df[["Year", "Team", "Cots_OD_Payroll"]].copy()
    panel["Payroll_Quartile"] = (
        panel.groupby("Year")["Cots_OD_Payroll"]
        .transform(lambda s: pd.qcut(s, quartiles, labels=range(1, quartiles + 1)))
    )

    made = playoffs[["Year", "Team", "Result"]]
    panel = panel.merge(made, on=["Year", "Team"], how="left")
    panel["Made_Playoffs"] = panel["Result"].notna()
    panel["Won_Title"] = panel["Result"].eq("Champion")
    panel["Reached_WS"] = panel["Result"].isin(["Champion", "WS"])

    out = (panel.groupby("Payroll_Quartile", observed=True)
                .agg(Team_Seasons=("Made_Playoffs", "size"),
                     Playoff_Rate=("Made_Playoffs", "mean"),
                     World_Series_Rate=("Reached_WS", "mean"),
                     Title_Rate=("Won_Title", "mean"),
                     Mean_Payroll_M=("Cots_OD_Payroll", lambda s: s.mean() / 1e6))
                .reset_index())
    return out


def report(balance, binding, concentration, by_payroll, latest_year, df):
    print(f"Competitive balance, {balance.Year.min()}-{balance.Year.max()} "
          f"({len(df)} team-seasons)")
    print(balance.round(3).to_string(index=False))

    print("\nPooled averages")
    print(f"   Noll-Scully        {balance.NollScully.mean():.2f}  "
          f"(1.00 = all teams identical)")
    print(f"   SD of wins         {balance.SD_Wins.mean():.1f}")
    print(f"   Gini, wins         {balance.Gini_Wins.mean():.3f}")
    print(f"   Gini, payroll      {balance.Gini_Payroll.mean():.3f}")

    print("\nTrend over the sample (correlation with season)")
    for column in ["NollScully", "SD_Wins", "Gini_Wins", "Gini_Payroll", "Payroll_CV"]:
        print(f"   {column:14} r = {np.corrcoef(balance.Year, balance[column])[0, 1]:+.2f}")

    print(f"\nWho a ${CAP_M:.1f}M cap / ${FLOOR_M:.1f}M floor would bind in {latest_year}")
    latest = binding[binding.Year == latest_year]
    for _, row in latest.iterrows():
        print(f"   {row.Basis:14}  over cap: {row.Teams_Over_Cap:2d}   "
              f"below floor: {row.Teams_Below_Floor:2d}   "
              f"cut ${row.Dollars_Cut_M:6.1f}M   add ${row.Dollars_Added_M:6.1f}M   "
              f"net {row.Net_Change_M:+7.1f}M")

    if concentration is None:
        print(f"\nDynamic balance skipped: {RAW_PLAYOFFS_FILE} not found.")
        return

    print("\nDynamic balance (playoff appearances)")
    print(concentration.round(3).to_string(index=False))
    attrs = concentration.attrs
    print(f"\n   {attrs['distinct_overall']} of {attrs['teams_in_league']} clubs "
          f"reached the postseason at least once")
    if attrs["never_qualified"]:
        print(f"   Never qualified: {', '.join(attrs['never_qualified'])}")
    print(f"   HHI of appearances  {attrs['hhi_appearances']:.4f}  "
          f"(perfectly even would be {attrs['hhi_even']:.4f})")
    print(f"   Mean repeat rate    {concentration.Repeat_Rate.mean():.2f}  "
          f"(share of playoff clubs that also made it the year before)")
    print("   Most appearances:")
    for team, n in attrs["most_appearances"].items():
        print(f"      {team:24} {n}")

    print("\nPostseason rate by payroll quartile (1 = lowest spending)")
    print(by_payroll.round(3).to_string(index=False))


def main():
    df = pd.read_csv(config.MERGED_FILE)
    df["G"] = df["W"] + df["L"]
    df["WinPct"] = df["W"] / df["G"]

    balance = balance_by_season(df)
    binding = cap_floor_binding(df)

    playoffs = load_playoffs(df)
    concentration = playoff_concentration(playoffs, df) if playoffs is not None else None
    by_payroll = playoff_rate_by_payroll(playoffs, df) if playoffs is not None else None

    report(balance, binding, concentration, by_payroll, df.Year.max(), df)

    balance.to_csv(BALANCE_BY_SEASON_FILE, index=False)
    binding.to_csv(CAP_FLOOR_BINDING_FILE, index=False)
    saved = [BALANCE_BY_SEASON_FILE.name, CAP_FLOOR_BINDING_FILE.name]
    if concentration is not None:
        concentration.to_csv(PLAYOFF_CONCENTRATION_FILE, index=False)
        by_payroll.to_csv(PLAYOFF_BY_PAYROLL_FILE, index=False)
        saved += [PLAYOFF_CONCENTRATION_FILE.name, PLAYOFF_BY_PAYROLL_FILE.name]
    print("\nSaved: " + ", ".join(saved))


if __name__ == "__main__":
    main()
