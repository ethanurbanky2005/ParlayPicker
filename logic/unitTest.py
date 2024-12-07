# tests/test_data_fetch.py

import unittest
from unittest.mock import patch
from logic.data_fetch import get_games_and_odds, get_advanced_metrics

class TestDataFetch(unittest.TestCase):

    @patch('logic.data_fetch.requests.get')
    def test_get_games_and_odds_success(self, mock_get):
        # Mock successful API responses
        mock_games_response = unittest.mock.Mock()
        mock_games_response.status_code = 200
        mock_games_response.json.return_value = [
            {"GameId": 1, "AwayTeam": "TeamA", "HomeTeam": "TeamB"},
            {"GameID": 2, "AwayTeam": "TeamC", "HomeTeam": "TeamD"}
        ]

        mock_odds_response = unittest.mock.Mock()
        mock_odds_response.status_code = 200
        mock_odds_response.json.return_value = [
            {"GameId": 1, "Odds": "some_odds"},
            {"GameId": 2, "Odds": "some_other_odds"}
        ]

        # Configure the mock to return responses in order
        mock_get.side_effect = [mock_games_response, mock_odds_response]

        games_with_odds = get_games_and_odds(2024, 15)
        self.assertEqual(len(games_with_odds), 2)
        self.assertIn("GameID", games_with_odds[0])
        self.assertIn("Odds", games_with_odds[0])
        self.assertEqual(games_with_odds[0]["GameID"], 1)
        self.assertEqual(games_with_odds[0]["Odds"]["Odds"], "some_odds")

    @patch('logic.data_fetch.requests.get')
    def test_get_advanced_metrics_success(self, mock_get):
        # Mock successful API response
        mock_metrics_response = unittest.mock.Mock()
        mock_metrics_response.status_code = 200
        mock_metrics_response.json.return_value = [
            {"Team": "TeamA", "PPA": 7.5},
            {"Team": "TeamB", "PPA": 6.8}
        ]
        mock_get.return_value = mock_metrics_response

        metrics = get_advanced_metrics(2024, 15)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0]["Team"], "TeamA")
        self.assertEqual(metrics[0]["PPA"], 7.5)

if __name__ == '__main__':
    unittest.main()