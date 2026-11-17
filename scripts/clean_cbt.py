"""
Step 1c: pull each team-season's competitive balance tax (CBT) payroll from
the Cot's sheets.

Why this exists separately from Opening Day payroll: the two measure different
things, and the paper needs both. Opening Day payroll is what a club actually
paid the players who produced that season's WAR, which is the right basis for
estimating what a win costs. CBT payroll is the average annual value of every
contract on the 40-man roster plus player benefits, and it is the figure MLB's
luxury tax — and any proposed cap or floor — is actually assessed on.

They are not a fixed multiple of each other. Across 2019-2026 the ratio averages
about 1.19 but ranges from 0.98 to 1.74, because it depends on how a club
structures contracts: deferrals and back-loaded deals push AAV above cash paid,
while cash received in trades pushes it below. So a scaled approximation of CBT
from Opening Day payroll misclassifies exactly the clubs nearest a threshold,
which are the ones a cap analysis turns on.

Coverage: 2019 onward. The 2015-2018 sheets carry only the Opening Day total,
with no CBT line, so those seasons come back empty and the step says so.

Cot's labels this row at least five different ways across seasons and clubs
("Projected 40-man CBT Payroll", "Projected 40-man CB Tax Payroll",
"Projected 40-man CB Payroll", "Projected 26-man CBT Payroll", and plain
"Projected CB Payroll"), and the roster size in the label is sometimes wrong
where the column header above it says 40-man. The parser therefore matches the
label loosely and takes the first full-dollar figure on that row, rather than
relying on a fixed cell position.
"""
import csv
import re

import pandas as pd

import clean_payroll
import config

# Matches every label variant seen across 2019-2026. The roster-size token is
# optional because some sheets omit it entirely.
CBT_LABEL = re.compile(r"projected\s+(\d+-man\s+)?(cbt|cb\s*tax|cb)\s+payroll", re.I)

# A full dollar figure, e.g. $129,390,766 — optionally in parentheses for a
# negative. The abbreviated columns beside it ($66.217) are deliberately not
# matched: those are per-year projections in millions, not the season total.
FULL_DOLLARS = re.compile(r"^\(?\$([\d,]+)\)?$")

# Below this, a figure on the CBT row is a component (benefits, minors) rather
# than the payroll total.
MIN_PLAUSIBLE = 1_000_000

FIRST_SEASON = 2019

CBT_FILE = config.PROCESSED_SALARY_DIR / "cbt_payroll.csv"


def parse_full_dollars(cell):
    """'$129,390,766' -> 129390766. Returns None if the cell is not one."""
    cell = (cell or "").strip()
    match = FULL_DOLLARS.match(cell)
    if not match:
        return None
    value = int(match.group(1).replace(",", ""))
    return -value if cell.startswith("(") else value


def cbt_from_file(path):
    """The CBT payroll on this sheet, or None if the sheet has no CBT row."""
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.reader(handle):
            if not row or not CBT_LABEL.search(row[0] or ""):
                continue
            for cell in row[1:]:
                value = parse_full_dollars(cell)
                if value and value > MIN_PLAUSIBLE:
                    return value
    return None


def main():
    rows, missing = [], []
    for season_dir in sorted(config.RAW_PAYROLL_DIR.iterdir()):
        if not season_dir.is_dir():
            continue
        season = int(season_dir.name)
        if season < FIRST_SEASON:
            continue
        for path in sorted(season_dir.glob("*.csv")):
            team = clean_payroll.team_from_filename(path)
            cbt = cbt_from_file(path)
            if cbt is None:
                missing.append(f"{season} {team}")
                continue
            rows.append({"Year": season, "Team": team, "CBT_Payroll": cbt})

    if not rows:
        print(f"No CBT payrolls found. Sheets before {FIRST_SEASON} have no CBT row.")
        return

    cbt = pd.DataFrame(rows).sort_values(["Year", "Team"]).reset_index(drop=True)

    # Every season present must be complete, or the binding counts below would
    # quietly be computed on a partial league.
    counts = cbt.groupby("Year").size()
    incomplete = counts[counts != 30]
    if not incomplete.empty:
        raise ValueError(f"Seasons without 30 teams: {incomplete.to_dict()}")

    cbt.to_csv(CBT_FILE, index=False)
    print(f"Parsed CBT payroll for {len(cbt)} team-seasons, "
          f"{cbt.Year.min()}-{cbt.Year.max()}")
    if missing:
        print(f"   no CBT row on {len(missing)} sheets: {', '.join(missing[:5])}")

    # Report the spread against Opening Day payroll, since the whole reason for
    # this step is that the two bases are not a fixed multiple of each other.
    merged_path = config.MERGED_FILE
    if merged_path.exists():
        merged = pd.read_csv(merged_path)
        joined = merged.merge(cbt, on=["Year", "Team"], how="inner")
        if len(joined):
            ratio = joined.CBT_Payroll / joined.Cots_OD_Payroll
            print(f"   CBT / Opening Day ratio: mean {ratio.mean():.3f}, "
                  f"range {ratio.min():.3f}-{ratio.max():.3f}, SD {ratio.std():.3f}")
            print("   (a fixed scaling would have SD 0.000 — it does not)")

    print(f"Saved: {CBT_FILE.name}")


if __name__ == "__main__":
    main()
