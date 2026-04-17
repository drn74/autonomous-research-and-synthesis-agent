import asyncio
from core.state import AgentState
from core.config import console
from tools.search import web_search
from database.db_manager import is_url_crawled, save_markdown_to_raw
from core.resource_handler import extract_markdown_from_url
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

async def crawler_node(state: AgentState) -> AgentState:
    console.print(f"\n[yellow]>>> CRAWLER NODE: Searching URLs for {len(state['queries'])} queries...[/yellow]")
    
    if not state['queries']:
        return {**state, "crawled_urls": state.get("crawled_urls", [])}

    new_urls = await web_search(state['queries'])
    console.print(f"[dim]Found {len(new_urls)} unique URLs.[/dim]")
    
    session_id = state["session_id"]
    urls_to_crawl = [url for url in new_urls if not is_url_crawled(url, session_id)]
    console.print(f"[cyan]URLs to download: {len(urls_to_crawl)}[/cyan]")
    
    if not urls_to_crawl:
        return {**state, "crawled_urls": state.get("crawled_urls", [])}
    successfully_crawled = []

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    
    # Parallelismo con Semaforo per evitare ban IP e saturazione banda
    semaphore = asyncio.Semaphore(5)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            crawl_task = progress.add_task("[cyan]Crawling URLs...", total=len(urls_to_crawl))
            
            async def process_url(url):
                async with semaphore:
                    try:
                        result = await extract_markdown_from_url(url, crawler, run_config)
                        if result.get("success"):
                            content = result.get("markdown", "")
                            filepath = save_markdown_to_raw(url, content, session_id)
                            
                            if filepath:
                                progress.console.print(f"[green]✓ Success:[/green] {url[:40]} saved.")
                                return url
                        else:
                            error_msg = result.get("error", "Unknown error")
                            progress.console.print(f"[red]✗ Failed:[/red] {url} - {error_msg}")
                    except Exception as e:
                         progress.console.print(f"[red]✗ Error:[/red] {url} - {e}")
                    finally:
                        progress.advance(crawl_task)
                return None

            # Esecuzione parallela
            results = await asyncio.gather(*[process_url(url) for url in urls_to_crawl])
            successfully_crawled = [url for url in results if url is not None]
            
            failed_count = len(urls_to_crawl) - len(successfully_crawled)
            if failed_count > 0:
                console.print(f"[yellow]Crawler: {len(successfully_crawled)} successi, {failed_count} fallimenti.[/yellow]")
            else:
                console.print(f"[green]Crawler: Tutti i {len(urls_to_crawl)} URL scaricati con successo.[/green]")

    return {
        **state,
        "crawled_urls": state.get("crawled_urls", []) + successfully_crawled
    }
