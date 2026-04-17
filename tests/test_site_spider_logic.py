import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from core.resource_handler import extract_markdown_from_url
from core.config import console
import aiohttp
from bs4 import BeautifulSoup

async def test_simple_aiohttp(url):
    console.print(f"[bold yellow]Test: Manual aiohttp for: {url}[/bold yellow]")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20) as response:
                console.print(f"Status: {response.status}")
                if response.status == 200:
                    text = await response.text()
                    console.print(f"HTML length: {len(text)}")
                    return True
                else:
                    return False
    except Exception as e:
        console.print(f"Error: {e}")
        return False

async def test_full_resource_handler():
    url = "https://wiki.cavesofqud.com/wiki/Modding"
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    
    console.print(f"[bold blue]Testing extract_markdown_from_url for: {url}[/bold blue]")
    
    # Let's test if aiohttp alone works first
    if await test_simple_aiohttp(url):
        console.print("[green]Aiohttp simple test passed![/green]")
    else:
        console.print("[red]Aiohttp simple test failed![/red]")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            result = await extract_markdown_from_url(url, crawler, run_config)
            if result.get("success"):
                console.print("[green]Resource Handler SUCCESS![/green]")
            else:
                console.print(f"[red]Resource Handler FAILED:[/red] {result.get('error')}")
        except Exception as e:
            console.print(f"[red]EXCEPTION:[/red] {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_full_resource_handler())
