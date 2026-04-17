import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from core.resource_handler import is_xml, process_xml

class TestXMLParsing(unittest.IsolatedAsyncioTestCase):

    def _mock_aiohttp_context(self, mock_response):
        """Helper to mock aiohttp context manager."""
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        return mock_cm

    async def test_is_xml_by_extension(self):
        # Case: .xml extension
        self.assertTrue(await is_xml("http://example.com/feed.xml"))
        # Case: .rss extension
        self.assertTrue(await is_xml("https://test.it/rss.rss"))

    async def test_is_xml_by_content_type(self):
        # Case: application/xml
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_response.status = 200
        
        mock_cm = self._mock_aiohttp_context(mock_response)
        
        with patch('aiohttp.ClientSession.head', return_value=mock_cm):
            self.assertTrue(await is_xml("http://example.com/api"))

        # Case: application/rss+xml
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'application/rss+xml'}
        mock_response.status = 200
        
        mock_cm = self._mock_aiohttp_context(mock_response)
        
        with patch('aiohttp.ClientSession.head', return_value=mock_cm):
            self.assertTrue(await is_xml("http://example.com/feed"))

        # Case: text/html (not XML)
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.status = 200
        
        mock_cm = self._mock_aiohttp_context(mock_response)
        
        with patch('aiohttp.ClientSession.head', return_value=mock_cm):
            self.assertFalse(await is_xml("http://example.com/page.html"))

    async def test_process_xml_rss(self):
        rss_content = """<?xml version="1.0" encoding="UTF-8" ?>
        <rss version="2.0">
        <channel>
            <title>Test RSS Feed</title>
            <item>
                <title>Item 1</title>
                <description>Description for item 1 with <p>HTML tags</p></description>
            </item>
            <item>
                <title>Item 2</title>
                <description>Description for item 2</description>
            </item>
        </channel>
        </rss>
        """
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=rss_content)
        
        mock_cm = self._mock_aiohttp_context(mock_response)

        with patch('aiohttp.ClientSession.get', return_value=mock_cm):
            result = await process_xml("http://example.com/rss")
            self.assertTrue(result["success"])
            markdown = result["markdown"]
            self.assertIn("Test RSS Feed", markdown)
            self.assertIn("Item 1", markdown)
            self.assertIn("Description for item 1", markdown)
            self.assertIn("Item 2", markdown)
            self.assertNotIn("<p>", markdown)

    async def test_process_xml_atom(self):
        atom_content = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Test Atom Feed</title>
          <entry>
            <title>Entry 1</title>
            <summary>Summary 1</summary>
          </entry>
          <entry>
            <title>Entry 2</title>
            <summary>Summary 2</summary>
          </entry>
        </feed>
        """
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=atom_content)
        
        mock_cm = self._mock_aiohttp_context(mock_response)

        with patch('aiohttp.ClientSession.get', return_value=mock_cm):
            result = await process_xml("http://example.com/atom")
            self.assertTrue(result["success"])
            markdown = result["markdown"]
            self.assertIn("Test Atom Feed", markdown)
            self.assertIn("Entry 1", markdown)
            self.assertIn("Summary 1", markdown)
            self.assertIn("Entry 2", markdown)

    async def test_process_xml_generic(self):
        generic_xml = """<root>
            <node1>Some significant text content that should be extracted because it is long enough.</node1>
            <node2>Short</node2>
            <node3>Another long text node that exceeds the threshold of twenty characters.</node3>
        </root>
        """
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=generic_xml)
        
        mock_cm = self._mock_aiohttp_context(mock_response)

        with patch('aiohttp.ClientSession.get', return_value=mock_cm):
            result = await process_xml("http://example.com/generic.xml")
            self.assertTrue(result["success"])
            markdown = result["markdown"]
            self.assertIn("Some significant text content", markdown)
            self.assertIn("Another long text node", markdown)
            self.assertNotIn("Short", markdown)

if __name__ == '__main__':
    unittest.main()
