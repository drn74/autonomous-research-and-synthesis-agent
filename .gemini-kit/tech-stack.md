# Tech Stack & Project State: ARSA

## Core Technologies
- **Language:** Python 3.10+
- **Orchestration:** LangGraph (StateGraph) for managing research iterations and state.
- **LLM Providers:**
  - **Google Gemini 2.5 Flash:** Used for Planning, Domain Detection, and Final Synthesis.
  - **Ollama (Llama 3.2:3b):** Used locally for technical entity and knowledge extraction (Analyst node).
- **Database:** SQLite (`research.db`) for tracking session data, URLs, entities, and technical chunks.
- **Web Scraping:** Crawl4AI with Playwright integration.
- **Parsing Engines:**
  - HTML: BeautifulSoup4 / Crawl4AI.
  - PDF: PyMuPDF4LLM.
  - YouTube: youtube-transcript-api.
- **CLI Tools:** Rich for console output and logging.

## Project Structure
- `workflow.py`: Defines the LangGraph state machine and routing logic.
- `core/`:
  - `config.py`: Configuration loader for `config.json` and `.env`.
  - `llm.py`: Provider for Gemini models.
  - `resource_handler.py`: Unified interface for processing different source types.
  - `state.py`: TypedDict defining the `AgentState`.
- `nodes/`: Implementation of each node in the graph (Planner, Crawler, Analyst, etc.).
- `database/`: SQL logic and session management.

## Current State of the Art
- **Functional Workflow:** The system can perform a complete research cycle from a topic/goal to a final Dossier.
- **Deep Extraction:** Successfully extracts code snippets, tables, and technical data into the database.
- **Recursive Logic:** The Planner generates new queries based on current knowledge until saturation is reached or max iterations are hit.
- **Universal Handler:** Successfully distinguishes and processes Web, PDF, and YouTube URLs.
- **State Tracking:** The database correctly manages the lifecycle of URLs (discovery -> crawl -> analysis).

## Environment Requirements
- **OS:** Linux (WSL2 supported) or Windows.
- **GPU:** NVIDIA GTX 1650 or better recommended for local Ollama inference.
- **Connectivity:** Internet access for Gemini API and Web Search (Serper.dev).
