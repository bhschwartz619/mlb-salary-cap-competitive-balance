"""
Shared settings for the WAR vs. wins pipeline.
Change paths or column lists here and every script picks it up.
"""
import os
from pathlib import Path

# -----------------------------
# Folders
# -----------------------------
# Set the WAR_RESEARCH_DIR environment variable to point somewhere else
# (e.g. for testing); otherwise the OneDrive folder is used.
BASE_DIR = Path(os.environ.get(
    "WAR_RESEARCH_DIR",
    Path(__file__).resolve().parent.parent,
))

RAW_STANDINGS_DIR = BASE_DIR / "Standings_Files"
RAW_WAR_DIR = BASE_DIR / "WAR_Files"
CLEAN_STANDINGS_DIR = BASE_DIR / "clean_Standings_Files"
CLEAN_WAR_DIR = BASE_DIR / "clean_WAR_Files"

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

# Predictors in the positional regression.
# "All P" is left out for now: if it already includes SP + RP, using all three
# would make the model nearly collinear. Swap SP/RP for "All P" here if preferred.
REGRESSION_POS_COLS = POSITION_COLS + ["SP", "RP"]
