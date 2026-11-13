# The Price of Parity: Salary Restrictions and Competitive Balance in Major League Baseball

## Abstract

Major League Baseball (MLB) currently utilizes a Competitive Balance Tax (CBT) to discourage excessive payrolls, a system facing particular scrutiny entering the 2026–2027 offseason and upcoming Collective Bargaining Agreement negotiations. Central to these discussions is whether the existing CBT sufficiently promotes competitive balance or whether MLB should follow other major American professional sports leagues by instituting a salary cap, salary floor, or both. This study examines how alternative salary restrictions could affect competitive balance across MLB. Using Opening Day payrolls from Cot’s Baseball Contracts and Wins Above Replacement (WAR) from Baseball-Reference for 330 team-seasons (2015–2026, excluding 2020), we estimate the relationships among team spending, player value, and team wins. Each additional WAR is associated with 0.98 wins, and each additional WAR costs about $14.4 million in 2026 dollars, with no evidence of diminishing returns. Payroll is associated with winning only through the WAR it buys: once WAR is controlled for, payroll has no remaining relationship with wins. However, payroll explains only 13% of the variation in team wins, which limits how much any payroll structure can change outcomes in a single season. These estimates provide the basis for simulating how various salary cap and floor thresholds could redistribute payroll and player talent across all 30 MLB clubs. Monte Carlo simulations of a 162-game season are then used to estimate how each structure affects season outcomes. Competitive balance is evaluated across multiple measures such as the spread of winning percentage and playoff qualification rates by payroll level. By comparing these measures across alternative payroll structures, this study provides data-driven evidence on the potential consequences of salary restrictions as MLB considers changes to its economic structure.

## Research Question

**How would the implementation of a salary cap and salary floor affect competitive balance in Major League Baseball?**

## Methodology

The project combines historical MLB data with statistical modeling and simulation:

- [x] Collect and clean team payroll, WAR, and standings data for 2015–2026 (330 team-seasons; the shortened 2020 season is excluded)
- [x] Estimate the relationship between WAR and team wins, overall and by position
- [x] Estimate the relationship between payroll and player talent (WAR), and between payroll and wins
- [x] Produce figures and tables for the paper
- [ ] Simulate alternative salary cap and salary floor thresholds, redistributing payroll and player talent across all 30 clubs
- [ ] Monte Carlo simulation of 162-game MLB seasons
- [ ] Evaluate competitive balance under each structure using multiple measures

## Key Findings to Date

Based on 330 team-seasons (2015–2026). Payroll is Opening Day payroll, scaled to 2026 dollars by league-average payroll growth.

- **WAR and wins:** each additional WAR is associated with 0.98 more wins (R² = 0.856), and a team with zero WAR projects to about 48 wins, close to the standard replacement-level baseline.
- **Position:** WAR is worth roughly the same number of wins at every position; splitting WAR by position does not improve on total WAR.
- **Payroll and WAR:** each additional WAR costs about $14.4M (95% CI $11.5M–$19.3M). The estimate holds with team and year fixed effects, with no evidence of diminishing returns.
- **Payroll works only through WAR:** once WAR is controlled for, payroll has no remaining relationship with wins (p = 0.97).
- **Limited reach of payroll:** payroll explains only about 13% of the variation in wins. Removing payroll differences entirely would lower the spread of team wins only from 12.7 to about 11.9 wins (luck alone produces about 6.4).
- **Hitters vs. pitchers:** pitcher spending bought WAR more cheaply than hitter spending (about $9.8M vs. $25.4M per WAR), but the difference is not statistically conclusive (p = 0.07).

## Data Sources

| Source | Data | Location |
|---|---|---|
| [Baseball-Reference](https://www.baseball-reference.com/) | Team WAR by position (including pitchers' WAR), one file per season | `data/raw/war/` |
| [Baseball-Reference](https://www.baseball-reference.com/) | Season standings: wins, losses, runs scored, runs allowed | `data/raw/standings/` |
| [Cot's Baseball Contracts](https://legacy.baseballprospectus.com/compensation/cots/) (Baseball Prospectus) | Opening Day payroll sheets listing every player's salary and position, one per team-season | `data/raw/salary/` |

Opening Day payroll is used because it reflects what each team spent on the players who produced that season's WAR. Cot's also reports a separate Competitive Balance Tax payroll (average annual value over the 40-man roster plus benefits), which is not used in the analysis so far.

## Repository Structure

```
├── data/
│   ├── raw/                          Source files as downloaded (never edited)
│   │   ├── salary/2015 … 2026/       Cot's Baseball Contracts Opening Day payroll sheets, one per team-season
│   │   ├── standings/                Baseball-Reference season standings (YYYY_standings.csv)
│   │   └── war/                      Baseball-Reference team WAR by position (YYYY_WAR.csv)
│   └── processed/                    Built by the pipeline
│       ├── salary/                   Opening Day payroll by player and by position group
│       ├── standings/                Cleaned standings, one file per season
│       ├── war/                      Cleaned WAR, one file per season
│       └── merged_war_standings.csv  WAR, standings, and payroll for every team-season
├── results/                          Regression output and summary statistics
├── figures/                          Paper figures (PNG and PDF) and figure_captions.md
├── tables/                           Paper tables (CSV)
├── scripts/                          Analysis pipeline (run run_all.py)
│   ├── config.py                     Folder paths and column settings
│   ├── team_names.py                 Maps every team name and abbreviation to one franchise name
│   ├── clean.py                      Step 1: clean WAR and standings
│   ├── clean_payroll.py              Step 1b: clean Cot's payroll sheets
│   ├── merge.py                      Step 2: merge WAR, standings, and payroll
│   ├── analysis.py                   Step 3: correlations and WAR-to-wins regressions
│   ├── salary_analysis.py            Step 4: payroll-to-WAR-to-wins regressions
│   ├── figures.py                    Step 5: paper figures and tables
│   └── run_all.py                    Runs every step in order
└── README.md
```

Everything in `data/processed/`, `results/`, `figures/`, and `tables/` is generated from `data/raw/` by `scripts/run_all.py`.

## How to Run

Requires Python 3.10 or later and these packages:

```
pip install pandas numpy statsmodels matplotlib seaborn
```

Then, from the `scripts/` folder:

```
python run_all.py
```

This runs every step in order (cleaning → payroll cleaning → merge → analysis → salary analysis → figures and tables) and rebuilds everything in `data/processed/`, `results/`, `figures/`, and `tables/` from the raw data. Individual steps can also be run on their own (for example, `python figures.py`) once the earlier steps have been run.

## Project Status

**Work in progress.** Data collection, cleaning, and the WAR and salary analysis are complete, along with the paper's figures and tables. The salary cap and floor simulation is next, and this repository will be updated as it is completed.

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
