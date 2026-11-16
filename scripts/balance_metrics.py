"""
Step 6: competitive balance metrics, and who a cap/floor would actually bind.

Two jobs, both from merged_war_standings.csv:

1. The historical baseline. Every simulated scenario gets compared against
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

Not computed here: playoff concentration and how often a bottom-payroll team
reaches the postseason. Those need playoff appearance data, which the repo
does not have yet.
"""
import numpy as np
import pandas as pd

import config

# MLB's reported 2027 proposal, $M. Change these to test other thresholds.
CAP_M = 245.3
FLOOR_M = 171.2

# CBT payroll runs above Opening Day payroll. Until it is parsed, the binding
# counts are reported on the OD basis and at these two scalings of it.
CBT_SCALINGS = (1.00, 1.12, 1.20)

BALANCE_BY_SEASON_FILE = config.RESULTS_DIR / "balance_by_season.csv"
CAP_FLOOR_BINDING_FILE = config.RESULTS_DIR / "cap_floor_binding.csv"


def gini(values):
    """Gini coefficient. 0 = everyone equal, 1 = one team has everything."""
    x = np.sort(np.asarray(values, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return np.nan
    return 2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum()) - (n + 1) / n


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


def report(balance, binding, latest_year, df):
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


def main():
    df = pd.read_csv(config.MERGED_FILE)
    df["G"] = df["W"] + df["L"]
    df["WinPct"] = df["W"] / df["G"]

    balance = balance_by_season(df)
    binding = cap_floor_binding(df)

    report(balance, binding, df.Year.max(), df)

    balance.to_csv(BALANCE_BY_SEASON_FILE, index=False)
    binding.to_csv(CAP_FLOOR_BINDING_FILE, index=False)
    print(f"\nSaved: {BALANCE_BY_SEASON_FILE.name}, {CAP_FLOOR_BINDING_FILE.name}")


if __name__ == "__main__":
    main()
