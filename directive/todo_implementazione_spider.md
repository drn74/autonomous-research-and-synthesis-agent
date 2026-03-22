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
- [ ] **4.1 Implementazione BFS + Sitemap**:
    - Funzione per estrarre URL da Sitemap XML.
    - Coda BFS per navigazione ricorsiva dei tag `<a>` (con limite di profondità).
- [ ] **4.2 Elaborazione Multi-Target**: Ciclo sequenziale se vengono rilevati più domini densi.

---

## 📅 FASE 5: Orchestrazione e Integrazione Finale
- [ ] **5.1 Assemblaggio Grafo**: Inserire i nuovi nodi e archi in `workflow.py`.
- [ ] **5.2 Testing Night-Run**: Validazione su topic ad alta densità informativa.
