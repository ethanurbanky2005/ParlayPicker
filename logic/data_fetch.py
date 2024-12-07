# logic/data_fetch.py

import os
import requests
import logging
import json

CFBD_KEY = os.getenv("CFBD_API_KEY")
SDIO_KEY = os.getenv("SDIO_API_KEY")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_games_and_odds(season, week):
    """
    Fetch games and associated odds for a given season and week from SportsDataIO.
    """
    # Fetch games
    games_url = f"https://api.sportsdata.io/v3/cfb/scores/json/GamesByWeek/{season}/{week}"
    try:
        games_resp = requests.get(games_url, params={"key": SDIO_KEY}, timeout=10)
        logger.debug(f"GET {games_resp.url} - Status Code: {games_resp.status_code}")
        if games_resp.status_code != 200:
            logger.error(f"Error fetching games: {games_resp.status_code} - {games_resp.text}")
            return []
        games = games_resp.json()
        logger.debug(f"Fetched {len(games)} games.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while fetching games: {e}")
        return []
    except json.decoder.JSONDecodeError as e:
        logger.error(f"JSON decode error while fetching games: {e} - Response Text: {games_resp.text}")
        return []

    # Fetch odds
    odds_url = f"https://api.sportsdata.io/v3/cfb/odds/json/GameOddsByWeek/{season}/{week}"
    try:
        odds_resp = requests.get(odds_url, params={"key": SDIO_KEY}, timeout=10)
        logger.debug(f"GET {odds_resp.url} - Status Code: {odds_resp.status_code}")
        if odds_resp.status_code != 200:
            logger.error(f"Error fetching odds: {odds_resp.status_code} - {odds_resp.text}")
            # Continue without odds
            for game in games:
                game["Odds"] = {}
            return games
        odds_data = odds_resp.json()
        logger.debug(f"Fetched odds for {len(odds_data)} games.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while fetching odds: {e}")
        for game in games:
            game["Odds"] = {}
        return games
    except json.decoder.JSONDecodeError as e:
        logger.error(f"JSON decode error while fetching odds: {e} - Response Text: {odds_resp.text}")
        for game in games:
            game["Odds"] = {}
        return games

    # Inspect a sample of odds_data
    if odds_data:
        sample_odds = odds_data[0]
        logger.debug(f"Sample odds_data: {sample_odds}")

    # Merge odds into games
    games_with_odds = []
    for game in games:
        game_id = game.get("GameId") or game.get("GameID")  # Handle both 'GameId' and 'GameID'
        if not game_id:
            logger.warning(f"Game without GameId found: {game}")
            game["Odds"] = {}
            games_with_odds.append(game)
            continue

        # Normalize 'GameID' key for consistency
        game["GameID"] = game_id

        # Find matching odds
        matching_odds = next(
            (odds for odds in odds_data if odds.get("GameId") == game_id),
            None
        )
        if matching_odds:
            game["Odds"] = matching_odds
        else:
            logger.info(f"No odds found for GameId {game_id}")
            game["Odds"] = {}
        games_with_odds.append(game)

    return games_with_odds

def get_advanced_metrics(season, week):
    """
    Fetch advanced metrics (EPA, SP+) from CFBD for a given season and week.
    """
    # Construct the API URL
    metrics_url = "https://api.collegefootballdata.com/stats/pointsperattempt"
    params = {
        "year": season,
        "week": week,
        "seasonType": "regular"  # Adjust based on your needs
    }
    headers = {
        "x-api-key": CFBD_KEY  # Correct header for CFBD API key
    }

    # Make the GET request with proper error handling
    try:
        resp = requests.get(metrics_url, params=params, headers=headers, timeout=10)
        logger.debug(f"GET {resp.url} - Status Code: {resp.status_code}")
        if resp.status_code != 200:
            logger.error(f"Error fetching advanced metrics: {resp.status_code} - {resp.text}")
            return []
        metrics = resp.json()
        logger.debug(f"Fetched advanced metrics for {len(metrics)} teams.")
        return metrics
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while fetching advanced metrics: {e}")
        return []
    except json.decoder.JSONDecodeError as e:
        logger.error(f"JSON decode error in get_advanced_metrics: {e} - Response Text: {resp.text}")
        return []

def get_player_props(game_id):
    """
    Fetch player props for a given game from SportsDataIO.
    """
    props_url = f"https://api.sportsdata.io/v3/cfb/odds/json/BettingPlayerPropsByGameID/{game_id}"
    try:
        props_resp = requests.get(props_url, params={"key": SDIO_KEY}, timeout=10)
        logger.debug(f"GET {props_resp.url} - Status Code: {props_resp.status_code}")
        if props_resp.status_code != 200:
            logger.error(f"Error fetching player props for GameID {game_id}: {props_resp.status_code} - {props_resp.text}")
            return []
        props = props_resp.json()
        logger.debug(f"Fetched {len(props)} player props for GameID {game_id}.")
        return props
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while fetching player props for GameID {game_id}: {e}")
        return []
    except json.decoder.JSONDecodeError as e:
        logger.error(f"JSON decode error in get_player_props for GameID {game_id}: {e} - Response Text: {props_resp.text}")
        return []

def get_betting_splits(market_id):
    """
    Fetch betting splits for a given market ID from SportsDataIO.
    """
    splits_url = f"https://api.sportsdata.io/v3/cfb/odds/json/BettingSplitsByMarketId/{market_id}"
    try:
        splits_resp = requests.get(splits_url, params={"key": SDIO_KEY}, timeout=10)
        logger.debug(f"GET {splits_resp.url} - Status Code: {splits_resp.status_code}")
        if splits_resp.status_code != 200:
            logger.error(f"Error fetching betting splits for MarketID {market_id}: {splits_resp.status_code} - {splits_resp.text}")
            return []
        splits = splits_resp.json()
        logger.debug(f"Fetched betting splits for MarketID {market_id}.")
        return splits
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while fetching betting splits for MarketID {market_id}: {e}")
        return []
    except json.decoder.JSONDecodeError as e:
        logger.error(f"JSON decode error in get_betting_splits for MarketID {market_id}: {e} - Response Text: {splits_resp.text}")
        return []

def get_injured_players():
    """
    Fetch injured players from SportsDataIO.
    """
    injuries_url = f"https://api.sportsdata.io/v3/cfb/scores/json/InjuredPlayers"
    try:
        injuries_resp = requests.get(injuries_url, params={"key": SDIO_KEY}, timeout=10)
        logger.debug(f"GET {injuries_resp.url} - Status Code: {injuries_resp.status_code}")
        if injuries_resp.status_code != 200:
            logger.error(f"Error fetching injured players: {injuries_resp.status_code} - {injuries_resp.text}")
            return []
        injuries = injuries_resp.json()
        logger.debug(f"Fetched {len(injuries)} injured players.")
        return injuries
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while fetching injured players: {e}")
        return []
    except json.decoder.JSONDecodeError as e:
        logger.error(f"JSON decode error in get_injured_players: {e} - Response Text: {injuries_resp.text}")
        return []
