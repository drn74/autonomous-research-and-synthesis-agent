# Product Context: ARSA (Autonomous Research & Synthesis Agent)

## Description
ARSA è un sistema di ricerca ricorsivo progettato per navigare, analizzare e sintetizzare informazioni in "Knowledge Dossiers" pronti per la RAG.

## Users
Sviluppatori e ricercatori che necessitano di estrarre dati tecnici strutturati da fonti eterogenee (Web, PDF, YouTube) per alimentare sistemi di Intelligenza Artificiale.

## Goals
Automatizzare la raccolta di conoscenze tecniche profonde, preservando codice e tabelle, per creare una base di conoscenza esaustiva senza perdere dettagli tramite eccessive sintesi.

## Main Features
- **Ingestione Universale:** Supporto nativo per pagine Web, PDF e video YouTube.
- **Estrazione Profonda:** Utilizzo di LLM locali (Llama 3.2 via Ollama) per estrarre blocchi tecnici puri preservando codice, ricette e tabelle.
- **Persistenza Strutturata:** Memorizzazione di entità, URL e chunk di conoscenza in un database SQLite.
- **Orchestrazione Avanzata:** Utilizzo di LangGraph per gestire lo stato e la raffinazione iterativa della ricerca.
- **Interfaccia CLI:** Supporto per argomenti da riga di comando per personalizzare topic, goal e lingua.
