"""
Step 7: simulate seasons under alternative cap and floor rules.

The question is what competitive balance would look like if MLB's proposed
thresholds had been in force. The chain is:

    cap/floor  ->  payroll moves  ->  talent moves  ->  wins  ->  balance

Three things about how this is built are worth stating plainly, because each is
a modelling choice a reader should be able to disagree with.

1. League WAR is conserved. WAR is defined against replacement level, so the
   30 clubs sum to roughly the same total every season no matter what anyone
   spends. Money can move talent between clubs; it cannot create any. After
   redistribution the simulated WAR is rescaled to the season's observed total,
   which stops a floor from manufacturing wins out of nothing.

2. The market does not have to clear, and when it does not, the step says so.
   Capped clubs release WAR; floored clubs demand it. At a fixed price those two
   quantities need not match. In 2019, for instance, the proposed thresholds put
   no club over the cap and 19 below the floor: roughly $928M of mandated new
   spending against zero dollars freed. The talent those clubs would be buying
   does not exist. Rather than quietly inventing it, each scenario reports WAR
   released against WAR demanded, and when demand exceeds supply the excess is
   treated as salary inflation — clubs pay more for the same players — and buys
   no talent at all.

3. The price of a win is not treated as known. $14.4M per WAR is what the
   market cleared at under the observed payroll distribution; compress that
   distribution and the clearing price should move, and nothing here can say by
   how much. So every scenario is run across a range of prices and the question
   becomes whether the balance conclusions survive all of them, rather than
   whether they hold at one number.

Scenarios are run on CBT payroll, the basis a real cap or floor would be
assessed on, so coverage is 2019 onward.
"""
import numpy as np
import pandas as pd

import balance_metrics
import config

CAP_M = balance_metrics.CAP_M
FLOOR_M = balance_metrics.FLOOR_M

# Dollars per WAR, in 2026 terms. The middle value is what the panel estimates;
# the outer two bound it, since the clearing price should move when the payroll
# distribution is compressed.
PRICES_M = (11.0, 14.4, 20.0)

SCENARIOS = {
    "Status quo": (None, None),
    "Cap only": (CAP_M, None),
    "Floor only": (None, FLOOR_M),
    "Cap + floor": (CAP_M, FLOOR_M),
}

SEASONS_SIMULATED = 2000
GAMES = 162
RNG_SEED = 20261116

SIMULATION_FILE = config.RESULTS_DIR / "simulation_results.csv"
CLEARING_FILE = config.RESULTS_DIR / "simulation_clearing.csv"


def win_model(df):
    """Fit wins on total WAR, so the simulation uses the paper's own estimate
    rather than a constant borrowed from elsewhere."""
    x = df["TotalWAR"].values
    y = df["W"].values
    slope, intercept = np.polyfit(x, y, 1)
    return float(intercept), float(slope)


def redistribute(season, cap_m, floor_m, price_m):
    """Move WAR between clubs to satisfy the thresholds.

    Returns the season frame with a Sim_WAR column, plus a dict describing
    whether the talent market actually cleared.
    """
    payroll_m = season["CBT_Payroll"].values / 1e6
    war = season["TotalWAR"].values.astype(float)

    over = (payroll_m > cap_m) if cap_m else np.zeros(len(season), dtype=bool)
    under = (payroll_m < floor_m) if floor_m else np.zeros(len(season), dtype=bool)

    dollars_cut = np.where(over, payroll_m - (cap_m or 0.0), 0.0)
    dollars_added = np.where(under, (floor_m or 0.0) - payroll_m, 0.0)

    war_released = dollars_cut.sum() / price_m
    war_demanded = dollars_added.sum() / price_m

    # A club cannot shed more talent than it has above replacement.
    war_lost = np.minimum(dollars_cut / price_m, np.maximum(war, 0))
    supply = war_lost.sum()

    # Demand above supply buys nothing: those dollars raise salaries without
    # moving players, because the players being bid for do not exist.
    if war_demanded > 0:
        fill = min(1.0, supply / war_demanded) if war_demanded else 0.0
        war_gained = (dollars_added / price_m) * fill
    else:
        war_gained = np.zeros(len(season))

    # Supply above demand has nowhere to go under a cap-only rule; it lands on
    # the clubs that are neither capped nor floored, in proportion to the talent
    # they already have, which is the mildest assumption available.
    leftover = supply - war_gained.sum()
    neutral = ~over & ~under
    if leftover > 1e-9 and neutral.any() and war[neutral].sum() > 0:
        share = np.where(neutral, war, 0.0)
        war_gained = war_gained + leftover * share / share.sum()

    sim_war = war - war_lost + war_gained
    sim_war = np.maximum(sim_war, 0.0)

    # Conserve the season's league total.
    if sim_war.sum() > 0:
        sim_war *= war.sum() / sim_war.sum()

    out = season.copy()
    out["Sim_WAR"] = sim_war
    clearing = {
        "Clubs_Over_Cap": int(over.sum()),
        "Clubs_Below_Floor": int(under.sum()),
        "WAR_Released": war_released,
        "WAR_Demanded": war_demanded,
        "WAR_Actually_Moved": float(min(supply, war_demanded)) if war_demanded else float(supply),
        "Unmet_Demand_WAR": float(max(0.0, war_demanded - supply)),
        "Inflation_Only_M": float(max(0.0, war_demanded - supply) * price_m),
    }
    return out, clearing


def simulate_wins(sim_war, intercept, slope, rng, n=SEASONS_SIMULATED):
    """Monte Carlo a 162-game season around each club's implied true talent.

    Clubs are drawn independently, so simulated league wins do not sum exactly
    to 2,430. That is immaterial for dispersion measures and is noted as a
    limitation rather than patched.
    """
    expected = intercept + slope * sim_war
    p = np.clip(expected / GAMES, 0.02, 0.98)
    draws = rng.binomial(GAMES, p, size=(n, len(p)))
    return draws


def balance_of(draws):
    """Spread measures across simulated seasons."""
    win_pct = draws / GAMES
    sd = win_pct.std(axis=1, ddof=1)
    ideal = 0.5 / np.sqrt(GAMES)
    sd_wins = draws.std(axis=1, ddof=1)
    return {
        "SD_WinPct": float(sd.mean()),
        "NollScully": float((sd / ideal).mean()),
        "SD_Wins": float(sd_wins.mean()),
        "SD_Wins_p05": float(np.percentile(sd_wins, 5)),
        "SD_Wins_p95": float(np.percentile(sd_wins, 95)),
    }


def main():
    merged = pd.read_csv(config.MERGED_FILE)
    cbt = balance_metrics.load_cbt()
    if cbt is None:
        print("No CBT payroll found — run clean_cbt.py first.")
        return

    df = merged.merge(cbt, on=["Year", "Team"], how="inner")
    intercept, slope = win_model(merged)
    rng = np.random.default_rng(RNG_SEED)

    print(f"Simulating {df.Year.nunique()} seasons ({df.Year.min()}-{df.Year.max()}), "
          f"{SEASONS_SIMULATED} draws each")
    print(f"Win model from the panel: wins = {intercept:.1f} + {slope:.3f} x WAR")
    print(f"Prices tested: {', '.join(f'${p:.1f}M/WAR' for p in PRICES_M)}")

    results, clearings = [], []
    for price in PRICES_M:
        for name, (cap_m, floor_m) in SCENARIOS.items():
            for year, season in df.groupby("Year"):
                sim, clearing = redistribute(season, cap_m, floor_m, price)
                draws = simulate_wins(sim["Sim_WAR"].values, intercept, slope, rng)
                row = {"Price_M_per_WAR": price, "Scenario": name, "Year": year}
                row.update(balance_of(draws))
                results.append(row)
                clearings.append({"Price_M_per_WAR": price, "Scenario": name,
                                  "Year": year, **clearing})

    results = pd.DataFrame(results)
    clearings = pd.DataFrame(clearings)

    print("\nMean Noll-Scully by scenario and price (lower = more balanced)")
    pivot = (results.pivot_table(index="Scenario", columns="Price_M_per_WAR",
                                 values="NollScully", aggfunc="mean")
             .reindex(SCENARIOS.keys()))
    print(pivot.round(3).to_string())

    print("\nMean SD of wins by scenario and price")
    pivot_sd = (results.pivot_table(index="Scenario", columns="Price_M_per_WAR",
                                    values="SD_Wins", aggfunc="mean")
                .reindex(SCENARIOS.keys()))
    print(pivot_sd.round(2).to_string())

    print(f"\nDid the talent market clear? (at ${PRICES_M[1]:.1f}M/WAR)")
    mid = clearings[clearings["Price_M_per_WAR"] == PRICES_M[1]]
    for name in SCENARIOS:
        block = mid[mid.Scenario == name]
        if name == "Status quo":
            continue
        print(f"   --- {name} ---")
        for _, r in block.iterrows():
            flag = "" if r.Unmet_Demand_WAR < 0.5 else \
                   f"   UNMET {r.Unmet_Demand_WAR:5.1f} WAR = ${r.Inflation_Only_M:6.0f}M inflation"
            print(f"   {int(r.Year)}   released {r.WAR_Released:5.1f}   "
                  f"demanded {r.WAR_Demanded:5.1f}{flag}")

    results.to_csv(SIMULATION_FILE, index=False)
    clearings.to_csv(CLEARING_FILE, index=False)
    print(f"\nSaved: {SIMULATION_FILE.name}, {CLEARING_FILE.name}")


if __name__ == "__main__":
    main()
