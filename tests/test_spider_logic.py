import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from core.resource_handler import extract_markdown_from_url
from core.config import console

async def test_crawl():
    url = "https://wiki.cavesofqud.com/wiki/Modding"
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    
    console.print(f"[bold blue]Testing crawl for: {url}[/bold blue]")
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            # We use a timeout to see if it hangs indefinitely
            result = await asyncio.wait_for(
                extract_markdown_from_url(url, crawler, run_config),
                timeout=60
            )
            
            if result.get("success"):
                console.print("[green]SUCCESS![/green]")
                md = result.get("markdown", "")
                console.print(f"Markdown length: {len(md)}")
                console.print(f"Preview: {md[:200]}...")
            else:
                console.print(f"[red]FAILED:[/red] {result.get('error')}")
                
        except asyncio.TimeoutError:
            console.print("[red]TIMED OUT after 60 seconds![/red]")
        except Exception as e:
            console.print(f"[red]EXCEPTION:[/red] {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_crawl())
