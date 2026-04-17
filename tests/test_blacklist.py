import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import os
from tools.search import web_search

class TestBlacklistFiltering(unittest.IsolatedAsyncioTestCase):
    
    @patch("aiohttp.ClientSession.post")
    async def test_web_search_filters_blacklist(self, mock_post):
        # Mocking APP_CONFIG in tools.search to ensure we have the blacklist
        with patch("tools.search.APP_CONFIG", {
            "limits": {"max_search_results_per_query": 5},
            "blacklist": ["youtube.com", "youtu.be"]
        }):
            # Mock Serper API key in environment
            with patch.dict(os.environ, {"SERPER_API_KEY": "fake_key"}):
                
                # Mock response from Serper API
                mock_response = MagicMock()
                mock_response.status = 200
                
                # Setup async json response
                async def mock_json():
                    return {
                        "organic": [
                            {"link": "https://boardgamegeek.com/boardgame/102506/martian-dice"},
                            {"link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
                            {"link": "https://youtu.be/dQw4w9WgXcQ"},
                            {"link": "https://m.youtube.com/watch?v=something"},
                            {"link": "https://www.tabletoptogether.com/2011/11/15/martian-dice/"}
                        ]
                    }
                mock_response.json = mock_json
                
                # Configure the mock context manager for session.post
                mock_context_manager = MagicMock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_post.return_value = mock_context_manager
                
                # Call the function
                queries = ["Martian Dice tutorial"]
                results = await web_search(queries)
                
                # Verify the results
                # Expected results should only contain non-blacklisted URLs
                # Note: results are returned as a list(set(urls)), so the order might vary
                
                # Check that blacklisted URLs are not in the results
                for url in results:
                    self.assertNotIn("youtube.com", url.lower())
                    self.assertNotIn("youtu.be", url.lower())
                
                # Check that valid URLs are present
                self.assertEqual(len(results), 2)
                self.assertIn("https://boardgamegeek.com/boardgame/102506/martian-dice", results)
                self.assertIn("https://www.tabletoptogether.com/2011/11/15/martian-dice/", results)

if __name__ == "__main__":
    unittest.main()
