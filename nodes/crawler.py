import re
from pathlib import Path
from datetime import datetime
from core.state import AgentState
from core.config import console
from tools.search import web_search
from database.db_manager import is_url_crawled, save_crawled_url
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-_\. ]', '_', name)

async def crawler_node(state: AgentState) -> AgentState:
    console.print(f"\n[yellow]>>> CRAWLER NODE: Searching URLs for {len(state['queries'])} queries...[/yellow]")
    
    if not state['queries']:
        return state

    new_urls = await web_search(state['queries'])
    console.print(f"[dim]Found {len(new_urls)} unique URLs.[/dim]")
    
    urls_to_crawl = [url for url in new_urls if not is_url_crawled(url)]
    console.print(f"[cyan]URLs to download: {len(urls_to_crawl)}[/cyan]")
    
    if not urls_to_crawl:
        return state

    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    session_mock = "sess_001"

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
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        slug = sanitize_filename(url.split('//')[-1][:40])
                        filename = f"{timestamp}_{slug}.md"
                        filepath = raw_dir / filename
                        
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(f"---\nurl: {url}\ntimestamp: {timestamp}\n---\n\n")
                            content = result.markdown if hasattr(result, 'markdown') else str(result.html)
                            f.write(content)
                            
                        save_crawled_url(url, session_mock, str(filepath))
                        progress.console.print(f"[green]✓ Success:[/green] {filename} saved.")
                    else:
                        progress.console.print(f"[red]✗ Failed:[/red] {url}")
                except Exception as e:
                     pass
                finally:
                    progress.advance(crawl_task)

    return state
