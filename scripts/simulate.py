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

Thresholds (thresholds.py). MLB's proposals are dollar amounts for 2027 or 2028.
The main results restate each as a multiple of league-average CBT payroll
(about 1.14x for the cap, 0.80x for the floor) and apply that multiple to each
season's own average, so 2019 is judged against 2019 payrolls rather than 2027
dollars. Fixed-dollar thresholds are kept as a robustness check. Both proposals
(2027: $245.3M / $171.2M; 2028: $258.2M / $180.2M) are run.

Where floor money finds talent (FLOOR_SUPPLY). "Capped clubs only" is the
original rule above: floor clubs can buy only the WAR capped clubs release, and
any excess is inflation. "Open market" lets floor clubs also bid WAR away from
every club not bound by the floor, in proportion to the talent those clubs hold,
which is how free agency would actually redistribute it. Without that variant, a
floor-only rule moves no talent by construction.

Where leftover talent goes (LEFTOVER_RULE). When the cap frees more talent than
floor clubs absorb, the rest goes to the clubs between the floor and the cap
(or, with no floor, every club under the cap) in proportion to their room under
the cap, and no club takes on more than its room can pay for. Released players
sign where there is money to pay them. The original rule (in proportion to each
club's existing WAR) is kept as an option for robustness checks.
"""
import numpy as np
import pandas as pd

import balance_metrics
import config
import thresholds

# Dollars per WAR, in 2026 terms. The middle value is what the panel estimates;
# the outer two bound it, since the clearing price should move when the payroll
# distribution is compressed.
PRICES_M = (11.0, 14.4, 20.0)

# Which rules each scenario applies: (cap, floor)
SCENARIOS = {
    "Status quo": (False, False),
    "Cap only": (True, False),
    "Floor only": (False, True),
    "Cap + floor": (True, True),
}

CAPPED_ONLY = "Capped clubs only"
OPEN_MARKET = "Open market"
FLOOR_SUPPLY = (CAPPED_ONLY, OPEN_MARKET)

# Where talent the cap frees goes once floor clubs have taken what they need.
#   "Cap room": to the remaining clubs in proportion to their room under the
#       cap, and never more than that room can pay for (any excess passes to
#       the other clubs). Released players sign where there is money to pay them.
#   "Existing WAR": in proportion to the talent each club already has (the
#       original rule), kept for robustness checks. Not limited by cap room.
CAP_ROOM = "Cap room"
EXISTING_WAR = "Existing WAR"
LEFTOVER_RULE = CAP_ROOM

# Headline specification for the printed summary
MAIN = {"Proposal": thresholds.DEFAULT_PROPOSAL, "Thresholds": thresholds.SCALED,
        "Floor_Supply": CAPPED_ONLY, "Price_M_per_WAR": 14.4}

SEASONS_SIMULATED = 2000
GAMES = 162
RNG_SEED = 20261116


# Division alignment, stable across 2015-2026. Needed because playoff berths go
# to division winners plus wild cards, not simply to the best records overall.
DIVISIONS = {
    "AL East": ["Baltimore Orioles", "Boston Red Sox", "New York Yankees",
                "Tampa Bay Rays", "Toronto Blue Jays"],
    "AL Central": ["Chicago White Sox", "Cleveland Guardians", "Detroit Tigers",
                   "Kansas City Royals", "Minnesota Twins"],
    "AL West": ["Houston Astros", "Los Angeles Angels", "Oakland Athletics",
                "Seattle Mariners", "Texas Rangers"],
    "NL East": ["Atlanta Braves", "Miami Marlins", "New York Mets",
                "Philadelphia Phillies", "Washington Nationals"],
    "NL Central": ["Chicago Cubs", "Cincinnati Reds", "Milwaukee Brewers",
                   "Pittsburgh Pirates", "St. Louis Cardinals"],
    "NL West": ["Arizona Diamondbacks", "Colorado Rockies", "Los Angeles Dodgers",
                "San Diego Padres", "San Francisco Giants"],
}
TEAM_DIVISION = {t: d for d, teams in DIVISIONS.items() for t in teams}

# Wild cards per league: two through 2021, three from 2022.
WILDCARDS_BY_SEASON = {2019: 2, 2021: 2, 2022: 3, 2023: 3, 2024: 3, 2025: 3, 2026: 3}

SIMULATION_FILE = config.RESULTS_DIR / "simulation_results.csv"
# Each club's WAR before and after the rules, at the main price (for the
# talent-movement figure)
TEAM_WAR_FILE = config.RESULTS_DIR / "simulation_team_war.csv"
CLEARING_FILE = config.RESULTS_DIR / "simulation_clearing.csv"


def win_model(df):
    """Fit wins on total WAR, so the simulation uses the paper's own estimate
    rather than a constant borrowed from elsewhere."""
    x = df["TotalWAR"].values
    y = df["W"].values
    slope, intercept = np.polyfit(x, y, 1)
    return float(intercept), float(slope)


def allocate_within_limits(amount, weights, limits):
    """Split `amount` in proportion to `weights`, without giving any club more
    than its limit. A club that hits its limit keeps exactly that much, and the
    rest is re-split among the others, until it is all placed or every club is
    full (anything left then is spread by weight, and the cap is exceeded)."""
    weights = np.asarray(weights, dtype=float)
    limits = np.asarray(limits, dtype=float)
    alloc = np.zeros_like(weights)
    open_ = weights > 0
    remaining = float(amount)
    while remaining > 1e-9 and open_.any():
        w = np.where(open_, weights, 0.0)
        proposal = remaining * w / w.sum()
        full = open_ & (alloc + proposal >= limits - 1e-12)
        if not full.any():
            return alloc + proposal
        remaining -= float((limits[full] - alloc[full]).sum())
        alloc[full] = limits[full]
        open_ &= ~full
    if remaining > 1e-9 and weights.sum() > 0:
        alloc += remaining * weights / weights.sum()
    return alloc


def redistribute(season, cap_m, floor_m, price_m, floor_supply=CAPPED_ONLY,
                 leftover_rule=None):
    """Move WAR between clubs to satisfy the thresholds.

    cap_m / floor_m are None when the rule is off. floor_supply sets where floor
    clubs may find talent (see FLOOR_SUPPLY in the module docstring).

    Returns the season frame with a Sim_WAR column, plus a dict describing
    whether the talent market actually cleared.
    """
    leftover_rule = LEFTOVER_RULE if leftover_rule is None else leftover_rule
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

    # Open market: demand the capped clubs cannot meet is bid away from every
    # club not bound by the floor, in proportion to the talent each still holds.
    war_drawn = np.zeros(len(season))
    bought_elsewhere = 0.0
    unmet = max(0.0, war_demanded - supply)
    if floor_supply == OPEN_MARKET and unmet > 1e-9:
        pool = np.where(~under, np.maximum(war - war_lost, 0.0), 0.0)
        if pool.sum() > 0:
            bought_elsewhere = min(unmet, pool.sum())
            war_drawn = bought_elsewhere * pool / pool.sum()
            war_gained = war_gained + (dollars_added / price_m) * (bought_elsewhere / war_demanded)

    # Talent the cap frees beyond what floor clubs absorb goes to the clubs that
    # are neither capped nor floored (see LEFTOVER_RULE).
    leftover = supply - war_gained.sum()
    neutral = ~over & ~under
    if leftover > 1e-9 and neutral.any():
        if leftover_rule == CAP_ROOM and cap_m:
            room_m = np.where(neutral, np.maximum(cap_m - payroll_m, 0.0), 0.0)
            war_gained = war_gained + allocate_within_limits(leftover, room_m, room_m / price_m)
        elif war[neutral].sum() > 0:
            share = np.where(neutral, np.maximum(war, 0.0), 0.0)
            war_gained = war_gained + leftover * share / share.sum()

    sim_war = war - war_lost - war_drawn + war_gained
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
        "WAR_Bought_From_Other_Clubs": float(bought_elsewhere),
        "WAR_Actually_Moved": (float(min(supply + bought_elsewhere, war_demanded))
                               if war_demanded else float(supply)),
        "Unmet_Demand_WAR": float(max(0.0, war_demanded - supply - bought_elsewhere)),
        "Inflation_Only_M": float(max(0.0, war_demanded - supply - bought_elsewhere) * price_m),
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



def playoff_berths(draws, divisions, leagues, n_wildcards, rng):
    """Which clubs qualify in each simulated season.

    Division winners first, then the best remaining records in each league fill
    the wild cards — the actual rule, rather than simply taking the best records
    in the league, which would overstate access for clubs in weak divisions.
    """
    n_draws, n_teams = draws.shape
    # A tiny jitter breaks ties the way a tiebreaker game would, without
    # favouring whichever club happens to sit first in the frame.
    jittered = draws + rng.random((n_draws, n_teams)) * 0.5
    qualified = np.zeros((n_draws, n_teams), dtype=bool)

    for division in np.unique(divisions):
        cols = np.flatnonzero(divisions == division)
        winner = cols[np.argmax(jittered[:, cols], axis=1)]
        qualified[np.arange(n_draws), winner] = True

    for league in np.unique(leagues):
        cols = np.flatnonzero(leagues == league)
        scores = np.where(qualified[:, cols], -np.inf, jittered[:, cols])
        # argsort descending, take the top n_wildcards still unqualified
        order = np.argsort(-scores, axis=1)[:, :n_wildcards]
        for slot in range(n_wildcards):
            picked = cols[order[:, slot]]
            qualified[np.arange(n_draws), picked] = True

    return qualified


def playoff_access(qualified, quartiles):
    """Share of simulated seasons in which a club of each payroll quartile
    qualifies. Quartiles are the club's STATUS QUO payroll rank, so the question
    is whether a rule helps the clubs that were previously disadvantaged."""
    out = {}
    for q in (1, 2, 3, 4):
        cols = np.flatnonzero(quartiles == q)
        out[q] = float(qualified[:, cols].mean()) if len(cols) else np.nan
    return out


def summary(results, spec, value):
    """Pivot one measure for one specification: scenarios down, prices across."""
    keep = np.ones(len(results), dtype=bool)
    for k, v in spec.items():
        keep &= results[k].values == v
    return (results[keep].pivot_table(index="Scenario", columns="Price_M_per_WAR",
                                      values=value, aggfunc="mean")
            .reindex(SCENARIOS.keys()))


def main():
    merged = pd.read_csv(config.MERGED_FILE)
    cbt = balance_metrics.load_cbt()
    if cbt is None:
        print("No CBT payroll found — run clean_cbt.py first.")
        return

    df = merged.merge(cbt, on=["Year", "Team"], how="inner")
    # Status quo payroll quartile, within season, fixed across scenarios.
    df["Payroll_Quartile"] = (df.groupby("Year")["CBT_Payroll"]
                              .transform(lambda s: pd.qcut(s, 4, labels=[1, 2, 3, 4]))
                              .astype(int))
    intercept, slope = win_model(merged)
    rng = np.random.default_rng(RNG_SEED)

    print(f"Simulating {df.Year.nunique()} seasons ({df.Year.min()}-{df.Year.max()}), "
          f"{SEASONS_SIMULATED} draws each")
    print(f"Win model from the panel: wins = {intercept:.1f} + {slope:.3f} x WAR")
    print(f"Prices tested: {', '.join(f'${p:.1f}M/WAR' for p in PRICES_M)}")
    avg = thresholds.league_average(cbt)
    for name in thresholds.PROPOSALS:
        r = thresholds.proposal_ratios(name, avg)
        print(f"{name}: cap = {r['cap_ratio']:.2f}x and floor = {r['floor_ratio']:.2f}x "
              f"league-average CBT payroll (projected ${r['projected_avg_m']:.1f}M, "
              f"{r['growth'] * 100:.1f}%/yr growth)")

    # Season thresholds for every proposal and threshold basis
    limits = {(p, b): thresholds.season_thresholds(cbt, p, b).set_index("Year")
              for p in thresholds.PROPOSALS for b in thresholds.THRESHOLD_BASES}

    # Every combination. Rules a scenario does not use cannot change it, so the
    # status quo is simulated once per price and season and the cap-only
    # scenario once per threshold set; their rows are labelled for every
    # specification so each specification has a complete set of scenarios.
    results, clearings, team_rows = [], [], []
    for price in PRICES_M:
        for year, season in df.groupby("Year"):
            divisions = season["Team"].map(TEAM_DIVISION).values
            leagues = np.array([d[:2] for d in divisions])
            n_wc = WILDCARDS_BY_SEASON.get(int(year), 3)
            cache = {}
            for (proposal, basis), lim in limits.items():
                cap_y, floor_y = lim.loc[year, "Cap_M"], lim.loc[year, "Floor_M"]
                for supply in FLOOR_SUPPLY:
                    for name, (use_cap, use_floor) in SCENARIOS.items():
                        key = (name,
                               cap_y if use_cap else None,
                               floor_y if use_floor else None,
                               supply if use_floor else None)
                        if key not in cache:
                            sim, clearing = redistribute(
                                season, key[1], key[2], price,
                                supply if use_floor else CAPPED_ONLY)
                            draws = simulate_wins(sim["Sim_WAR"].values, intercept, slope, rng)
                            qualified = playoff_berths(draws, divisions, leagues, n_wc, rng)
                            access = playoff_access(qualified, season["Payroll_Quartile"].values)
                            row = balance_of(draws)
                            row.update({f"Playoff_Rate_Q{q}": v for q, v in access.items()})
                            row["Playoff_Gap_Q4_Q1"] = access[4] - access[1]
                            cache[key] = (row, clearing, sim["Sim_WAR"].values)
                        row, clearing, sim_war = cache[key]
                        labels = {"Proposal": proposal, "Thresholds": basis,
                                  "Floor_Supply": supply, "Price_M_per_WAR": price,
                                  "Scenario": name, "Year": year,
                                  "Cap_M": cap_y if use_cap else np.nan,
                                  "Floor_M": floor_y if use_floor else np.nan}
                        results.append({**labels, **row})
                        clearings.append({**labels, **clearing})
                        if price == MAIN["Price_M_per_WAR"]:
                            team_rows.append(pd.DataFrame({
                                **{k: labels[k] for k in ("Proposal", "Thresholds", "Floor_Supply",
                                                          "Scenario", "Year", "Cap_M", "Floor_M")},
                                "Team": season["Team"].values,
                                "CBT_Payroll_M": season["CBT_Payroll"].values / 1e6,
                                "Payroll_Quartile": season["Payroll_Quartile"].values,
                                "WAR": season["TotalWAR"].values,
                                "Sim_WAR": sim_war,
                                "WAR_Change": sim_war - season["TotalWAR"].values,
                                "Expected_Wins": intercept + slope * season["TotalWAR"].values,
                                "Sim_Expected_Wins": intercept + slope * sim_war,
                            }))

    results = pd.DataFrame(results)
    clearings = pd.DataFrame(clearings)

    spec = {k: v for k, v in MAIN.items() if k != "Price_M_per_WAR"}
    title = f"{MAIN['Proposal']}, {MAIN['Thresholds'].lower()}, floor supply: {MAIN['Floor_Supply'].lower()}"

    print(f"\nMAIN SPECIFICATION: {title}")
    print("\nMean Noll-Scully by scenario and price (lower = more balanced)")
    print(summary(results, spec, "NollScully").round(3).to_string())
    print("\nMean SD of wins by scenario and price")
    print(summary(results, spec, "SD_Wins").round(2).to_string())

    mid_spec = {**spec, "Price_M_per_WAR": MAIN["Price_M_per_WAR"]}
    keep = np.ones(len(results), dtype=bool)
    for k, v in mid_spec.items():
        keep &= results[k].values == v
    access_tbl = (results[keep].groupby("Scenario")[
        ["Playoff_Rate_Q1", "Playoff_Rate_Q2", "Playoff_Rate_Q3",
         "Playoff_Rate_Q4", "Playoff_Gap_Q4_Q1"]].mean().reindex(SCENARIOS.keys()))
    access_tbl.columns = ["Q1 (low)", "Q2", "Q3", "Q4 (high)", "Q4 - Q1"]
    print(f"\nPlayoff rate by status-quo payroll quartile (at ${MAIN['Price_M_per_WAR']:.1f}M/WAR)")
    print(access_tbl.round(3).to_string())

    print(f"\nDid the talent market clear? (at ${MAIN['Price_M_per_WAR']:.1f}M/WAR)")
    keep_c = np.ones(len(clearings), dtype=bool)
    for k, v in mid_spec.items():
        keep_c &= clearings[k].values == v
    mid = clearings[keep_c]
    for name in list(SCENARIOS)[1:]:
        print(f"   --- {name} ---")
        for _, r in mid[mid.Scenario == name].iterrows():
            flag = "" if r.Unmet_Demand_WAR < 0.5 else \
                   f"   UNMET {r.Unmet_Demand_WAR:5.1f} WAR = ${r.Inflation_Only_M:6.0f}M inflation"
            print(f"   {int(r.Year)}   over cap {int(r.Clubs_Over_Cap):2d}  below floor "
                  f"{int(r.Clubs_Below_Floor):2d}   released {r.WAR_Released:5.1f}   "
                  f"demanded {r.WAR_Demanded:5.1f}{flag}")

    print(f"\nROBUSTNESS: Q4 - Q1 playoff gap and Noll-Scully at ${MAIN['Price_M_per_WAR']:.1f}M/WAR")
    at_mid = results[results.Price_M_per_WAR == MAIN["Price_M_per_WAR"]]
    robust = (at_mid.groupby(["Proposal", "Thresholds", "Floor_Supply", "Scenario"], sort=False)
              [["NollScully", "Playoff_Gap_Q4_Q1"]].mean().unstack("Scenario"))
    robust = robust.reindex(columns=list(SCENARIOS), level=1)
    print(robust.round(3).to_string())

    results.to_csv(SIMULATION_FILE, index=False)
    clearings.to_csv(CLEARING_FILE, index=False)
    pd.concat(team_rows, ignore_index=True).to_csv(TEAM_WAR_FILE, index=False)
    print(f"\nSaved: {SIMULATION_FILE.name}, {CLEARING_FILE.name}, {TEAM_WAR_FILE.name}")


if __name__ == "__main__":
    main()
