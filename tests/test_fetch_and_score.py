import unittest
from unittest.mock import Mock, call, patch

import requests

from scripts.fetch_and_score import fetch_weather


class FetchWeatherRetryTests(unittest.TestCase):
    @patch("scripts.fetch_and_score.time.sleep")
    @patch("scripts.fetch_and_score.requests.get")
    def test_retries_then_succeeds(self, mock_get, mock_sleep):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "daily": {
                "temperature_2m_max": [10.0, 12.0],
                "precipitation_sum": [1.0, 3.0],
                "sunshine_duration": [100.0, 200.0],
            }
        }
        mock_get.side_effect = [requests.ReadTimeout("timeout"), response]

        avg_temp, total_precip, avg_sunshine = fetch_weather(1.0, 2.0)

        self.assertEqual((avg_temp, total_precip, avg_sunshine), (11.0, 4.0, 150.0))
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch("scripts.fetch_and_score.time.sleep")
    @patch("scripts.fetch_and_score.requests.get")
    def test_raises_after_max_retries(self, mock_get, mock_sleep):
        mock_get.side_effect = requests.ReadTimeout("timeout")

        with self.assertRaises(requests.ReadTimeout):
            fetch_weather(1.0, 2.0)

        self.assertEqual(mock_get.call_count, 5)
        self.assertEqual(mock_sleep.call_args_list, [call(1), call(2), call(4), call(8)])


if __name__ == "__main__":
    unittest.main()
