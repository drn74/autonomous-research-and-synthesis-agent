# Guidelines Context: ARSA Development Standards

## Code Style & Formatting
- **Language Standards:** Python 3.10+ following **PEP 8**.
- **Typing:** Use explicit **Type Hints** (`typing` module) for all function arguments and return types.
- **Documentation:** Every function and class MUST have a **Docstring** explaining its purpose, parameters, and return values.
- **Asynchronicity:** Use `asyncio` for all I/O bound operations (Web Scraping, API calls, File I/O) to maintain non-blocking execution in the LangGraph workflow.
- **Logging:** Use the `Rich` library for console output to maintain a high-signal, visually organized CLI experience.

## Error Handling & Reliability
- **Robustness:** Wrap I/O and LLM calls in `try-except` blocks. Log errors with detailed context but without exposing sensitive data.
- **Validation:** Use **Pydantic** models (like `PlannerOutput` in `state.py`) to validate structured outputs from LLMs.
- **State Integrity:** Ensure the `AgentState` is correctly updated in each node of the LangGraph to prevent state corruption or infinite loops.

## Development Workflow
- **Roadmap Management:** The `todo.md` file in the root directory is the **Single Source of Truth**. Update it before starting a task and mark tasks as complete `[x]` upon finishing.
- **GPU Verification:** Before running or testing the `Analyst` node, verify GPU accessibility via `nvidia-smi` (especially on WSL2) to ensure local Ollama inference functions correctly.
- **Database Safety:** Always verify and/or migrate the SQLite schema (`research.db`) when adding new data fields to `db_manager.py`.

## Version Control & Commits
- **Conventional Commits:** Use clear, prefixed commit messages:
  - `feat:` for new features.
  - `fix:` for bug fixes.
  - `docs:` for documentation updates.
  - `refactor:` for code restructuring without changing behavior.
  - `test:` for adding or updating tests.
- **Secrets Management:** NEVER commit `.env` files, API keys, or sensitive credentials. Ensure they are listed in `.gitignore`.

## Architectural Principles
- **Modularity:** Keep nodes in `nodes/` decoupled. They should only communicate through the `AgentState`.
- **Universal Handling:** New resource types should be integrated into `core/resource_handler.py` to maintain a unified ingestion interface.
- **RAG-Ready Output:** Prioritize "Knowledge Chunks" that preserve technical integrity (code, tables, lists) over summarized text.
