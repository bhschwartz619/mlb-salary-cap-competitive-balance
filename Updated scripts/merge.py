"""
Step 2: join each season's cleaned WAR and standings into one dataset.
"""
import pandas as pd
from pathlib import Path

import config
from team_names import standardize_team_column


def merge_single_season(war_file, standings_file, year):
    war = pd.read_csv(war_file)
    standings = pd.read_csv(standings_file)

    # Safety net: re-normalize and check for duplicate teams
    war = standardize_team_column(war, "Team", label=Path(war_file).name)
    standings = standardize_team_column(standings, "Tm", label=Path(standings_file).name)

    merged = war.merge(
        standings, left_on="Team", right_on="Tm",
        how="outer", validate="one_to_one", indicator=True
    )

    war_only = merged.loc[merged["_merge"] == "left_only", "Team"].tolist()
    standings_only = merged.loc[merged["_merge"] == "right_only", "Tm"].tolist()
    if war_only or standings_only:
        print(f"⚠️ {year}: unmatched teams")
        if war_only:
            print(f"   In WAR file only: {war_only}")
        if standings_only:
            print(f"   In standings file only: {standings_only}")

    # Keep WAR rows (left join), drop the helper columns
    merged = merged[merged["_merge"] != "right_only"].drop(columns=["_merge", "Tm"])
    merged.insert(0, "Year", year)
    return merged


def add_payroll(full_df):
    """Join payroll by position (if it has been built) on Year + Team."""
    if not config.PAYROLL_BY_POSITION_FILE.exists():
        print("No payroll file found, merging without payroll.")
        return full_df

    payroll = pd.read_csv(config.PAYROLL_BY_POSITION_FILE)
    merged = full_df.merge(payroll, on=["Year", "Team"], how="left",
                           validate="one_to_one", indicator=True)

    missing = merged[merged["_merge"] == "left_only"]
    if not missing.empty:
        print(f"⚠️ {len(missing)} team-seasons have no payroll data:")
        print(missing.groupby("Year")["Team"].apply(list).to_string())
    merged = merged.drop(columns="_merge")

    # Outfield WAR as one group, to match Pay_OF_All
    merged["OF_All"] = merged[["LF", "CF", "RF"]].sum(axis=1, min_count=1)

    # Payroll relative to that season's league average (1.0 = average),
    # so seasons with different overall salary levels can be compared
    for col in ["Cots_OD_Payroll", "Pay_Total"]:
        merged[f"{col}_Rel"] = merged[col] / merged.groupby("Year")[col].transform("mean")

    return merged


def main():
    all_data = []

    for war_file in sorted(config.CLEAN_WAR_DIR.glob("*_WAR_cleaned.csv")):
        year = int(war_file.stem.split("_")[0])
        standings_file = config.CLEAN_STANDINGS_DIR / f"{year}_standings_cleaned.csv"

        if not standings_file.exists():
            print(f"⚠️ Missing cleaned standings file for {year}, skipping.")
            continue

        all_data.append(merge_single_season(war_file, standings_file, year))

    if not all_data:
        raise RuntimeError("No seasons were merged. Run clean.py first.")

    full_df = pd.concat(all_data, ignore_index=True)

    dupes = full_df[full_df.duplicated(subset=["Year", "Team"], keep=False)]
    if not dupes.empty:
        raise ValueError(f"Duplicate team-seasons found:\n{dupes[['Year', 'Team']]}")

    full_df = add_payroll(full_df)

    print("\nTeams per season:")
    print(full_df.groupby("Year")["Team"].nunique().to_string())

    full_df.to_csv(config.MERGED_FILE, index=False)
    print(f"\nMerged WAR + standings saved to: {config.MERGED_FILE}")


if __name__ == "__main__":
    main()
