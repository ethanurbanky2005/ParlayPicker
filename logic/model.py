import numpy as np
import random

def simulate_game(home_data, away_data):
    """
    Simulate a single game based on team data.
    """
    home_off_epa = home_data.get("PointsPerAttempt", 0)
    home_def_epa = home_data.get("OpponentPointsPerAttempt", 0)
    away_off_epa = away_data.get("PointsPerAttempt", 0)
    away_def_epa = away_data.get("OpponentPointsPerAttempt", 0)

    # Simplistic simulation: Base score + offense EPA - opponent defense EPA + randomness
    home_score = 24 + (home_off_epa - away_def_epa) * 10 + random.gauss(0, 5)
    away_score = 24 + (away_off_epa - home_def_epa) * 10 + random.gauss(0, 5)
    return home_score, away_score

def predict_outcomes(games, adv_data):
    """
    Predict outcomes for a list of games using advanced metrics.
    """
    for game in games:
        home_team = game["HomeTeam"]
        away_team = game["AwayTeam"]

        # Find team metrics
        home_metrics = find_team_metrics(home_team, adv_data)
        away_metrics = find_team_metrics(away_team, adv_data)

        # Monte Carlo simulations
        margins = []
        for _ in range(500):
            hs, as_ = simulate_game(home_metrics, away_metrics)
            margins.append(hs - as_)
        avg_margin = np.mean(margins)

        # Extract spread from odds
        spread = extract_spread(game["Odds"])
        if spread is None:
            spread = 0  # Default to no spread if not available

        # Determine recommended pick
        if avg_margin > spread:
            recommended_pick = home_team
        else:
            recommended_pick = away_team

        # Confidence can be absolute difference between predicted margin and spread
        confidence = abs(avg_margin - spread)

        # Add predictions to game data
        game["pred_margin"] = round(avg_margin, 2)
        game["recommended_pick"] = recommended_pick
        game["confidence"] = round(confidence, 2)

    return games

def find_team_metrics(team, adv_data):
    """
    Locate team in adv_data and return metrics.
    """
    for t in adv_data:
        if t["team"] == team:
            return {
                "PointsPerAttempt": t.get("PointsPerAttempt", 0),
                "OpponentPointsPerAttempt": t.get("OpponentPointsPerAttempt", 0),
            }
    return {"PointsPerAttempt": 0, "OpponentPointsPerAttempt": 0}

def extract_spread(odds):
    """
    Extract the point spread from odds data.
    """
    # Assuming odds contain a list of GameOdds with PointSpread
    if not odds:
        return None
    game_odds = odds.get("GameOdds", [])
    for odd in game_odds:
        if odd.get("OddType") == "Game":
            spread = odd.get("PointSpread")
            if spread is not None:
                return spread
    return None
