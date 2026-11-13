"""
Step 1: clean the raw standings and WAR files, one CSV per season.
"""
import re
import pandas as pd
from pathlib import Path

import config
from team_names import standardize_team_column


def year_from_filename(path):
    # e.g. "2015_WAR.csv" -> "2015"
    return Path(path).stem.split("_")[0]


# -----------------------------
# Standings
# -----------------------------
def clean_standings_file(path):
    df = pd.read_csv(path)
    df = df[config.STANDINGS_COLS]
    df = standardize_team_column(df, "Tm", label=Path(path).name)
    return df


# -----------------------------
# WAR
# -----------------------------
# The raw WAR files are leaderboards: every column is sorted on its own, so a
# row is a rank, not a team. Each cell holds team + value run together,
# e.g. "STL29.9", "COL-0.2" or "St. Louis Cardinals50.1".
WAR_CELL = re.compile(r"^(.*?)(-?\d+(?:\.\d+)?)$")

# Raw column name -> name used in the pipeline
WAR_RENAME = {"Total": "TotalWAR"}


def split_war_cell(cell):
    """'STL29.9' -> ('STL', 29.9). Returns (None, None) if it can't be parsed."""
    if pd.isna(cell):
        return None, None
    match = WAR_CELL.match(str(cell).strip())
    if not match:
        return None, None
    return match.group(1).strip(), float(match.group(2))


def clean_war_file(path):
    label = Path(path).name
    raw = pd.read_csv(path).rename(columns=WAR_RENAME)

    wanted = [c for c in config.WAR_COLS if c in raw.columns]
    missing = [c for c in config.WAR_COLS if c not in raw.columns]
    if missing:
        print(f"[{label}] Missing columns: {missing}")

    # Turn each leaderboard column into (Team, value) pairs
    pieces = []
    for col in wanted:
        rows = []
        for cell in raw[col]:
            team, value = split_war_cell(cell)
            if team is None:
                if pd.notna(cell):
                    print(f"[{label}] Could not read cell '{cell}' in column {col}")
                continue
            rows.append({"Team": team, col: value})

        col_df = standardize_team_column(pd.DataFrame(rows), "Team",
                                         label=f"{label} / {col}")
        pieces.append(col_df.set_index("Team"))

    # Line the columns back up by team: one row per team
    df = pd.concat(pieces, axis=1).reset_index()

    incomplete = df[df[wanted].isna().any(axis=1)]["Team"].tolist()
    if incomplete:
        print(f"[{label}] Teams missing a value in some column: {incomplete}")

    return df[["Team"] + wanted].sort_values("Team").reset_index(drop=True)


# -----------------------------
# Run both
# -----------------------------
def clean_folder(input_dir, output_dir, clean_fn, suffix):
    output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        print(f"⚠️ No CSV files found in {input_dir}")

    for file in files:
        cleaned = clean_fn(file)
        out_file = output_dir / f"{year_from_filename(file)}_{suffix}.csv"
        cleaned.to_csv(out_file, index=False)
        print(f"Cleaned: {file.name} → {out_file.name} ({len(cleaned)} teams)")


def main():
    print("=== Cleaning standings ===")
    clean_folder(config.RAW_STANDINGS_DIR, config.CLEAN_STANDINGS_DIR,
                 clean_standings_file, "standings_cleaned")

    print("\n=== Cleaning WAR ===")
    clean_folder(config.RAW_WAR_DIR, config.CLEAN_WAR_DIR,
                 clean_war_file, "WAR_cleaned")


if __name__ == "__main__":
    main()
