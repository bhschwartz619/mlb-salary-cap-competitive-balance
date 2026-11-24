"""
Salary cap and floor thresholds, and how they are applied to past seasons.

MLB's proposals are dollar amounts for the season they would take effect
(2027 or 2028). Applying those dollars directly to 2019-2026 payrolls would
compare future dollars with past ones: league-average CBT payroll grew about
4.5% a year over the sample, so a fixed $171.2M floor sits far below a typical
2019 payroll's footing and puts 19 clubs under it, against 12 in 2026. That is
an artifact of payroll growth, not a feature of the rule.

So each proposal is restated as a multiple of league-average CBT payroll in the
season it takes effect (projected forward from 2026 at the sample's average
growth rate), and that multiple is applied to each historical season's own
league average. Both proposals come out at about 1.14-1.15x average for the cap
and 0.80x for the floor.

The fixed-dollar version is kept as a robustness check (THRESHOLD_BASES), so the
paper can show what changes when the rule is scaled.
"""
import pandas as pd

# MLB's salary cap / floor proposals, $M in the season they take effect.
#   2027: May 2026 proposal (reported by MLB.com, July 31, 2026)
#   2028: revised proposal of Nov. 3, 2026, which delays the cap a year
PROPOSALS = {
    "MLB 2027 proposal": {"cap_m": 245.3, "floor_m": 171.2, "start": 2027},
    "MLB 2028 proposal": {"cap_m": 258.2, "floor_m": 180.2, "start": 2028},
}
DEFAULT_PROPOSAL = "MLB 2027 proposal"

SCALED = "Scaled to season"
FIXED = "Fixed dollars"
THRESHOLD_BASES = (SCALED, FIXED)


def league_average(cbt):
    """League-average CBT payroll by season, $M."""
    return cbt.groupby("Year")["CBT_Payroll"].mean() / 1e6


def payroll_growth(avg):
    """Average annual growth of league-average payroll across the sample,
    measured over calendar years (2020 counts as a year even though it has no
    sheet)."""
    first, last = avg.index.min(), avg.index.max()
    return (avg[last] / avg[first]) ** (1 / (last - first)) - 1


def proposal_ratios(proposal, avg, growth=None):
    """Cap and floor as multiples of league-average payroll in the season the
    proposal takes effect, projected forward from the last observed season."""
    p = PROPOSALS[proposal]
    growth = payroll_growth(avg) if growth is None else growth
    last = avg.index.max()
    projected_avg = avg[last] * (1 + growth) ** (p["start"] - last)
    return {"cap_ratio": p["cap_m"] / projected_avg,
            "floor_ratio": p["floor_m"] / projected_avg,
            "projected_avg_m": projected_avg,
            "growth": growth}


def season_thresholds(cbt, proposal=DEFAULT_PROPOSAL, basis=SCALED):
    """Cap and floor ($M) to apply in each season of the CBT panel."""
    avg = league_average(cbt)
    p = PROPOSALS[proposal]
    if basis == SCALED:
        r = proposal_ratios(proposal, avg)
        cap, floor = r["cap_ratio"] * avg, r["floor_ratio"] * avg
    elif basis == FIXED:
        cap = pd.Series(p["cap_m"], index=avg.index)
        floor = pd.Series(p["floor_m"], index=avg.index)
    else:
        raise ValueError(f"Unknown threshold basis: {basis}")
    return pd.DataFrame({"Year": avg.index, "Cap_M": cap.values,
                         "Floor_M": floor.values, "League_Avg_M": avg.values})
