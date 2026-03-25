import os
import aiohttp
import aiofiles
import tempfile
import pymupdf4llm
from urllib.parse import urlparse, parse_qs
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from core.config import console
from youtube_transcript_api import YouTubeTranscriptApi

async def is_pdf(url: str) -> bool:
    """Rileva se l'URL punta a un file PDF."""
    parsed_url = urlparse(url.lower())
    if parsed_url.path.endswith('.pdf'):
        return True
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=5) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/pdf' in content_type:
                    return True
    except Exception:
        pass
    
    return False

def is_youtube_url(url: str) -> bool:
    """Rileva se l'URL appartiene a YouTube."""
    parsed_url = urlparse(url.lower())
    return parsed_url.netloc in ['youtube.com', 'www.youtube.com', 'youtu.be']

def get_youtube_video_id(url: str) -> str:
    """Estrae l'ID del video da un URL YouTube."""
    parsed_url = urlparse(url)
    if parsed_url.netloc == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.netloc in ('youtube.com', 'www.youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        if parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        if parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
    return None

async def process_pdf(url: str) -> dict:
    """Scarica un PDF e lo converte in Markdown usando pymupdf4llm."""
    console.print(f"[dim]ResourceHandler: Rilevato PDF, inizio download asincrono...[/dim]")
    temp_path = ""
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd) 
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    async with aiofiles.open(temp_path, mode='wb') as f:
                        await f.write(await response.read())
                else:
                    return {"success": False, "error": f"HTTP {response.status}"}
        
        console.print(f"[dim]ResourceHandler: Estrazione testo dal PDF...[/dim]")
        import asyncio
        loop = asyncio.get_running_loop()
        md_text = await loop.run_in_executor(None, pymupdf4llm.to_markdown, temp_path)
        
        return {"success": True, "markdown": md_text}
        
    except Exception as e:
        return {"success": False, "error": f"Errore parsing PDF: {str(e)}"}
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

async def process_youtube(url: str) -> dict:
    """Estrae i sottotitoli di un video YouTube e li converte in Markdown."""
    console.print(f"[dim]ResourceHandler: Rilevato YouTube URL, estrazione transcript...[/dim]")
    video_id = get_youtube_video_id(url)
    
    if not video_id:
        return {"success": False, "error": "ID Video non trovato nell'URL."}
        
    try:
        # Run blocking transcript fetch in executor
        import asyncio
        loop = asyncio.get_running_loop()
        
        # Prova a prendere il transcript (preferisce l'italiano o l'inglese, o tradotti automaticamente)
        def fetch_transcript():
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)
            try:
                # Prova a prendere italiano o inglese
                transcript = transcript_list.find_transcript(['it', 'en'])
            except:
                # Prendi il primo disponibile e prova a tradurlo in inglese o usalo nativo
                transcript = transcript_list.find_generated_transcript(['it', 'en'])
                if not transcript:
                    for t in transcript_list:
                        transcript = t
                        break
            return transcript.fetch()

        transcript_data = await loop.run_in_executor(None, fetch_transcript)
        
        # Formattazione base del transcript in testo leggibile (supporta dict o oggetti)
        full_text = " ".join([getattr(item, 'text', item.get('text', '')) if isinstance(item, dict) else item.text for item in transcript_data])
        
        md_content = f"# YouTube Video Transcript\n**Video ID:** {video_id}\n\n{full_text}"
        return {"success": True, "markdown": md_content}
        
    except Exception as e:
        return {"success": False, "error": f"Impossibile estrarre transcript (forse non disponibile o video privato): {str(e)}"}

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
    if is_youtube_url(url):
        return await process_youtube(url)
        
    if await is_pdf(url):
        return await process_pdf(url)
    
    # Default ad HTML (Crawl4AI)
    return await process_html(url, crawler, run_config)
