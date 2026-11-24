"""
Step 9 (optional): which clubs would actually have made the playoffs under each rule.

The simulation (Step 7) gives each club's playoff ODDS under each rule: the
share of 2,000 simulated seasons in which it qualifies. This step adds the one
outcome that lines up with what really happened, by keeping each club's real
luck.

    luck           = actual wins - expected wins from actual WAR
    rule wins      = expected wins from the WAR the club would have had under
                     the rule + that same luck

Under the status quo, rule wins equal actual wins, so the real playoff field is
reproduced exactly (checked below). Under a rule, the standings are rebuilt
with each season's real format (division winners plus two wild cards per league
in 2019 and 2021, three from 2022) and compared with the real field. Because
league WAR is conserved, wins still add up across the league.

Ties in rule wins are broken in favour of the club that actually made the
playoffs (which is how the real tiebreaker went when wins are unchanged), then
by actual wins.

This is a single, illustrative outcome: it says what the rule would have done
to the seasons that really happened, holding everything else fixed. The odds
from Step 7 say how likely a change was. Both are reported.

Main specification only (see simulate.MAIN).

Outputs
    results/counterfactual_playoffs.csv     every club-season under every rule
    tables/table5_playoff_changes.csv       every playoff spot that changes
                                            hands under cap + floor
"""
import numpy as np
import pandas as pd

import config
import simulate
import team_names

TEAM_FILE = config.RESULTS_DIR / "counterfactual_playoffs.csv"
CHANGES_TABLE = config.TABLES_DIR / "table5_playoff_changes.csv"
TABLE_SCENARIO = "Cap + floor"


def load():
    teams = pd.read_csv(simulate.TEAM_WAR_FILE)
    spec = {k: v for k, v in simulate.MAIN.items() if k in teams.columns}
    for k, v in spec.items():
        teams = teams[teams[k] == v]

    merged = pd.read_csv(config.MERGED_FILE)[["Year", "Team", "W", "L"]]
    teams = teams.merge(merged, on=["Year", "Team"], how="left", validate="many_to_one")

    playoffs = pd.read_csv(config.RAW_DIR / "playoffs" / "playoffs.csv")
    playoffs["Team"] = playoffs["Team"].apply(team_names.normalize_team_name)
    made = set(zip(playoffs["Year"], playoffs["Team"]))
    teams["Made_Actual"] = [(y, t) in made for y, t in zip(teams["Year"], teams["Team"])]

    sq_odds = (teams[teams["Scenario"] == "Status quo"]
               .set_index(["Year", "Team"])["Playoff_Odds"].rename("Playoff_Odds_Status_Quo"))
    teams = teams.join(sq_odds, on=["Year", "Team"])
    return teams


def playoff_field(season, wins_col, n_wildcards):
    """Division winners, then the best remaining records in each league.
    Returns a boolean array aligned with `season`."""
    division = season["Team"].map(simulate.TEAM_DIVISION)
    league = division.str[:2]
    order = season.assign(_div=division, _lg=league).sort_values(
        [wins_col, "Made_Actual", "W"], ascending=False)

    made = pd.Series(False, index=season.index)
    made[order.groupby("_div").head(1).index] = True
    rest = order[~made[order.index]]
    made[rest.groupby("_lg").head(n_wildcards).index] = True
    return made.values


def build(teams):
    teams = teams.copy()
    teams["Luck"] = teams["W"] - teams["Expected_Wins"]
    teams["Rule_Wins"] = teams["Sim_Expected_Wins"] + teams["Luck"]
    teams["Win_Change"] = teams["Rule_Wins"] - teams["W"]
    teams["Made_Rule"] = False
    for (scenario, year), season in teams.groupby(["Scenario", "Year"]):
        n_wc = simulate.WILDCARDS_BY_SEASON.get(int(year), 3)
        teams.loc[season.index, "Made_Rule"] = playoff_field(season, "Rule_Wins", n_wc)
    teams["Change"] = np.select(
        [teams["Made_Rule"] & ~teams["Made_Actual"], ~teams["Made_Rule"] & teams["Made_Actual"]],
        ["In", "Out"], "")
    teams["League"] = teams["Team"].map(simulate.TEAM_DIVISION).str[:2]
    return teams


def check_status_quo(teams):
    sq = teams[teams["Scenario"] == "Status quo"]
    wrong = sq[sq["Made_Rule"] != sq["Made_Actual"]]
    if len(wrong):
        print("WARNING: the status quo does not reproduce the real playoff field:")
        print(wrong[["Year", "Team", "W", "Made_Actual", "Made_Rule"]].to_string(index=False))
    else:
        print(f"Check: the status quo reproduces all {int(sq['Made_Actual'].sum())} real "
              f"playoff berths, {sq['Year'].min()}-{sq['Year'].max()}")


def club_label(r):
    return (f"{r['Team']} (Q{int(r['Payroll_Quartile'])}; {int(r['W'])} -> "
            f"{r['Rule_Wins']:.1f} wins; odds {r['Playoff_Odds_Status_Quo'] * 100:.0f}% -> "
            f"{r['Playoff_Odds'] * 100:.0f}%)")


def changes_table(teams, scenario=TABLE_SCENARIO):
    """One row per playoff spot that changes hands: the club that gets in and
    the club it displaces, in the same league and season."""
    rows = []
    sc = teams[teams["Scenario"] == scenario]
    for (year, league), g in sc.groupby(["Year", "League"]):
        ins = g[g["Change"] == "In"].sort_values("Rule_Wins", ascending=False)
        outs = g[g["Change"] == "Out"].sort_values("Rule_Wins", ascending=False)
        for (_, i), (_, o) in zip(ins.iterrows(), outs.iterrows()):
            rows.append({
                "Season": int(year), "League": league,
                "Gets in": i["Team"], "Payroll quartile (in)": int(i["Payroll_Quartile"]),
                "Actual wins (in)": int(i["W"]), "Wins under rule (in)": round(i["Rule_Wins"], 1),
                "WAR change (in)": round(i["WAR_Change"], 1),
                "Playoff odds (in)": f"{i['Playoff_Odds_Status_Quo'] * 100:.0f}% -> {i['Playoff_Odds'] * 100:.0f}%",
                "Drops out": o["Team"], "Payroll quartile (out)": int(o["Payroll_Quartile"]),
                "Actual wins (out)": int(o["W"]), "Wins under rule (out)": round(o["Rule_Wins"], 1),
                "WAR change (out)": round(o["WAR_Change"], 1),
                "Playoff odds (out)": f"{o['Playoff_Odds_Status_Quo'] * 100:.0f}% -> {o['Playoff_Odds'] * 100:.0f}%",
            })
    return pd.DataFrame(rows)


def report(teams):
    print(f"\nPlayoff spots that change hands, {teams['Year'].min()}-{teams['Year'].max()} "
          f"(main specification, real luck held fixed)")
    berths = int(teams[teams["Scenario"] == "Status quo"]["Made_Actual"].sum())
    for scenario in list(simulate.SCENARIOS)[1:]:
        sc = teams[teams["Scenario"] == scenario]
        n = int((sc["Change"] == "In").sum())
        by_q = sc[sc["Made_Rule"]].groupby("Payroll_Quartile").size().reindex([1, 2, 3, 4], fill_value=0)
        act_q = sc[sc["Made_Actual"]].groupby("Payroll_Quartile").size().reindex([1, 2, 3, 4], fill_value=0)
        print(f"\n   {scenario}: {n} of {berths} berths change hands")
        print("      berths by payroll quartile (Q1 low):  actual "
              + " / ".join(str(v) for v in act_q.values)
              + "   under rule " + " / ".join(str(v) for v in by_q.values))
        for _, r in sc[sc["Change"] != ""].sort_values(["Year", "League", "Change"]).iterrows():
            print(f"      {int(r['Year'])} {r['League']}  {r['Change']:3s}  {club_label(r)}")


def main():
    teams = build(load())
    check_status_quo(teams)
    report(teams)

    cols = ["Proposal", "Thresholds", "Floor_Supply", "Scenario", "Year", "League", "Team",
            "CBT_Payroll_M", "Payroll_Quartile", "WAR", "Sim_WAR", "WAR_Change", "W",
            "Expected_Wins", "Luck", "Rule_Wins", "Win_Change", "Playoff_Odds_Status_Quo",
            "Playoff_Odds", "Made_Actual", "Made_Rule", "Change"]
    teams[cols].round(4).to_csv(TEAM_FILE, index=False)
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    table = changes_table(teams)
    table.to_csv(CHANGES_TABLE, index=False)
    print(f"\nSaved: {TEAM_FILE.name}, {CHANGES_TABLE.name} ({len(table)} spots, {TABLE_SCENARIO})")


if __name__ == "__main__":
    main()
