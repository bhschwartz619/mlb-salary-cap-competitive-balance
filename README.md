# The Price of Parity: Salary Restrictions and Competitive Balance in Major League Baseball

## Abstract

Major League Baseball (MLB) currently utilizes a Competitive Balance Tax (CBT) to discourage excessive payrolls, a system facing particular scrutiny entering the 2026–2027 offseason and upcoming Collective Bargaining Agreement negotiations. Central to these discussions is whether the existing CBT sufficiently promotes competitive balance or whether MLB should follow other major American professional sports leagues by instituting a salary cap, salary floor, or both. This study examines how alternative salary restrictions could affect competitive balance across MLB. Using Opening Day payrolls from Cot’s Baseball Contracts and Wins Above Replacement (WAR) from Baseball-Reference for 330 team-seasons (2015–2026, excluding 2020), we estimate the relationships among team spending, player value, and team wins. Each additional WAR is associated with 0.98 wins, and each additional WAR costs about $14.4 million in 2026 dollars, with no evidence of diminishing returns. Payroll is associated with winning only through the WAR it buys: once WAR is controlled for, payroll has no remaining relationship with wins. However, payroll explains only 13% of the variation in team wins, which limits how much any payroll structure can change outcomes in a single season. These estimates provide the basis for simulating how various salary cap and floor thresholds could redistribute payroll and player talent across all 30 MLB clubs. Monte Carlo simulations of a 162-game season are then used to estimate how each structure affects season outcomes. Competitive balance is evaluated across multiple measures such as the spread of winning percentage and playoff qualification rates by payroll level. By comparing these measures across alternative payroll structures, this study provides data-driven evidence on the potential consequences of salary restrictions as MLB considers changes to its economic structure.

## Research Question

**How would the implementation of a salary cap and salary floor affect competitive balance in Major League Baseball?**

## Methodology

The project combines historical MLB data with statistical modeling and simulation:

- [x] Collect and clean team payroll, WAR, standings, and postseason data for 2015–2026 (330 team-seasons; the shortened 2020 season is excluded)
- [x] Estimate the relationship between WAR and team wins, overall and by position
- [x] Estimate the relationship between payroll and player talent (WAR), and between payroll and wins
- [x] Produce figures and tables for the paper
- [x] Measure actual competitive balance each season (Noll-Scully, Gini, playoff concentration, playoff rate by payroll quartile)
- [x] Simulate MLB's proposed salary cap and floor thresholds, redistributing payroll and player talent across all 30 clubs
- [x] Monte Carlo simulation of 162-game MLB seasons, including the real playoff format
- [x] Evaluate competitive balance under each structure using multiple measures
- [ ] Write up the balance and simulation results for the paper (due December 1, 2026)

### How the simulation works

The simulation asks what competitive balance would have looked like if MLB's proposed cap and floor had been in force from 2019 to 2026. It uses each season's real clubs, rosters, and CBT payrolls.

1. **Thresholds.** MLB's proposals are dollar amounts for the season they take effect: $245.3M cap / $171.2M floor for 2027, and $258.2M / $180.2M in the revised proposal of November 3, 2026, which delays the cap to 2028. Applying 2027 dollars to 2019 payrolls would put 19 clubs under the floor purely because payrolls have grown. So each proposal is restated as a multiple of projected league-average CBT payroll (about 1.14× for the cap and 0.80× for the floor) and applied to each season's own average. Fixed-dollar thresholds are kept as a robustness check.
2. **Payroll moves, then talent moves.** Clubs over the cap cut payroll down to it and release WAR at the price of a win ($14.4M per WAR, also run at $11M and $20M). Clubs under the floor spend up to it and buy WAR. Total league WAR is held fixed, because money can move talent between clubs but cannot create it.
3. **Where floor money finds talent.** In the main version, floor clubs can buy only the talent that capped clubs release, and any spending beyond that raises salaries without adding talent. An "open market" version also lets floor clubs bid talent away from every other club.
4. **Where leftover talent goes.** When the cap frees more talent than floor clubs absorb, the rest goes to the other clubs under the cap in proportion to their room under it, and no club takes on more than its room can pay for.
5. **Seasons and playoffs.** Each club's WAR is converted to expected wins with the WAR-to-wins regression, and each scenario is played out over 2,000 simulated 162-game seasons. Playoff berths follow the real format of each year (division winners plus two wild cards per league in 2019 and 2021, three from 2022).

Four scenarios are compared: status quo, cap only, floor only, and cap + floor.

## Key Findings to Date

### Salary analysis

Based on 330 team-seasons (2015–2026). Payroll is Opening Day payroll, scaled to 2026 dollars by league-average payroll growth.

- **WAR and wins:** each additional WAR is associated with 0.98 more wins (R² = 0.856), and a team with zero WAR projects to about 48 wins, close to the standard replacement-level baseline.
- **Position:** WAR is worth roughly the same number of wins at every position; splitting WAR by position does not improve on total WAR.
- **Payroll and WAR:** each additional WAR costs about $14.4M (95% CI $11.5M–$19.3M). The estimate holds with team and year fixed effects, with no evidence of diminishing returns.
- **Payroll works only through WAR:** once WAR is controlled for, payroll has no remaining relationship with wins (p = 0.97).
- **Limited reach of payroll:** payroll explains only about 13% of the variation in wins. Removing payroll differences entirely would lower the spread of team wins only from 12.7 to about 11.9 wins (luck alone produces about 6.4).
- **Hitters vs. pitchers:** pitcher spending bought WAR more cheaply than hitter spending (about $9.8M vs. $25.4M per WAR), but the difference is not statistically conclusive (p = 0.07).

### Actual competitive balance

- **Within-season balance:** the Noll-Scully ratio (spread of win percentage relative to what luck alone produces; 1.0 is perfect balance) averaged 2.01 over 2015–2026. It peaked at 2.49 in 2019 and has fallen every season since, to 1.73 in 2026.
- **Playoff access by payroll:** clubs in the top payroll quartile made the playoffs 55% of the time, against 26% for the bottom quartile.

### Simulated cap and floor (2019–2026)

Main specification: 2027 proposal, thresholds scaled to each season, floor clubs buying only the talent the cap releases, $14.4M per WAR.

| Scenario | Noll-Scully | Playoff rate, bottom payroll quartile | Playoff rate, top payroll quartile | Gap (top − bottom) |
|---|---|---|---|---|
| Status quo | 2.16 | 23% | 62% | 38.9 pts |
| Cap only | 2.04 | 30% | 50% | 20.2 pts |
| Floor only | 2.16 | 23% | 62% | 39.0 pts |
| Cap + floor | 2.04 | 30% | 50% | 20.1 pts |

- **The cap does the work.** A cap cuts the playoff gap between the highest- and lowest-payroll clubs roughly in half and lowers Noll-Scully by about 5%. Adding a floor changes almost nothing.
- **A floor alone moves no talent in the main version**, because it can only buy talent that a cap releases. In the open-market version, a floor alone narrows the gap to 27.8 points, less than a cap does.
- **Robust to the proposal and the price of a win:** with scaled thresholds, a cap brings the gap to about 20 points under both the 2027 and 2028 proposals and under both floor versions. Across $11M–$20M per WAR, the gap under cap + floor ranges from 14 to 26 points, against 39 under the status quo.
- **Fixed-dollar thresholds:** applying 2027 dollars directly to 2019–2026 payrolls puts fewer clubs over the cap, so a cap narrows the gap less (to 28–32 points). An open-market floor at fixed dollars narrows it much more, but mainly because 2027 dollars put most early-season clubs under the floor.
- **Calibration:** the simulated status quo (Noll-Scully 2.16) is close to the actual 2019–2026 average (2.10).
- **Limits:** even with a cap, the top payroll quartile still makes the playoffs more often than the bottom, because talent that is already spread out stays spread out and luck still decides much of a season. The effect also varies a lot by season: under cap + floor, the gap ranges from 38.6 points in 2019 to −7.7 in 2026.

## Data Sources

| Source | Data | Location |
|---|---|---|
| [Baseball-Reference](https://www.baseball-reference.com/) | Team WAR by position (including pitchers' WAR), one file per season | `data/raw/war/` |
| [Baseball-Reference](https://www.baseball-reference.com/) | Season standings: wins, losses, runs scored, runs allowed | `data/raw/standings/` |
| [Cot's Baseball Contracts](https://legacy.baseballprospectus.com/compensation/cots/) (Baseball Prospectus) | Payroll sheets listing every player's salary and position, one per team-season, with Opening Day and Competitive Balance Tax (CBT) payroll | `data/raw/salary/` |
| MLB postseason results | Every playoff team and how far it advanced, 2015–2026 | `data/raw/playoffs/playoffs.csv` |

Two payroll measures are used, for different jobs:

- **Opening Day payroll** is what each club actually paid the players who produced that season's WAR, so it is used to estimate what a win costs.
- **CBT payroll** (average annual value of every contract on the 40-man roster, plus benefits) is what the luxury tax, and any cap or floor, would be assessed on, so the simulation uses it. Cot's reports it from 2019 onward, which is why the simulation covers 2019–2026. The two measures are not a fixed multiple of each other: the ratio runs from 0.98 to 1.74 depending on how a club structures its contracts.

## Repository Structure

```
├── data/
│   ├── raw/                          Source files as downloaded (never edited)
│   │   ├── salary/2015 … 2026/       Cot's Baseball Contracts payroll sheets, one per team-season
│   │   ├── standings/                Baseball-Reference season standings (YYYY_standings.csv)
│   │   ├── war/                      Baseball-Reference team WAR by position (YYYY_WAR.csv)
│   │   └── playoffs/                 Postseason teams and results (playoffs.csv)
│   └── processed/                    Built by the pipeline
│       ├── salary/                   Opening Day payroll by player and position group; CBT payroll (cbt_payroll.csv)
│       ├── standings/                Cleaned standings, one file per season
│       ├── war/                      Cleaned WAR, one file per season
│       └── merged_war_standings.csv  WAR, standings, and payroll for every team-season
├── results/                          Regression output, balance metrics, and simulation results
├── figures/                          Paper figures (PNG and PDF) and their captions
├── tables/                           Paper tables (CSV)
├── scripts/                          Analysis pipeline (run run_all.py)
│   ├── config.py                     Folder paths and column settings
│   ├── team_names.py                 Maps every team name and abbreviation to one franchise name
│   ├── thresholds.py                 MLB's cap/floor proposals and how they are applied to each season
│   ├── clean.py                      Step 1: clean WAR and standings
│   ├── clean_payroll.py              Step 1b: clean Cot's Opening Day payroll sheets
│   ├── clean_cbt.py                  Step 1c: pull CBT payroll from the Cot's sheets
│   ├── merge.py                      Step 2: merge WAR, standings, and payroll
│   ├── analysis.py                   Step 3: correlations and WAR-to-wins regressions
│   ├── salary_analysis.py            Step 4: payroll-to-WAR-to-wins regressions
│   ├── figures.py                    Step 5: paper figures and tables (figs 1–10)
│   ├── balance_metrics.py            Step 6: actual competitive balance and who a cap/floor would bind
│   ├── simulate.py                   Step 7: cap/floor simulation
│   ├── simulation_figures.py         Step 8: simulation figures (figs 11–16) and Table 4
│   ├── counterfactual_playoffs.py    Step 9: which clubs would have made the playoffs under each rule (Table 5)
│   └── run_all.py                    Runs every step in order
└── README.md
```

Everything in `data/processed/`, `results/`, `figures/`, and `tables/` is generated from `data/raw/` by `scripts/run_all.py`.

Main outputs from the new steps:

| File | Contents |
|---|---|
| `results/balance_by_season.csv` | Noll-Scully, SD of win %, Gini of wins and payroll, by season |
| `results/playoff_rate_by_payroll.csv`, `results/playoff_concentration.csv` | Playoff access by payroll quartile; repeat and distinct playoff teams |
| `results/cap_floor_binding.csv` | Clubs over the cap and under the floor each season, and the dollars involved |
| `results/simulation_results.csv` | Balance and playoff access for every scenario and specification |
| `results/simulation_clearing.csv` | Talent released by capped clubs vs. talent demanded by floor clubs |
| `results/simulation_team_war.csv` | Each club's WAR, expected wins, and playoff odds before and after the rules |
| `results/counterfactual_playoffs.csv` | Each club-season's wins and playoff result under each rule, holding the club's real luck fixed |
| `tables/table5_playoff_changes.csv` | Table 5: every playoff spot that changes hands under cap + floor, 2019–2026 |
| `tables/table4_simulation_results.csv` | Table 4: balance and playoff access under each rule, with the actual league for comparison |
| `figures/simulation_figure_captions.md` | Captions for figures 11–16 and Table 4, with numbers generated from the results |

## How to Run

Requires Python 3.10 or later and these packages:

```
pip install pandas numpy statsmodels matplotlib seaborn
```

Then, from the `scripts/` folder:

```
python run_all.py
```

This runs every step in order (cleaning → payroll cleaning → CBT payroll → merge → analysis → salary analysis → figures and tables → competitive balance → simulation → simulation figures → counterfactual playoffs) and rebuilds everything in `data/processed/`, `results/`, `figures/`, and `tables/` from the raw data. The full run takes about a minute. Individual steps can also be run on their own (for example, `python simulation_figures.py`) once the earlier steps have been run.

## Project Status

**Analysis complete; paper in progress.** Data collection, the WAR and salary analysis, the competitive balance metrics, and the cap and floor simulation are done, with figures 1–16 and their captions. The full paper for the MIT Sloan Sports Analytics Conference is due December 1, 2026. A possible extension is a sensitivity check that moves hitter and pitcher talent separately, since pitcher WAR appeared cheaper to buy.

## Authors

**Ben Schwartz**  
M.S. Business Analytics  
Brandeis University

**Matthew Shrake**
M.S. Business Analytics
Brandeis University

**Ahmad Namini, Ph.D**
Professor of the Practice of Business Analytics
Brandeis University
