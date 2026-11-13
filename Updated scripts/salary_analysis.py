"""
Step 4: the salary -> WAR -> wins chain.

Answers three questions with team-season data (2015 onward, no 2020):
  1. Salary -> WAR:  how much WAR does an extra $1M of payroll buy?
  2. Salary -> wins: does payroll still matter once WAR is known?
     (If not, money wins games only by buying WAR, so a simulation can go
      dollars -> WAR -> wins.)
  3. Where the money goes: WAR per $1M for hitters vs pitchers, and by position group.

Dollars are put in latest-season terms (e.g. 2026 dollars) by scaling each
season's payroll by the growth in league-average Opening Day payroll, so
seasons can be pooled.
Standard errors are heteroskedasticity-robust (HC1).

Outputs:
  salary_war_wins_results.txt   full regression summaries
  salary_war_wins_summary.csv   key coefficients in one table
  payroll_to_wins_table.csv     predicted WAR and wins at payroll levels
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import config

HITTER_WAR = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]
PITCHER_WAR = ["SP", "RP"]

# Position groups: WAR columns and the matching payroll columns.
# Infield is grouped because Cot's position labels and WAR's playing-time split
# rarely line up for individual infield spots.
POSITION_GROUPS = {
    "Catcher":    (["C"], ["Pay_C"]),
    "Infield":    (["1B", "2B", "3B", "SS"], ["Pay_1B", "Pay_2B", "Pay_3B", "Pay_SS", "Pay_UTIL"]),
    "Outfield":   (["LF", "CF", "RF"], ["Pay_OF_All"]),
    "DH":         (["DH"], ["Pay_DH"]),
    "Starters":   (["SP"], ["Pay_SP"]),
    "Relievers":  (["RP"], ["Pay_RP"]),
}

PAYROLL_LEVELS = [60, 100, 150, 200, 250, 300, 350]   # $M, latest-season dollars


def prepare(df):
    """Add payroll columns in latest-season dollars ($M) and WAR/payroll groups."""
    df = df.rename(columns={"C": "C_WAR"}).copy()   # 'C' clashes with formula syntax

    league_avg = df.groupby("Year")["Cots_OD_Payroll"].transform("mean")
    to_latest = df.loc[df["Year"] == df["Year"].max(), "Cots_OD_Payroll"].mean() / league_avg

    df["Payroll"] = df["Cots_OD_Payroll"] * to_latest / 1e6
    df["Hit_Pay"] = df["Pay_Hitters"] * to_latest / 1e6
    df["Pit_Pay"] = df["Pay_Pitchers"] * to_latest / 1e6
    df["SP_Pay"] = df["Pay_SP"] * to_latest / 1e6
    df["RP_Pay"] = df["Pay_RP"] * to_latest / 1e6

    war = {c: ("C_WAR" if c == "C" else c) for c in HITTER_WAR + PITCHER_WAR}
    df["Hit_WAR"] = df[[war[c] for c in HITTER_WAR]].sum(axis=1)
    df["Pit_WAR"] = df[[war[c] for c in PITCHER_WAR]].sum(axis=1)

    for name, (war_cols, pay_cols) in POSITION_GROUPS.items():
        df[f"{name}_WAR"] = df[[war[c] for c in war_cols]].sum(axis=1)
        df[f"{name}_Pay"] = df[pay_cols].sum(axis=1) * to_latest / 1e6
    return df


def fit(formula, df):
    return smf.ols(formula, df).fit(cov_type="HC1")


def row(model_name, result, term, per="WAR"):
    """One line of the summary table for a payroll coefficient."""
    b = result.params[term]
    lo, hi = result.conf_int().loc[term]
    return {
        "Model": model_name,
        "Term": term,
        f"Per $1M": round(b, 4),
        "CI_low": round(lo, 4),
        "CI_high": round(hi, 4),
        "p_value": round(result.pvalues[term], 4),
        # Cost per unit only when the estimate is clearly above zero
        f"$M per 1 {per}": round(1 / b, 1) if lo > 0 else np.nan,
        "R2": round(result.rsquared, 3),
        "N": int(result.nobs),
    }


def main():
    df = prepare(pd.read_csv(config.MERGED_FILE))
    base = int(df["Year"].max())   # dollars are expressed in this season's terms
    if df["Cots_OD_Payroll"].isna().any():
        missing = df.loc[df["Cots_OD_Payroll"].isna(), ["Year", "Team"]]
        raise ValueError(f"Team-seasons without payroll (run clean_payroll first):\n{missing}")

    models, summary = {}, []

    # ---- 1. Salary -> WAR ----
    models["1a WAR ~ payroll"] = m1 = fit("TotalWAR ~ Payroll", df)
    models["1b WAR ~ payroll + team fixed effects"] = fit("TotalWAR ~ Payroll + C(Team)", df)
    models["1c WAR ~ payroll + payroll^2 (diminishing returns?)"] = fit(
        "TotalWAR ~ Payroll + I(Payroll**2)", df)
    summary.append(row("WAR ~ payroll", m1, "Payroll"))
    summary.append(row("WAR ~ payroll + team FE", models["1b WAR ~ payroll + team fixed effects"], "Payroll"))

    # ---- 2. Salary -> wins, with and without WAR ----
    models["2a Wins ~ payroll"] = m2a = fit("W ~ Payroll", df)
    models["2b Wins ~ payroll + WAR"] = m2b = fit("W ~ Payroll + TotalWAR", df)
    models["2c Wins ~ WAR"] = m2c = fit("W ~ TotalWAR", df)
    summary.append(row("Wins ~ payroll", m2a, "Payroll", per="win"))
    summary.append(row("Wins ~ payroll + WAR", m2b, "Payroll", per="win"))

    # ---- 3. Where the money goes ----
    models["3a WAR ~ hitter pay + pitcher pay"] = m3a = fit("TotalWAR ~ Hit_Pay + Pit_Pay", df)
    models["3b WAR ~ hitter pay + SP pay + RP pay"] = m3b = fit("TotalWAR ~ Hit_Pay + SP_Pay + RP_Pay", df)
    for term in ["Hit_Pay", "Pit_Pay"]:
        summary.append(row("WAR ~ hitter + pitcher pay", m3a, term))
    for term in ["Hit_Pay", "SP_Pay", "RP_Pay"]:
        summary.append(row("WAR ~ hitter + SP + RP pay", m3b, term))
    equal_test = m3a.t_test("Hit_Pay - Pit_Pay = 0")

    for name in POSITION_GROUPS:
        r = fit(f"{name}_WAR ~ {name}_Pay", df)
        models[f"3c {name} WAR ~ {name} pay"] = r
        summary.append(row(f"{name} WAR ~ {name} pay", r, f"{name}_Pay"))

    summary = pd.DataFrame(summary)

    # ---- Payroll -> WAR -> wins table (for the simulation) ----
    a, b = m1.params["Intercept"], m1.params["Payroll"]
    c, d = m2c.params["Intercept"], m2c.params["TotalWAR"]
    pay_col = f"Payroll_{base}_$M"
    table = pd.DataFrame({pay_col: PAYROLL_LEVELS})
    table["Expected_WAR"] = (a + b * table[pay_col]).round(1)
    table["Expected_Wins"] = (c + d * table["Expected_WAR"]).round(1)

    # ---- Save ----
    with open(config.SALARY_RESULTS_FILE, "w") as f:
        f.write("SALARY -> WAR -> WINS\n")
        f.write(f"Payroll in $M, {base} dollars (scaled by league-average payroll growth).\n")
        f.write("Robust (HC1) standard errors. Team fixed-effect dummies omitted from printouts.\n\n")
        for name, r in models.items():
            f.write(f"{'=' * 78}\n{name}\n")
            text = r.summary().as_text()
            if "C(Team)" in r.model.formula:   # keep it readable
                keep = [l for l in text.splitlines() if "C(Team)" not in l]
                text = "\n".join(keep)
            f.write(text + "\n\n")
        f.write(f"{'=' * 78}\nTest: hitter pay and pitcher pay buy the same WAR per $1M\n")
        f.write(str(equal_test) + "\n")
    summary.to_csv(config.SALARY_SUMMARY_FILE, index=False)
    table.to_csv(config.PAYROLL_TO_WINS_FILE, index=False)

    # ---- Console summary ----
    med = m2b.params["Payroll"]
    print(f"Salary -> WAR:   {b:.4f} WAR per $1M  (≈ ${1 / b:.1f}M per WAR, {base} $)")
    print(f"WAR -> wins:     {d:.3f} wins per WAR")
    print(f"Salary -> wins:  {m2a.params['Payroll']:.4f} wins per $1M  "
          f"(≈ ${1 / m2a.params['Payroll']:.1f}M per win)")
    print(f"  ...with WAR in the model, payroll's effect is {med:.4f} (p = {m2b.pvalues['Payroll']:.2f}) "
          f"-> payroll works through WAR")
    print(f"Hitters ${1 / m3a.params['Hit_Pay']:.1f}M per WAR vs pitchers "
          f"${1 / m3a.params['Pit_Pay']:.1f}M per WAR (difference p = {float(equal_test.pvalue):.2f})")
    print(table.to_string(index=False))
    print(f"Saved: {config.SALARY_RESULTS_FILE.name}, {config.SALARY_SUMMARY_FILE.name}, "
          f"{config.PAYROLL_TO_WINS_FILE.name}")


if __name__ == "__main__":
    main()
