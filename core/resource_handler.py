import os
import aiohttp
import aiofiles
import tempfile
import pymupdf4llm
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from core.config import console

async def is_pdf(url: str) -> bool:
    """Rileva se l'URL punta a un file PDF."""
    # Controllo rapido sull'estensione
    parsed_url = urlparse(url.lower())
    if parsed_url.path.endswith('.pdf'):
        return True
    
    # Fallback con HTTP HEAD per URL senza estensione esplicita
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=5) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/pdf' in content_type:
                    return True
    except Exception:
        pass
    
    return False

async def process_pdf(url: str) -> dict:
    """Scarica un PDF e lo converte in Markdown usando pymupdf4llm."""
    console.print(f"[dim]ResourceHandler: Rilevato PDF, inizio download asincrono...[/dim]")
    temp_path = ""
    try:
        # Crea un file temporaneo
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd) 
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    async with aiofiles.open(temp_path, mode='wb') as f:
                        await f.write(await response.read())
                else:
                    return {"success": False, "error": f"HTTP {response.status}"}
        
        # Converte in Markdown
        console.print(f"[dim]ResourceHandler: Estrazione testo dal PDF...[/dim]")
        # run in executor since pymupdf4llm is blocking
        import asyncio
        loop = asyncio.get_running_loop()
        md_text = await loop.run_in_executor(None, pymupdf4llm.to_markdown, temp_path)
        
        return {"success": True, "markdown": md_text}
        
    except Exception as e:
        return {"success": False, "error": f"Errore parsing PDF: {str(e)}"}
    finally:
        # Pulizia del file temporaneo
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

async def process_html(url: str, crawler: AsyncWebCrawler, run_config: CrawlerRunConfig) -> dict:
    """Usa Crawl4AI per estrarre Markdown dall'HTML."""
    try:
        result = await crawler.arun(url=url, config=run_config)
        if result.success:
            content = result.markdown if hasattr(result, 'markdown') else str(result.html)
            raw_html = str(result.html) if hasattr(result, 'html') else ""
            return {"success": True, "markdown": content, "html": raw_html}
        else:
            return {"success": False, "error": result.error_message}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def extract_markdown_from_url(url: str, crawler: AsyncWebCrawler, run_config: CrawlerRunConfig) -> dict:
    """Gestore universale: determina il tipo di risorsa e ne estrae il Markdown."""
    if await is_pdf(url):
        return await process_pdf(url)
    
    # Default ad HTML (Crawl4AI)
    return await process_html(url, crawler, run_config)
