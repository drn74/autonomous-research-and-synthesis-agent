# ARSA 3.0: High-Performance Autonomous Research & Synthesis Agent

ARSA is an advanced, multi-agent AI system designed to autonomously plan, execute, and synthesize deep technical research. **Version 3.0** introduces a high-performance parallel architecture, recursive document chunking, and a dedicated **RAG (Retrieval-Augmented Generation)** synthesis engine.

By combining **Cloud LLMs (Gemini 2.5 Flash)** for strategic reasoning with **Local LLMs (Ollama/Llama 3.2)** for heavy extraction, ARSA provides professional-grade research dossiers with citations, zero token costs for raw data analysis, and extreme I/O speed.

## 🚀 Key Features in v3.0
- **High-Performance Parallelism:** Concurrent web crawling and multi-chunk analysis (Semaphore controlled).
- **Semantic Memory (Vector DB):** Integration with **ChromaDB** for context-aware research and RAG.
- **Recursive Chunking:** Handles massive PDFs and long transcripts without context window limits.
- **Self-Correction Loop:** A dedicated **Critic Node** (Gemini) that audits local extraction quality.
- **RAG-based Synthesis:** Generates structured dossiers with automatic citations to original sources.

## 🧠 Architecture Overview

ARSA 3.0 operates on a sophisticated State Graph (LangGraph) with active feedback loops:

1. **[Planner] (`nodes/planner.py`):** Strategically evaluates knowledge gaps and plans recursive search queries (Gemini).
2. **[Crawler] (`nodes/crawler.py`):** Parallel downloader using **Crawl4AI**. Asynchronously fetches HTML, PDFs, and YouTube transcripts.
3. **[Domain Detector] (`nodes/domain_detector.py`):** Identifies "dense" technical sources for deep-dive spidering.
4. **[Site Spider] (`nodes/site_spider.py`):** Deeply mines specialized wikis or forums using BFS and parallel Sitemap parsing.
5. **[Analyst] (`nodes/analyst.py`):** Performs local technical extraction using **Ollama (Llama 3.2)**. Now analyzes long documents via **Recursive Chunking**.
6. **[Critic] (`nodes/critic.py`):** **(NEW)** A quality gate that audits extraction results and can trigger a "Retry" if details are insufficient.
7. **[Synthesizer] (`nodes/synthesizer.py`):** A full RAG engine that queries the Vector DB to write professional chapters with source citations.

## ⚙️ Prerequisites

- **OS:** Linux (Ubuntu 22.04/24.04) or Windows (WSL2 recommended).
- **Python:** 3.10 or higher.
- **Ollama:** Installed and running with `llama3.2:3b`.
- **GPU:** NVIDIA GPU (e.g., GTX 1650, 4GB+ VRAM) for local inference.

## 🚀 Quick Start

1. **Clone & Setup:**
   ```bash
   git clone https://github.com/yourusername/ARSA.git
   cd ARSA
   python -m venv .venv
   # Windows
   .venv\Scripts\Activate.ps1
   # Linux/WSL
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure API Keys:**
   Create a `.env` file:
   ```env
   GEMINI_API_KEY="your_key_here"
   SERPER_API_KEY="your_key_here"
   ```

3. **Run General Research:**
   Configure `config.json` or use CLI arguments to explore the web. Use `--synthesize` to automatically generate the dossier at the end:
   ```bash
   python run_researcher.py --topic "Quantum Computing" --goal "Extract implementation details" --synthesize
   ```

4. **Targeted Site Scanning (Deep Dive):**
   Use the specialized scanner to ingest an entire website (e.g., a documentation wiki) skipping the planning phase:
   ```bash
   python run_site_scanner.py --url "https://docs.example.com" --max-pages 100 --synthesize
   ```

5. **Synthesize Dossier:**
   If you didn't use the `--synthesize` flag, run the manual synthesis:
   ```bash
   python run_synthesizer.py
   ```

## 📁 Output: RAG-Ready Dossiers

The final report in `output/` is a professional Markdown document featuring:
- **Executive Summary:** High-level takeaways.
- **Thematic Chapters:** Generated via semantic search in the local Vector DB.
- **In-text Citations:** Every technical fact includes a link to the original source `[https://...]`.
- **Technical Integrity:** Preserves source code, tables, and complex procedures.

## 📜 License
[MIT License](LICENSE)
