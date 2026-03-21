# ARSA (Autonomous Research & Synthesis Agent) - GEMINI.md

## 1. Project Overview
ARSA is a recursive research system designed to crawl, analyze, and synthesize information into "RAG-ready" Markdown documents. It utilizes a LangGraph-based orchestrator to manage state and iterative refinement through Gap Analysis.

## 2. Tech Stack & Environment
- **OS:** Ubuntu 24.04 on WSL2.
- **Python:** 3.11+.
- **Orchestrator:** LangGraph (Python).
- **State Persistence:** SQLite (WSL2).
- **Inference (Cloud):** Gemini 2.0 Flash API (Planning & Synthesis).
- **Inference (Local):** Ollama/vLLM via NVIDIA GTX 1650 GPU (Modello: llama3.2:3b).
- **Scraping:** Crawl4AI / Firecrawl (Playwright-based).
- **Environment:** Windows 10 Host + WSL2 (Ubuntu 24.04).

## 3. Core Mandates
- **Recursive Logic:** Every search must evaluate "Saturation" and "Gap Analysis" before concluding.
- **Data Integrity:** SQLite must track URLs, Content Hashes (anti-duplication), Entities, and Saturation Scores.
- **Output Format:** Final documents must be `.md` with YAML Frontmatter for RAG compatibility.
- **Efficiency:** Use local LLMs (Ollama) for high-volume, low-complexity tasks (filtering/scoring) to save API costs.

## 4. Architectural Standards (Phase 1)
- **Graph-Based Workflow:** Implement logic using LangGraph nodes (Planner, Crawler, Analyst, Synthesizer).
- **Gap Analysis:** LLM-driven comparison between current findings and the research objective to generate new queries.
- **RAG-Ready Storage:** Structured output directory for ease of indexing.

## 5. Environment Setup (Phase 2 - COMPLETED)
- **Virtual Environment:** `arsa-env` using Python 3.10+ initialized.
- **System Dependencies:** `libmagic1`, `libnss3`, and Playwright/Patchright browsers installed successfully.
- **GPU Integration:** Verified. NVIDIA GeForce GTX 1650 accessible within WSL2 (CUDA 13.2 via `nvidia-smi`).
- **Ollama Connectivity:** Ollama process verified running on GPU. Ensure `OLLAMA_ORIGINS` is configured if cross-platform communication is required.
- **Database:** `research.db` successfully initialized with `schema.sql`.

## 6. Immediate Technical Requirements (Phases 3 & 4 - COMPLETED)
- **Orchestration:** LangGraph integrated with `asyncio` (`StateGraph`, nodes, conditional edges).
- **Planner Node:** Gemini 2.0 Flash implemented with `Pydantic` structured output to generate recursive search plans and evaluate saturation.
- **Crawler Node:** Implemented asynchronous search via Serper API and markdown extraction via `Crawl4AI` (AsyncWebCrawler). Verified with ~40+ downloads in test run.
- **Data Persistence:** Added duplicate URL detection via MD5 hashing in SQLite and raw markdown storage in `data/raw/`.

## 7. Immediate Technical Requirements (Phase 5 - Logic Implementation)
- **Analyst Node:** Analisi dei contenuti tramite **llama3.2:3b** per estrazione entità e calcolo saturazione reale.
- **Synthesizer Node:** Generate the final "RAG-ready" document by combining the accepted markdown chunks and the Planner's outline.
- **Graph Optimization:** Refine the recursion limits and ensure robust error handling between the Analyst and Planner.

## 8. Development Guidelines
- Always verify GPU accessibility in WSL2 (`nvidia-smi`) before starting local inference tasks.
- Ensure `Crawl4AI` is configured for efficient Markdown extraction.
- Maintain strict separation between State (SQLite) and Output (.md files).
- Use `OLLAMA_ORIGINS="*"` (or specific domain) for cross-platform API calls.
