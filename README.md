# ARSA: Autonomous Research & Synthesis Agent

ARSA is an open-source, multi-agent AI system designed to autonomously plan, execute, and synthesize deep research on any given topic. By combining the reasoning capabilities of **Cloud LLMs (Gemini 2.0 Flash)** with the cost-efficiency of **Local LLMs (Ollama/Llama 3.2)**, ARSA can surf the web, read dozens of technical articles, extract entities, and produce a comprehensive, "RAG-ready" final Markdown guide.

Built natively for **Linux / WSL2** and orchestrated via **LangGraph**.

## 🧠 Architecture Overview

The system operates on a recursive State Graph composed of 4 main nodes:

1. **[Planner] (Gemini 2.0 Flash):** Analyzes the Goal, evaluates the current knowledge base, and generates precise search queries to fill knowledge gaps.
2. **[Crawler] (Crawl4AI + Serper API):** Asynchronously searches the web, downloads the top results, bypasses anti-bot protections, and converts raw HTML into clean Markdown.
3. **[Analyst] (Local Ollama - Llama 3.2:3b):** Reads the downloaded Markdown files, extracts key technical entities, and updates the SQLite knowledge graph. Calculates the "Saturation Score".
4. **[Synthesizer] (Gemini 2.0 Flash):** Once saturation is reached (or the loop limit is hit), it aggregates all the gathered knowledge and writes a definitive, highly structured Markdown report.

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
   *Note: If you are running Ollama on a Windows Host while ARSA runs in WSL2, ensure you have set `OLLAMA_ORIGINS="*"` in your Windows environment variables.*

## 🏃‍♂️ Usage

1. **Activate the Virtual Environment:**
   ```bash
   source arsa-env/bin/activate
   ```

2. **Define your Goal:**
   Open `main.py` and modify the `initial_state` variable at the bottom of the file with your desired Topic, Goal, and Language.
   ```python
   initial_state = AgentState(
       topic="Your Topic Here",
       goal="What exactly do you want to learn or build a guide about?",
       language="English", # Set to "Italian", "Spanish", etc. for localized research
       # ...
   )
   ```

3. **Run the Orchestrator:**
   ```bash
   python main.py
   ```

Watch your terminal as ARSA plans, crawls the web with a progress bar, extracts data locally on your GPU, and finally synthesizes the research!

## 📁 Output

The final synthesized report will be saved in the `output/` directory as `FINAL_GUIDE_{topic}.md`, complete with YAML frontmatter detailing the sources analyzed and entities extracted. Raw scraped markdowns are kept in `data/raw/` for transparency or direct RAG indexing.

## 📜 License

[MIT License](LICENSE)
