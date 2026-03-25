# ARSA: Autonomous Research & Synthesis Agent

ARSA is an open-source, multi-agent AI system designed to autonomously plan, execute, and synthesize deep research on any given topic. By combining the reasoning capabilities of **Cloud LLMs (Gemini 2.5 Flash)** with the cost-efficiency of **Local LLMs (Ollama/Llama 3.2)**, ARSA can surf the web, read technical articles, parse **PDF documents**, extract **YouTube transcripts**, and produce a comprehensive, "RAG-ready" final Markdown guide.

Built natively for **Linux / WSL2** and orchestrated via **LangGraph**.

## 🧠 Architecture Overview

The system operates on a recursive State Graph composed of 6 main nodes, organized in a modular structure. ARSA features a dynamic routing system and a **Universal Resource Handler** capable of intelligently downloading and converting different media types into Markdown.

1. **[Planner] (`nodes/planner.py`):** Analyzes the Goal, evaluates the current knowledge base, and generates precise search queries to fill knowledge gaps (Powered by Gemini).
2. **[Crawler] (`nodes/crawler.py`):** Asynchronously searches the web via Serper API and downloads the top results. It uses the `ResourceHandler` to automatically convert HTML (via Crawl4AI), PDFs (via PyMuPDF), and YouTube videos (via Transcript API) into clean Markdown.
3. **[Domain Detector] (`nodes/domain_detector.py`):** Semantically analyzes the URLs found by the crawler to identify "dense domains" (e.g., specialized wikis, forums). If detected, it routes the graph to the Site Spider.
4. **[Site Spider] (`nodes/site_spider.py`):** When a dense domain is found, this node activates a recursive Breadth-First Search (BFS) and Sitemap extraction to deeply mine the specific website, extracting dozens of internal pages.
5. **[Analyst] (`nodes/analyst.py`):** Reads the downloaded Markdown files locally on your GPU, extracts key technical entities, and updates the SQLite knowledge graph. Calculates the "Saturation Score" (Powered by Local Ollama Llama 3.2).
6. **[Synthesizer] (`nodes/synthesizer.py`):** Once saturation is reached, it aggregates all the gathered knowledge and writes a definitive, highly structured Markdown report (Powered by Gemini).

## ⚙️ Prerequisites

- **OS:** Ubuntu 22.04/24.04 (Natively or via WSL2 on Windows)
- **Python:** 3.10 or higher
- **GPU (Optional but Highly Recommended):** NVIDIA GPU (e.g., GTX 1650 or better) with CUDA Toolkit installed to run the local Analyst node efficiently.
- **Ollama:** Installed and accessible.

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ARSA.git
   cd ARSA
   ```

2. **Run the Setup Script:**
   We provide an automated bash script that installs all system dependencies (for Playwright/Crawl4AI), creates the Python virtual environment (`arsa-env`), installs requirements, and initializes the `research.db` SQLite database.
   ```bash
   chmod +x setup_arsa.sh
   ./setup_arsa.sh
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your API keys:
   ```env
   GEMINI_API_KEY="your_google_gemini_api_key"
   SERPER_API_KEY="your_serper_dev_api_key"
   ```
   *(You can get a free Serper API key at [serper.dev](https://serper.dev/) and a Gemini key at Google AI Studio).*

4. **Prepare the Local LLM (Ollama):**
   Ensure Ollama is running. Pull the model used by the Analyst Node:
   ```bash
   ollama pull llama3.2:3b
   ```

## 🏃‍♂️ Usage

1. **Activate the Virtual Environment:**
   ```bash
   source arsa-env/bin/activate
   ```

2. **Configure your Research:**
   Open the `config.json` file in the root directory to set your defaults, or simply use **Command Line Arguments** to override them on the fly:
   ```bash
   python run_researcher.py --topic "Black Holes" --goal "Explain the event horizon" --lang "en"
   ```

3. **Run the Extraction Phase (Researcher):**
   This script runs the core agentic loop (Planner, Crawler, Analyst) to populate the local database and `data/raw/` directory. It can take a long time depending on the depth of the search.
   ```bash
   python run_researcher.py
   ```

4. **Run the Synthesis Phase (Synthesizer):**
   Once the extraction is complete, run the synthesizer to aggregate all the raw code, recipes, and entities into a massive Markdown dossier. You can even pass a different goal to the synthesizer without re-running the researcher!
   ```bash
   python run_synthesizer.py --goal "Create a bullet-point summary"
   ```

## 📁 Output

The final synthesized report will be saved in the `output/` directory as `KNOWLEDGE_DOSSIER_{topic}.md`. It contains:
- An **Executive Summary** written by Gemini.
- A **Taxonomy** of all entities discovered.
- The **Raw Knowledge Chunks** (code snippets, tables, detailed explanations) extracted by the local GPU, preserving 100% of the technical details for direct RAG indexing.

## 📜 License

[MIT License](LICENSE)
