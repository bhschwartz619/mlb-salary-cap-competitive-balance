"""
Shared settings for the WAR vs. wins pipeline.
Change paths or column lists here and every script picks it up.
"""
import os
from pathlib import Path

# -----------------------------
# Folders
# -----------------------------
# By default, the data folders are one level above this script's folder
# (e.g. for_git/ when the scripts are in for_git/Updated scripts/).
# Set the WAR_RESEARCH_DIR environment variable to point somewhere else.
BASE_DIR = Path(os.environ.get(
    "WAR_RESEARCH_DIR",
    Path(__file__).resolve().parent.parent,
))

RAW_STANDINGS_DIR = BASE_DIR / "Standings_Files"
RAW_WAR_DIR = BASE_DIR / "WAR_Files"
RAW_PAYROLL_DIR = BASE_DIR / "Salary_Files"   # Cot's sheets, one subfolder per season
CLEAN_STANDINGS_DIR = BASE_DIR / "clean_Standings_Files"
CLEAN_WAR_DIR = BASE_DIR / "clean_WAR_Files"

# Cleaned payroll: one row per player, and one row per team-season
PAYROLL_PLAYERS_FILE = BASE_DIR / "payroll_players.csv"
PAYROLL_BY_POSITION_FILE = BASE_DIR / "payroll_by_position.csv"
OD_SALARIES_FILE = BASE_DIR / "opening_day_salaries.csv"   # one row per rostered player

MERGED_FILE = BASE_DIR / "merged_war_standings.csv"
CORRELATION_FILE = BASE_DIR / "correlation_matrix.csv"
HEATMAP_FILE = BASE_DIR / "correlation_heatmap.png"
REGRESSION_TOTAL_FILE = BASE_DIR / "totalwar_wins_regression.txt"
REGRESSION_POS_FILE = BASE_DIR / "war_wins_regression.txt"

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
