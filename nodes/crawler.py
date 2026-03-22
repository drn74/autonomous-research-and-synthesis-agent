from core.state import AgentState
from core.config import console
from tools.search import web_search
from database.db_manager import is_url_crawled, save_markdown_to_raw
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

async def crawler_node(state: AgentState) -> AgentState:
    console.print(f"\n[yellow]>>> CRAWLER NODE: Searching URLs for {len(state['queries'])} queries...[/yellow]")
    
    if not state['queries']:
        return {**state, "crawled_urls": []}

    new_urls = await web_search(state['queries'])
    console.print(f"[dim]Found {len(new_urls)} unique URLs.[/dim]")
    
    urls_to_crawl = [url for url in new_urls if not is_url_crawled(url)]
    console.print(f"[cyan]URLs to download: {len(urls_to_crawl)}[/cyan]")
    
    if not urls_to_crawl:
        return {**state, "crawled_urls": []}

    session_mock = "sess_001"
    successfully_crawled = []

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            crawl_task = progress.add_task("[cyan]Crawling URLs...", total=len(urls_to_crawl))
            
            for url in urls_to_crawl:
                progress.update(crawl_task, description=f"[cyan]Downloading: {url[:60]}...[/cyan]")
                try:
                    result = await crawler.arun(url=url, config=run_config)
                    if result.success:
                        content = result.markdown if hasattr(result, 'markdown') else str(result.html)
                        filepath = save_markdown_to_raw(url, content, session_mock)
                        
                        if filepath:
                            progress.console.print(f"[green]✓ Success:[/green] {url[:40]} saved.")
                            successfully_crawled.append(url)
                    else:
                        progress.console.print(f"[red]✗ Failed:[/red] {url}")
                except Exception as e:
                     progress.console.print(f"[red]✗ Error:[/red] {url} - {e}")
                finally:
                    progress.advance(crawl_task)

    return {
        **state,
        "crawled_urls": successfully_crawled
    }
