import json
from core.state import AgentState
from core.llm import get_gemini_model
from rich.panel import Panel
from core.config import console

DETECTION_PROMPT = """
You are an expert in information retrieval. Analyze these URLs found during 
the research on the topic: "{topic}"

URLs found by the Crawler:
{urls}

For each unique domain in the list, evaluate:
1. How many distinct URLs come from the same domain?
2. Does the domain appear to be a wiki, knowledge base, specialized technical forum, 
   documentation repository, or other dedicated source?
3. Based on the topic, estimate how likely this domain is to contain 
   much more relevant information beyond what has already been found (density 0.0-1.0)

Respond ONLY with a valid JSON object, without markdown blocks or backticks:
{{
  "dense_domains": [
    {{
      "domain": "example.net",
      "url_count": 8,
      "type": "wiki|forum|docs|repository|blog|other",
      "density_score": 0.92,
      "reasoning": "Brief explanation of why this site is dense",
      "entry_points": ["https://example.net/start", "https://example.net/index"]
    }}
  ],
  "should_deep_crawl": true,
  "reason": "Explanation of the overall decision"
}}

If no domain deserves a deep crawl, return:
{{
  "dense_domains": [],
  "should_deep_crawl": false,
  "reason": "Explanation"
}}

Recommended threshold: activate deep crawl if density_score >= 0.75 and url_count >= 1.
"""

async def domain_detector_node(state: AgentState) -> AgentState:
    console.print("\n[blue]>>> DOMAIN DETECTOR NODE: Analyzing crawled URLs for dense sources...[/blue]")
    
    crawled_urls = state.get("crawled_urls", [])
    
    if not crawled_urls:
        console.print("[dim]No URLs to analyze. Proceeding in normal mode.[/dim]")
        return {**state, "mode": "normal", "dense_domains": []}

    prompt = DETECTION_PROMPT.format(
        topic=state.get("topic", ""),
        urls="\n".join(crawled_urls)
    )

    llm = get_gemini_model(purpose="domain_detector", temperature=0.1)
    
    console.print("[dim]Invoking Gemini to detect dense domains...[/dim]")
    
    try:
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()
        
        # Clean up potential markdown formatting from the response
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        result = json.loads(response_text)

        if result.get("should_deep_crawl") and result.get("dense_domains"):
            domains_str = ", ".join([d["domain"] for d in result["dense_domains"]])
            console.print(Panel(
                f"[bold green]Dense Domains Detected![/bold green]\n\n"
                f"[yellow]Targets:[/yellow] {domains_str}\n"
                f"[cyan]Reason:[/cyan] {result['reason']}",
                title="Domain Detector Result", border_style="blue"
            ))
            return {
                **state, 
                "mode": "deep_crawl", 
                "dense_domains": result["dense_domains"]
            }
        else:
            console.print(f"[dim]No dense sites detected. {result.get('reason', '')}[/dim]")
            return {**state, "mode": "normal", "dense_domains": []}

    except Exception as e:
        console.print(f"[bold red]Domain Detector Error:[/bold red] {e}. Proceeding in normal mode.")
        return {**state, "mode": "normal", "dense_domains": []}
