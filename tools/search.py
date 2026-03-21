import os
import json
import aiohttp
from typing import List
from core.config import console

async def web_search(queries: List[str]) -> List[str]:
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        console.print("[bold red]ERROR: SERPER_API_KEY not found in .env file[/bold red]")
        return []
    
    urls = []
    async with aiohttp.ClientSession() as session:
        for query in queries:
            try:
                payload = json.dumps({"q": query, "num": 3})
                headers = {
                    'X-API-KEY': serper_api_key,
                    'Content-Type': 'application/json'
                }
                async with session.post("https://google.serper.dev/search", headers=headers, data=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        organic_results = data.get("organic", [])
                        for result in organic_results:
                            link = result.get("link")
                            if link:
                                urls.append(link)
                    else:
                        console.print(f"[red]Serper API Error: {response.status}[/red]")
            except Exception as e:
                console.print(f"[red]Error during search for '{query}': {e}[/red]")
    
    return list(set(urls))
