import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio
from nodes.analyst import run_local_analysis

class TestAnalystBehavior(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.test_file = "test_input.txt"
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("Sample content for analysis")

    def tearDown(self):
        import os
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        self.loop.close()

    @patch("aiohttp.ClientSession.post")
    def test_noisy_json_extraction(self, mock_post):
        # Case 1: Noisy JSON (text before and after)
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response": 'Here is the result: {"entities": ["A", "B"], "knowledge_chunks": []} Hope it helps!'
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        result = self.loop.run_until_complete(
            run_local_analysis(self.test_file, "goal", "127.0.0.1", "en")
        )

        self.assertIn("entities", result)
        self.assertEqual(result["entities"], ["A", "B"])
        self.assertNotIn("error", result)

    @patch("aiohttp.ClientSession.post")
    @patch("nodes.analyst.console.print")
    def test_invalid_json_handling(self, mock_print, mock_post):
        # Case 2: Malformed JSON (unclosed brace)
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response": '{"entities": ["A", "B"], "knowledge_chunks": [' # Malformed
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        result = self.loop.run_until_complete(
            run_local_analysis(self.test_file, "goal", "127.0.0.1", "en")
        )

        self.assertIn("error", result)
        self.assertIn("JSON parsing error", result["error"])
        mock_print.assert_called()
        # Verify it contains "[red]Error parsing JSON."
        args, kwargs = mock_print.call_args
        self.assertIn("[red]Error parsing JSON. Partial output:[/red]", args[0])

    @patch("aiohttp.ClientSession.post")
    def test_json_list_handling(self, mock_post):
        # Case 3: JSON is a list, not an object
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response": '["entity1", "entity2"]'
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        result = self.loop.run_until_complete(
            run_local_analysis(self.test_file, "goal", "127.0.0.1", "en")
        )

        self.assertIn("error", result)
        self.assertEqual(result["error"], "JSON is not an object.")

if __name__ == "__main__":
    unittest.main()
