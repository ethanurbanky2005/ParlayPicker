import os
import requests

SDIO_KEY = os.getenv("SDIO_API_KEY")

def analyze_line_movement(season, week):
    """
    Analyze line movements by calling SportsDataIO line movement endpoints.
    We'll fetch line movement for all games in the specified week and season,
    and compare initial and latest spreads.

    Returns a list of changes with game names and spread movements.
    """

    # First get a list of games for the specified season and week
    url = f"https://api.sportsdata.io/v3/cfb/scores/json/GamesByWeek/{season}/{week}"
    resp = requests.get(url, params={"key": SDIO_KEY})
    if resp.status_code != 200:
        print(f"Error fetching games: {resp.status_code}")
        return []
    games = resp.json()

    changes = []
    for g in games:
        game_id = g["GameID"]
        # Fetch line movement data for each game
        line_url = f"https://api.sportsdata.io/v3/cfb/odds/json/GameOddsLineMovement/{game_id}"
        line_resp = requests.get(line_url, params={"key": SDIO_KEY})
        if line_resp.status_code != 200:
            print(f"Error fetching line movement for GameID {game_id}: {line_resp.status_code}")
            continue
        line_data = line_resp.json()

        # line_data is a list of odds snapshots sorted by time
        # Compare first and last snapshot if available
        if len(line_data) > 1:
            first_spread = extract_spread(line_data[0])
            last_spread = extract_spread(line_data[-1])
            if first_spread is not None and last_spread is not None and first_spread != last_spread:
                changes.append(
                    {
                        "game": f"{g['AwayTeam']} @ {g['HomeTeam']}",
                        "old_spread": first_spread,
                        "new_spread": last_spread,
                    }
                )

    return changes

def extract_spread(odds_snapshot):
    """
    Extract the point spread from an odds snapshot.
    """
    # Each odds_snapshot contains a list of GameOdds
    # We need to find the spread for the main game
    game_odds = odds_snapshot.get("GameOdds", [])
    for odd in game_odds:
        if odd.get("Type") == "Game":
            spread = odd.get("PointSpread")
            if spread is not None:
                return spread
    return None
