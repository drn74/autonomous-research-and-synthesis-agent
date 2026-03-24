# TODO: Implementazione Domain Detection & Site Spider (REVISED)

Questa lista delinea i passaggi per evolvere ARSA in un agente di mining mirato.

---

## 📅 FASE 1: Refactoring dell'Infrastruttura di Base (Preparazione)
- [x] **1.1 Centralizzazione LLM**: Creare `core/llm.py` per esportare un'istanza di Gemini riutilizzabile.
- [x] **1.2 Estrazione Logica Salvataggio**: Spostare il salvataggio Markdown in `database/db_manager.py` come funzione `save_markdown_to_raw`.
- [x] **1.3 Aggiornamento Crawler**: Modificare `nodes/crawler.py` per popolare `state["crawled_urls"]` solo con gli URL dell'iterazione corrente.

---

## 📅 FASE 2: Aggiornamento Stato e Configurazione
- [x] **2.1 Modifica `core/state.py`**: Aggiungere `mode` e `dense_domains`.
- [x] **2.2 Aggiornamento `config.json`**: Inserire sezione `site_spider` con:
    - `max_pages_per_domain` (per limitare i test o permettere run lunghe).
    - `request_delay_seconds` (per evitare ban).
    - `use_sitemap` (true/false).

---

## 📅 FASE 3: Il Nodo Domain Detector
- [x] **3.1 Creazione `nodes/domain_detector.py`**: Prompt Gemini per analisi densità informativa e identificazione entry-points.
- [x] **3.2 Routing Condizionale**: Implementare `route_after_detection` in `workflow.py`.

---

## 📅 FASE 4: Il Nodo Site Spider (Strategia Ibrida)
- [x] **4.1 Implementazione BFS + Sitemap**:
    - Funzione per estrarre URL da Sitemap XML.
    - Coda BFS per navigazione ricorsiva dei tag `<a>` (con limite di profondità).
- [x] **4.2 Elaborazione Multi-Target**: Ciclo sequenziale se vengono rilevati più domini densi.

---

## 📅 FASE 5: Orchestrazione e Integrazione Finale
- [x] **5.1 Assemblaggio Grafo**: Inserire i nuovi nodi e archi in `workflow.py`.
- [x] **5.2 Testing Night-Run**: Validazione su topic ad alta densità informativa.

---

## 📅 FASE 6: Resource Manager Multi-Formato (PDF & YouTube)
- [x] **6.1 Creazione `core/resource_handler.py`**: Modulo centrale per delegare il download in base al Content-Type o all'URL.
- [x] **6.2 Integrazione `pymupdf4llm`**: Aggiungere il parsing intelligente dei documenti PDF in Markdown.
- [x] **6.3 Integrazione `youtube-transcript-api`**: Estrazione automatica dei sottotitoli dai video YouTube.
- [x] **6.4 Refactoring Crawler & Spider**: Aggiornare i nodi di scraping per usare il nuovo gestore universale invece di chiamare direttamente Crawl4AI.

---

## 📅 FASE 7: Deep Synthesis & Knowledge Extraction
*Obiettivo: Risolvere il problema degli output troppo sintetici e della perdita di dettagli tecnici (codice/ricette).*

- [ ] **7.1 Schema Database Avanzato**: Creare una tabella `knowledge_chunks` per salvare pezzi di codice, ricette e snippet estratti dall'Analyst.
- [ ] **7.2 Potenziamento Analyst (Extraction)**: Modificare il prompt di Llama 3.2 per estrarre non solo nomi di entità ma blocchi di contenuto tecnico/pratico rilevanti per il Goal.
- [ ] **7.3 Synthesizer Iterativo (Chapter-by-Chapter)**: Riscrivere il nodo Synthesizer affinché esegua una chiamata a Gemini per ogni capitolo dell'outline, garantendo massima prolissità e dettaglio.
- [ ] **7.4 Parametro `detail_level`**: Aggiungere il controllo nel `config.json` per regolare la profondità della sintesi.
