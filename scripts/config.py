"""
Shared settings for the WAR vs. wins pipeline.
Change paths or column lists here and every script picks it up.
"""
import os
from pathlib import Path

# -----------------------------
# Folders
# -----------------------------
# The project folder is one level above this script's folder
# (for_git/ when the scripts are in for_git/scripts/).
# Set the WAR_RESEARCH_DIR environment variable to point somewhere else.
BASE_DIR = Path(os.environ.get(
    "WAR_RESEARCH_DIR",
    Path(__file__).resolve().parent.parent,
))

# data/raw: files as downloaded, never edited
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_STANDINGS_DIR = RAW_DIR / "standings"     # Baseball-Reference standings, one file per season
RAW_WAR_DIR = RAW_DIR / "war"                 # Baseball-Reference WAR leaderboards, one file per season
RAW_PAYROLL_DIR = RAW_DIR / "salary"          # Cot's Opening Day sheets, one subfolder per season

# data/processed: built by the pipeline
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CLEAN_STANDINGS_DIR = PROCESSED_DIR / "standings"
CLEAN_WAR_DIR = PROCESSED_DIR / "war"
PROCESSED_SALARY_DIR = PROCESSED_DIR / "salary"

# Cleaned payroll: one row per player, and one row per team-season
PAYROLL_PLAYERS_FILE = PROCESSED_SALARY_DIR / "payroll_players.csv"
PAYROLL_BY_POSITION_FILE = PROCESSED_SALARY_DIR / "payroll_by_position.csv"
OD_SALARIES_FILE = PROCESSED_SALARY_DIR / "opening_day_salaries.csv"   # one row per rostered player

MERGED_FILE = PROCESSED_DIR / "merged_war_standings.csv"

# results: regression output and summary numbers
RESULTS_DIR = BASE_DIR / "results"
CORRELATION_FILE = RESULTS_DIR / "correlation_matrix.csv"
HEATMAP_FILE = RESULTS_DIR / "correlation_heatmap.png"   # quick-look version; the paper uses figures/fig05
REGRESSION_TOTAL_FILE = RESULTS_DIR / "totalwar_wins_regression.txt"
REGRESSION_POS_FILE = RESULTS_DIR / "war_wins_regression.txt"

# Salary -> WAR -> wins (salary_analysis.py)
SALARY_RESULTS_FILE = RESULTS_DIR / "salary_war_wins_results.txt"
SALARY_SUMMARY_FILE = RESULTS_DIR / "salary_war_wins_summary.csv"
PAYROLL_TO_WINS_FILE = RESULTS_DIR / "payroll_to_wins_table.csv"

# Paper figures and tables (figures.py)
FIGURES_DIR = BASE_DIR / "figures"
TABLES_DIR = BASE_DIR / "tables"

# Make sure every output folder exists (e.g. in a fresh clone of the repository)
for _folder in (CLEAN_STANDINGS_DIR, CLEAN_WAR_DIR, PROCESSED_SALARY_DIR,
                RESULTS_DIR, FIGURES_DIR, TABLES_DIR):
    _folder.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Columns
# -----------------------------
STANDINGS_COLS = ["Tm", "W", "L", "W-L%", "R", "RA"]

# Positional WAR for position players
POSITION_COLS = ["1B", "2B", "3B", "C", "CF", "DH", "LF", "RF", "SS"]

# Pitching WAR. "All P" is kept so pitchers' hitting counts (pre-universal-DH data).
PITCHER_COLS = ["SP", "RP", "All P"]

# Everything kept from the raw WAR files
WAR_COLS = POSITION_COLS + PITCHER_COLS + ["TotalWAR"]

# Columns in the correlation matrix / heatmap
CORRELATION_COLS = WAR_COLS + ["W"]

# Payroll position groups (built from Cot's position codes).
# Cot's often lists outfielders only as "of", so OF holds those players and
# Pay_OF_All (LF + CF + RF + OF) is the reliable outfield total.
# UTIL = hitters with a position code that isn't one of the above.
# Other = money not tied to a rostered player (released/DFA'd players,
# buyouts, cash paid to or received from other teams in trades).
PAYROLL_GROUPS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "OF",
                  "DH", "UTIL", "SP", "RP", "Other"]

# Predictors in the positional regression.
# "All P" is left out for now: if it already includes SP + RP, using all three
# would make the model nearly collinear. Swap SP/RP for "All P" here if preferred.
REGRESSION_POS_COLS = POSITION_COLS + ["SP", "RP"]
