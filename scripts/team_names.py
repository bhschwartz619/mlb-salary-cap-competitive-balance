"""
Shared team-name normalization used by every script in the pipeline.

Every alias (abbreviation, nickname, old franchise name) maps to ONE canonical
franchise name, so ATH/OAK/Athletics are always the same team and
CLE/Indians/Guardians are always the same team.
"""
import pandas as pd

# canonical franchise name -> every alias that should map to it
TEAM_ALIASES = {
    "Arizona Diamondbacks": ["ARI", "AZ", "Diamondbacks"],
    "Atlanta Braves": ["ATL", "Braves"],
    "Baltimore Orioles": ["BAL", "Orioles"],
    "Boston Red Sox": ["BOS", "Red Sox"],
    "Chicago Cubs": ["CHC", "Cubs"],
    "Chicago White Sox": ["CHW", "CWS", "White Sox"],
    "Cincinnati Reds": ["CIN", "Reds"],
    "Cleveland Guardians": ["CLE", "Cleveland", "Guardians",
                            "Cleveland Indians", "Indians"],
    "Colorado Rockies": ["COL", "Rockies"],
    "Detroit Tigers": ["DET", "Tigers"],
    "Houston Astros": ["HOU", "Astros"],
    "Kansas City Royals": ["KCR", "KC", "KCA", "Royals"],
    "Los Angeles Angels": ["LAA", "ANA", "CAL", "Angels",
                           "Los Angeles Angels of Anaheim",
                           "Anaheim Angels", "California Angels"],
    "Los Angeles Dodgers": ["LAD", "Dodgers"],
    "Miami Marlins": ["MIA", "FLA", "Marlins", "Florida Marlins"],
    "Milwaukee Brewers": ["MIL", "Brewers"],
    "Minnesota Twins": ["MIN", "Twins"],
    "New York Mets": ["NYM", "Mets"],
    "New York Yankees": ["NYY", "Yankees"],
    "Oakland Athletics": ["OAK", "ATH", "Athletics", "Oakland",
                          "Oakland A's", "A's", "Sacramento Athletics"],
    "Philadelphia Phillies": ["PHI", "Phillies"],
    "Pittsburgh Pirates": ["PIT", "Pirates"],
    "San Diego Padres": ["SDP", "SD", "Padres"],
    "San Francisco Giants": ["SFG", "SF", "Giants"],
    "Seattle Mariners": ["SEA", "Mariners"],
    "St. Louis Cardinals": ["STL", "Cardinals", "St Louis Cardinals"],
    "Tampa Bay Rays": ["TBR", "TB", "TBD", "TBA", "Rays",
                       "Tampa Bay Devil Rays", "Devil Rays"],
    "Texas Rangers": ["TEX", "Rangers"],
    "Toronto Blue Jays": ["TOR", "Blue Jays"],
    "Washington Nationals": ["WSN", "WSH", "WAS", "Nationals",
                             "Montreal Expos", "MON", "Expos"],
}


def _clean_key(name):
    # Case-insensitive, ignores extra spaces and Baseball-Reference's "*" markers
    return " ".join(str(name).replace("*", "").split()).upper()


_LOOKUP = {}
for canonical, aliases in TEAM_ALIASES.items():
    for alias in [canonical] + aliases:
        key = _clean_key(alias)
        if key in _LOOKUP and _LOOKUP[key] != canonical:
            raise ValueError(f"Alias '{alias}' maps to two different teams")
        _LOOKUP[key] = canonical


def normalize_team_name(name):
    """Return the canonical franchise name, or None if the name isn't a known team."""
    if pd.isna(name):
        return None
    return _LOOKUP.get(_clean_key(name))


def standardize_team_column(df, col, label=""):
    """
    Normalize a team column, drop rows that aren't real teams (e.g. 'League Average'),
    and stop with an error if two rows collapse into the same team
    (e.g. a file that contains both ATH and OAK).
    """
    df = df.copy()
    original = df[col]
    df[col] = original.apply(normalize_team_name)

    unknown = original[df[col].isna()].dropna().unique()
    if len(unknown):
        print(f"[{label}] Dropped rows with unrecognized team names: {list(unknown)}")
    df = df[df[col].notna()]

    dupes = df.loc[df[col].duplicated(keep=False), col].unique()
    if len(dupes):
        raise ValueError(
            f"[{label}] These teams appear more than once after normalization: {list(dupes)}"
        )

    return df
