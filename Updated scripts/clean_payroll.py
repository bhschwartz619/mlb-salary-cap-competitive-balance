"""
Step 1b: turn Cot's Baseball Contracts Opening Day sheets into payroll by position.

Expects Salary_Files/<season>/<Cot's sheet>.csv, one file per team-season, and writes:
  - payroll_players.csv      one row per player / money item (for checking)
  - payroll_by_position.csv  one row per team-season, dollars per position group
  - opening_day_salaries.csv one row per rostered player: Year, Team, Player,
                             Position, Pos_Cots, OD_Salary

Cot's used three layouts over 2015-2025:
  2015-2018  header row has a blank first cell + "Pos'n", salary in the first year column,
             total in a "TOTAL - XXX" row
  2019       "Player" / "Pos'n" header, total in "Projected 25-man Opening Day Payroll"
  2021-2025  "Player" / "Pos." header, total in "... Opening Day Payroll"
             (2021-22 leave that row blank and use "Running Payroll Total")
The parser finds the header row, salary column and total by their labels, so it
handles all three.

Salary = the first salary column for the season (Opening Day salary + pro-rated bonus).
Rows with a player name but no position are money not tied to a rostered player:
released/DFA'd players, buyouts, and cash paid to or received from other teams
(received money is negative). These go in the "Other" group.

Cot's Opening Day total is kept as Cots_OD_Payroll (use it for total team payroll).
Pay_Unlisted = Cots_OD_Payroll - sum of rows, for checking.
"""
import csv
import re
from pathlib import Path

import pandas as pd

import config

# File names start with "MLB <city>"; map Cot's city labels to team names
# (same canonical names as team_names.py).
CITY_TO_TEAM = {
    "arizona": "Arizona Diamondbacks",
    "atlanta": "Atlanta Braves",
    "baltimore": "Baltimore Orioles",
    "boston": "Boston Red Sox",
    "chicago al": "Chicago White Sox",
    "chicago nl": "Chicago Cubs",
    "cincinnati": "Cincinnati Reds",
    "cleveland": "Cleveland Guardians",
    "colorado": "Colorado Rockies",
    "detroit": "Detroit Tigers",
    "houston": "Houston Astros",
    "kansas city": "Kansas City Royals",
    "los angeles al": "Los Angeles Angels",
    "la angels": "Los Angeles Angels",
    "los angeles nl": "Los Angeles Dodgers",
    "la dodgers": "Los Angeles Dodgers",
    "miami": "Miami Marlins",
    "milwaukee": "Milwaukee Brewers",
    "minnesota": "Minnesota Twins",
    "new york al": "New York Yankees",
    "new york nl": "New York Mets",
    "oakland": "Oakland Athletics",
    "athletics": "Oakland Athletics",
    "philadelphia": "Philadelphia Phillies",
    "pittsburgh": "Pittsburgh Pirates",
    "san diego": "San Diego Padres",
    "san francisco": "San Francisco Giants",
    "seattle": "Seattle Mariners",
    "st. louis": "St. Louis Cardinals",
    "st louis": "St. Louis Cardinals",
    "texas": "Texas Rangers",
    "tampa bay": "Tampa Bay Rays",
    "toronto": "Toronto Blue Jays",
    "washington": "Washington Nationals",
}

# Known errors in Cot's sheets, applied only to money rows (no position):
# (season, team, player) -> corrected amount
CORRECTIONS = {
    # The "portion paid by Boston" row is listed as +$18,045,000, but it's money
    # the Giants received; Cot's own Opening Day total treats it as negative.
    (2019, "San Francisco Giants", "Sandoval, Pablo"): -18_045_000,
}

# Label rows that end the player list (summary/notes sections)
END_OF_LIST = ("minors", "benefits", "payroll", "total", "threshold", "bonus pool",
               "note", "cbt", "tax", "history")

HITTER_CODES = {"c": "C", "1b": "1B", "lb": "1B", "2b": "2B", "3b": "3B", "ss": "SS",
                "lf": "LF", "cf": "CF", "rf": "RF", "of": "OF", "dh": "DH"}


# -----------------------------
# Helpers
# -----------------------------
def parse_money(text):
    """'$18,000,000' -> 18000000; '-$3,000,000', '($500,000)' -> negative; '' -> 0"""
    text = str(text).strip()
    negative = text.startswith(("-", "(", "$-"))
    digits = re.sub(r"[^\d.]", "", text)
    if not digits or digits == ".":
        return 0.0
    value = float(digits)
    return -value if negative else value


def position_group(pos):
    """
    'rhp-s'/'lhp-s' -> SP; 'rhp'/'lhp'/'rhp-c' -> RP;
    hitters use their first listed position ('1b-of' -> 1B); 'inf' etc. -> UTIL;
    no position -> Other.
    """
    tokens = [t for t in re.split(r"[-/ ]+", str(pos).strip().lower()) if t and t != "."]
    if not tokens:
        return "Other"
    first = tokens[0]
    if first in ("rhp", "lhp", "p"):
        return "SP" if "s" in tokens[1:] else "RP"
    return HITTER_CODES.get(first, "UTIL")


def first_last(name):
    """'DeShields Jr., Delino' -> 'Delino DeShields Jr.' (matches Baseball-Reference style).
    Cot's footnote markers ('Ohtani, Shohei*') are removed."""
    name = name.replace("*", "").strip()
    if "," not in name:
        return name
    last, first = name.split(",", 1)
    return f"{first.strip()} {last.strip()}"


def roster_table(players):
    """Rostered players only: one row per player per team-season."""
    roster = players[players["Group"] != "Other"].copy()
    roster["Player"] = roster["Player"].map(first_last)
    roster = roster.rename(columns={"Pos": "Pos_Cots", "Group": "Position",
                                    "Salary": "OD_Salary"})
    roster = roster[["Year", "Team", "Player", "Position", "Pos_Cots", "OD_Salary"]]
    return roster.sort_values(["Year", "Team", "OD_Salary"],
                              ascending=[True, True, False]).reset_index(drop=True)


def team_from_filename(path):
    """'MLB Chicago AL 15 OD - ....csv' -> 'Chicago White Sox'"""
    match = re.match(r"MLB (.+?) (?:OD )?\d\d\b", Path(path).name)
    city = match.group(1).strip().lower() if match else ""
    if city not in CITY_TO_TEAM:
        raise ValueError(f"[{Path(path).name}] Can't tell which team this is (city '{city}')")
    return CITY_TO_TEAM[city]


# -----------------------------
# Parse one sheet
# -----------------------------
def parse_cots_file(path, season):
    label = f"{season}/{Path(path).name}"
    team = team_from_filename(path)

    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        rows = list(csv.reader(f))
    width = max(len(r) for r in rows)
    rows = [[c.strip() for c in r] + [""] * (width - len(r)) for r in rows]

    # Header row: second cell is "Pos'n" or "Pos."
    header = next((i for i, r in enumerate(rows) if r[1].lower().startswith("pos")), None)
    if header is None:
        raise ValueError(f"[{label}] Could not find the header row")

    # Salary column: first year-labeled column in the header row or the row below
    salary_col = next((c for rr in (header, header + 1) for c, v in enumerate(rows[rr])
                       if re.fullmatch(r"20\d\d", v)), None)
    if salary_col is None:
        raise ValueError(f"[{label}] Could not find the salary column")

    # Column with notes ("Length / Total Value"), e.g. "DFA 1/31/25", "portion paid by..."
    note_col = next((c for c, v in enumerate(rows[header]) if v.lower().startswith("length")), None)

    items, totals = [], {}
    in_list = True
    for r in rows[header + 1:]:
        name, low = r[0], r[0].lower()
        if not name:
            continue
        value = parse_money(r[salary_col])

        # Cot's totals
        if "opening day payroll" in low:
            totals["od"] = value
        elif "running payroll total" in low:
            totals["running"] = value
        elif low.startswith("total"):
            totals["total"] = value

        if "," in name and not name.startswith("*"):
            if not in_list:
                continue
            if not r[1]:
                value = CORRECTIONS.get((season, team, name), value)
            if value == 0:
                continue  # not on the Opening Day payroll (e.g. in the minors)
            items.append({
                "Year": season, "Team": team, "Player": name, "Pos": r[1],
                "Group": position_group(r[1]), "Salary": value,
                "Note": r[note_col] if note_col is not None and not r[1] else "",
            })
        elif any(word in low for word in END_OF_LIST):
            in_list = False
        # other labels ("Injured List", "Injured list replacements", section names)
        # are skipped; Cot's Opening Day totals don't include them

    cots_total = totals.get("od") or totals.get("running") or totals.get("total")
    if cots_total is None:
        print(f"[{label}] No Opening Day total found")

    info = {"Year": season, "Team": team, "Cots_OD_Payroll": cots_total, "File": label}
    return pd.DataFrame(items), info


# -----------------------------
# Team-season totals by position
# -----------------------------
def summarize_by_position(players):
    table = players.pivot_table(index=["Year", "Team"], columns="Group",
                                values="Salary", aggfunc="sum", fill_value=0)
    table = table.reindex(columns=config.PAYROLL_GROUPS, fill_value=0)
    table.columns = [f"Pay_{g}" for g in table.columns]

    table["Pay_OF_All"] = table[["Pay_LF", "Pay_CF", "Pay_RF", "Pay_OF"]].sum(axis=1)
    table["Pay_Pitchers"] = table[["Pay_SP", "Pay_RP"]].sum(axis=1)
    table["Pay_Total"] = table[[f"Pay_{g}" for g in config.PAYROLL_GROUPS]].sum(axis=1)
    table["Pay_Hitters"] = table["Pay_Total"] - table["Pay_Pitchers"] - table["Pay_Other"]
    return table.reset_index()


def main():
    files = sorted(config.RAW_PAYROLL_DIR.glob("*/*.csv"))
    if not files:
        print(f"⚠️ No payroll files found in {config.RAW_PAYROLL_DIR}, skipping payroll.")
        return

    parsed = [parse_cots_file(f, int(f.parent.name)) for f in files]
    players = pd.concat([p for p, _ in parsed], ignore_index=True)
    totals = pd.DataFrame([info for _, info in parsed])

    dupes = totals[totals.duplicated(subset=["Year", "Team"], keep=False)]
    if not dupes.empty:
        raise ValueError(f"More than one payroll file for the same team-season:\n{dupes}")

    by_position = summarize_by_position(players).merge(
        totals.drop(columns="File"), on=["Year", "Team"], how="left", validate="one_to_one")
    by_position["Pay_Unlisted"] = by_position["Cots_OD_Payroll"] - by_position["Pay_Total"]

    # Report
    print(f"Parsed {len(files)} payroll files")
    for year, group in by_position.groupby("Year"):
        missing = sorted(set(CITY_TO_TEAM.values()) - set(group["Team"]))
        if missing:
            print(f"⚠️ {year}: no payroll file for {missing}")

    off = by_position[by_position["Pay_Unlisted"].abs() > 1_000_000]
    print(f"{len(by_position) - len(off)} of {len(by_position)} team-seasons are within $1M "
          f"of Cot's Opening Day total.")
    if not off.empty:
        print("Larger gaps (Cot's total minus listed rows):")
        for _, row in off.iterrows():
            print(f"   {row['Year']} {row['Team']:24} ${row['Pay_Unlisted']:>14,.0f}")

    roster = roster_table(players)

    players.to_csv(config.PAYROLL_PLAYERS_FILE, index=False)
    by_position.to_csv(config.PAYROLL_BY_POSITION_FILE, index=False)
    roster.to_csv(config.OD_SALARIES_FILE, index=False)
    print(f"Saved: {config.PAYROLL_PLAYERS_FILE.name}, {config.PAYROLL_BY_POSITION_FILE.name}, "
          f"{config.OD_SALARIES_FILE.name} ({len(roster)} players)")


if __name__ == "__main__":
    main()
