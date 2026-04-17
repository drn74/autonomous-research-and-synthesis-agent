import asyncio
import urllib.parse
from bs4 import BeautifulSoup
from core.state import AgentState
from core.config import console, APP_CONFIG
from database.db_manager import is_url_crawled, save_markdown_to_raw, get_pending_crawl_urls, add_pending_urls, count_crawled_urls_for_domain
from core.resource_handler import extract_markdown_from_url
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import aiohttp
import xml.etree.ElementTree as ET

def get_domain_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc

async def fetch_sitemap_urls(domain: str) -> list[str]:
    """Tenta di estrarre gli URL dal sitemap.xml del dominio, supportando sitemap index in parallelo."""
    sitemap_url = f"https://{domain}/sitemap.xml"
    all_urls = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(sitemap_url, timeout=10) as response:
                if response.status != 200:
                    return []
                xml_content = await response.text()
                root = ET.fromstring(xml_content)
                
                # Namespace mapping
                namespaces = {
                    'smap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
                }
                
                # Caso 1: È un indice di sitemap (contiene altri sitemap)
                if 'sitemapindex' in root.tag:
                    sub_sitemaps = [loc.text for loc in root.findall('smap:sitemap/smap:loc', namespaces)]
                    console.print(f"[dim]Rilevato sitemapindex per {domain}. Sub-sitemaps: {len(sub_sitemaps)}[/dim]")
                    
                    # Parallelizziamo il fetch di max 3 sub-sitemap
                    async def fetch_sub(url):
                        try:
                            async with session.get(url, timeout=10) as sub_resp:
                                if sub_resp.status == 200:
                                    sub_xml = await sub_resp.text()
                                    sub_root = ET.fromstring(sub_xml)
                                    return [loc.text for loc in sub_root.findall('smap:url/smap:loc', namespaces)]
                        except Exception:
                            pass
                        return []

                    results = await asyncio.gather(*[fetch_sub(u) for u in sub_sitemaps[:3]])
                    for urls in results:
                        all_urls.extend(urls)
                
                # Caso 2: È un sitemap standard
                else:
                    urls = [loc.text for loc in root.findall('smap:url/smap:loc', namespaces)]
                    all_urls.extend(urls)
                
                console.print(f"[dim]Trovati {len(all_urls)} URL totali dal sitemap di {domain}[/dim]")
    except Exception as e:
        console.print(f"[dim]Errore nel recupero sitemap per {domain}: {e}[/dim]")
    return all_urls

def extract_internal_links(html: str, base_url: str, domain: str) -> list[str]:
    """Estrae i link interni (stesso dominio) da una stringa HTML."""
    links = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urllib.parse.urljoin(base_url, href)
            full_url, _ = urllib.parse.urldefrag(full_url)
            if full_url.startswith('http') and get_domain_from_url(full_url) == domain:
                links.append(full_url)
    except Exception:
        pass
    return list(set(links))

async def site_spider_node(state: AgentState) -> AgentState:
    spider_config = APP_CONFIG.get("site_spider", {})
    if not spider_config.get("enabled", True):
        console.print("[yellow]Site Spider disabilitato dalla configurazione.[/yellow]")
        return {**state, "mode": "normal"}

    dense_domains = state.get("dense_domains", [])
    mode = state.get("mode", "normal")
    
    if not dense_domains:
        console.print("[yellow]Site Spider attivato, ma nessun dominio target fornito. Ritorno alla normalità.[/yellow]")
        return {**state, "mode": "normal"}

    max_pages = spider_config.get("max_pages_per_domain", 20)
    max_depth = spider_config.get("max_depth", 3)
    delay = spider_config.get("request_delay_seconds", 1.5)
    use_sitemap = spider_config.get("use_sitemap", True)

    session_id = state["session_id"]
    all_new_crawled_urls = []
    global_is_saturated = False

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    console.print(f"\n[magenta]>>> SITE SPIDER NODE: Inizio scansione (Modo: {mode}) su {len(dense_domains)} domini...[/magenta]")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for target in dense_domains:
            domain = target.get("domain")
            entry_points = target.get("entry_points", [])
            
            if not domain:
                continue

            console.print(f"\n[bold yellow]Target:[/bold yellow] {domain}")
            current_count = count_crawled_urls_for_domain(session_id, domain)
            if current_count >= max_pages:
                console.print(f"[yellow]Limit reached for {domain} ({current_count}/{max_pages}). Skipping domain.[/yellow]")
                global_is_saturated = True
                continue

            queue = [(url, 0) for url in entry_points]
            if mode == "archivist":
                db_pending = get_pending_crawl_urls(session_id)
                existing_urls = {u for u, d in queue}
                for db_url, db_depth in db_pending:
                    if db_url not in existing_urls:
                        queue.append((db_url, db_depth))

            if use_sitemap and mode != "archivist":
                sitemap_urls = await fetch_sitemap_urls(domain)
                queue.extend([(url, 1) for url in sitemap_urls if url not in [u for u, d in queue]])
            
            if not queue:
                queue = [(f"https://{domain}", 0)]

            visited_in_this_run = set()
            pages_downloaded_for_domain = 0
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                remaining_pages = max_pages - current_count
                spider_task = progress.add_task(f"[magenta]Spidering {domain}...", total=remaining_pages)
                
                while queue and pages_downloaded_for_domain < max_pages:
                    current_url, current_depth = queue.pop(0)
                    if current_url in visited_in_this_run:
                        continue

                    if is_url_crawled(current_url, session_id):
                        import sqlite3
                        conn = sqlite3.connect("research.db")
                        cursor = conn.cursor()
                        cursor.execute("SELECT status, local_path FROM crawled_urls WHERE url = ? AND session_id = ?", (current_url, session_id))
                        row = cursor.fetchone()
                        conn.close()
                        if row and (row[1] or row[0] == 'analyzed'):
                            continue

                    visited_in_this_run.add(current_url)
                    progress.update(spider_task, description=f"[magenta]D:{current_depth} | {current_url[:50]}...[/magenta]")
                    
                    try:
                        await asyncio.sleep(delay)
                        result = await extract_markdown_from_url(current_url, crawler, run_config)
                        if result.get("success"):
                            content = result.get("markdown", "")
                            filepath = save_markdown_to_raw(current_url, content, session_id)
                            if filepath:
                                all_new_crawled_urls.append(current_url)
                                pages_downloaded_for_domain += 1
                                progress.advance(spider_task)
                                if current_depth < max_depth:
                                    html_content = result.get("html", "")
                                    if html_content:
                                        new_links = extract_internal_links(html_content, current_url, domain)
                                        if mode == "archivist":
                                            add_pending_urls(session_id, new_links, current_depth + 1)
                                        for link in new_links:
                                            if link not in visited_in_this_run:
                                                queue.append((link, current_depth + 1))
                        else:
                            error_msg = result.get("error", "Unknown error")
                            progress.console.print(f"[red]✗ Failed:[/red] {current_url} - {error_msg}")
                    except Exception as e:
                        progress.console.print(f"[red]Errore spider su {current_url}: {e}[/red]")
            
            console.print(f"[green]Spider completato per {domain}. Pagine scaricate: {pages_downloaded_for_domain}[/green]")
            if (current_count + pages_downloaded_for_domain) >= max_pages:
                global_is_saturated = True

    final_crawled_urls = state.get("crawled_urls", []) + all_new_crawled_urls
    is_saturated = state.get("is_saturated", False) or global_is_saturated
    if mode == "archivist":
        db_pending = get_pending_crawl_urls(session_id)
        if not db_pending:
            console.print("[bold green]No more URLs to crawl in Archivist mode.[/bold green]")
            is_saturated = True

    return {
        **state,
        "mode": mode,
        "dense_domains": dense_domains,
        "crawled_urls": final_crawled_urls,
        "is_saturated": is_saturated
    }
