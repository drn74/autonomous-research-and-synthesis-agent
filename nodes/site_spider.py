import asyncio
import urllib.parse
from bs4 import BeautifulSoup
from core.state import AgentState
from core.config import console, APP_CONFIG
from database.db_manager import is_url_crawled, save_markdown_to_raw
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import aiohttp
import xml.etree.ElementTree as ET

def get_domain_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc

async def fetch_sitemap_urls(domain: str) -> list[str]:
    """Tenta di estrarre gli URL dal sitemap.xml del dominio."""
    sitemap_url = f"https://{domain}/sitemap.xml"
    urls = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(sitemap_url, timeout=10) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    root = ET.fromstring(xml_content)
                    # Namespace XML per sitemap
                    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                    for url_elem in root.findall('ns:url/ns:loc', namespace):
                        if url_elem.text:
                            urls.append(url_elem.text)
                    console.print(f"[dim]Trovati {len(urls)} URL dal sitemap.xml di {domain}[/dim]")
    except Exception:
        console.print(f"[dim]Sitemap non trovato o non valido per {domain}[/dim]")
    return urls

def extract_internal_links(html: str, base_url: str, domain: str) -> list[str]:
    """Estrae i link interni (stesso dominio) da una stringa HTML."""
    links = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Risolvi URL relativi
            full_url = urllib.parse.urljoin(base_url, href)
            # Normalizza rimuovendo frammenti
            full_url, _ = urllib.parse.urldefrag(full_url)
            
            # Controlla se è un link interno e http(s)
            if full_url.startswith('http') and get_domain_from_url(full_url) == domain:
                links.append(full_url)
    except Exception:
        pass
    return list(set(links))

async def site_spider_node(state: AgentState) -> AgentState:
    dense_domains = state.get("dense_domains", [])
    
    if not dense_domains:
        console.print("[yellow]Site Spider attivato, ma nessun dominio target fornito. Ritorno alla normalità.[/yellow]")
        return {**state, "mode": "normal"}

    spider_config = APP_CONFIG.get("site_spider", {})
    max_pages = spider_config.get("max_pages_per_domain", 20)
    max_depth = spider_config.get("max_depth", 3)
    delay = spider_config.get("request_delay_seconds", 1.5)
    use_sitemap = spider_config.get("use_sitemap", True)

    session_mock = "sess_001"
    all_new_crawled_urls = []

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    console.print(f"\n[magenta]>>> SITE SPIDER NODE: Inizio scansione profonda su {len(dense_domains)} domini...[/magenta]")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for target in dense_domains:
            domain = target.get("domain")
            entry_points = target.get("entry_points", [])
            
            if not domain:
                continue

            console.print(f"\n[bold yellow]Target:[/bold yellow] {domain}")
            
            # Coda BFS: tuple di (URL, Profondità)
            queue = [(url, 0) for url in entry_points]
            
            if use_sitemap:
                sitemap_urls = await fetch_sitemap_urls(domain)
                # Aggiungiamo i link del sitemap alla coda a profondità 1 (così hanno priorità ma non scavalcano l'entry point)
                queue.extend([(url, 1) for url in sitemap_urls if url not in entry_points])
            
            # Fallback se non ci sono entry_points
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
                # Usiamo max_pages come total, anche se la coda potrebbe finire prima
                spider_task = progress.add_task(f"[magenta]Spidering {domain}...", total=max_pages)
                
                while queue and pages_downloaded_for_domain < max_pages:
                    current_url, current_depth = queue.pop(0)
                    
                    if current_url in visited_in_this_run or is_url_crawled(current_url):
                        continue
                        
                    visited_in_this_run.add(current_url)

                    progress.update(spider_task, description=f"[magenta]D:{current_depth} | {current_url[:50]}...[/magenta]")
                    
                    try:
                        # Rispetto del Rate Limit
                        await asyncio.sleep(delay)
                        
                        result = await crawler.arun(url=current_url, config=run_config)
                        
                        if result.success:
                            # Salvataggio
                            content = result.markdown if hasattr(result, 'markdown') else str(result.html)
                            filepath = save_markdown_to_raw(current_url, content, session_mock)
                            
                            if filepath:
                                all_new_crawled_urls.append(current_url)
                                pages_downloaded_for_domain += 1
                                progress.advance(spider_task)
                                
                                # Estrazione nuovi link per la BFS
                                if current_depth < max_depth:
                                    html_content = str(result.html) if hasattr(result, 'html') else ""
                                    if html_content:
                                        new_links = extract_internal_links(html_content, current_url, domain)
                                        for link in new_links:
                                            if link not in visited_in_this_run:
                                                queue.append((link, current_depth + 1))
                                                
                    except Exception as e:
                        progress.console.print(f"[red]Errore spider su {current_url}: {e}[/red]")
            
            console.print(f"[green]Spider completato per {domain}. Pagine scaricate: {pages_downloaded_for_domain}[/green]")

    # Uniamo gli URL appena scaricati con quelli già presenti nello stato (scaricati dal nodo crawler base)
    final_crawled_urls = state.get("crawled_urls", []) + all_new_crawled_urls

    # Impostiamo il mode su "normal" in modo che il routing successivo funzioni (va all'analyst)
    return {
        **state,
        "mode": "normal",
        "dense_domains": [], # Puliamo per le prossime iterazioni
        "crawled_urls": final_crawled_urls
    }
