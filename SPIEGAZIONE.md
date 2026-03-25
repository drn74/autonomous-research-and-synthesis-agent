# 🧠 ARSA: Come Funziona l'Agente Ricercatore

**ARSA** (Autonomous Research & Synthesis Agent) non è un semplice script che scarica pagine web. È un **team di specialisti virtuali** che lavorano insieme in modo ciclico per sviscerare un argomento, scartare il rumore e distillare solo la conoscenza purissima.

Immagina di aver dato a una squadra di veri ricercatori il compito di studiare un argomento complesso. Ecco come si dividerebbero il lavoro, che corrisponde esattamente ai "Nodi" dell'architettura di ARSA:

---

## 🏗️ L'Architettura in 6 Passaggi

Il sistema è governato da **LangGraph**, un "direttore d'orchestra" che fa passare la palla da un agente all'altro. Il processo è diviso in due grandi fasi: la **Raccolta** e la **Stesura**.

### FASE 1: La Raccolta (`run_researcher.py`)
Questa fase è un "loop". L'agente continua a girare in tondo, trovando sempre più informazioni, finché non ritiene di aver raggiunto una *Saturazione* sufficiente dell'argomento.

#### 1. 🧠 Il Planner (Il Capo Progetto)
*   **Chi è:** L'intelligenza cloud (Gemini 2.5 Flash).
*   **Cosa fa:** Legge il tuo obiettivo iniziale (il *Goal*). Controlla cosa sa già (se ha già fatto dei giri precedenti). Poi, genera da 3 a 5 **query di ricerca intelligentissime** da cercare su Google per coprire i "buchi" di conoscenza.

#### 2. 🕷️ Il Crawler (Il Cercatore)
*   **Chi è:** Un automa velocissimo (Crawl4AI + Serper API).
*   **Cosa fa:** Prende le query del Planner, va su Google e apre i siti web in modalità invisibile (per non farsi bloccare). 
*   **Il suo superpotere (Universal Resource Handler):** Che trovi una normale pagina web, un **PDF** o un video di **YouTube**, il Crawler sa come estrarre il testo e convertirlo in un documento pulito e formattato.

#### 3. 🚦 Il Domain Detector (Il Vigile Urbano)
*   **Chi è:** Di nuovo Gemini.
*   **Cosa fa:** Osserva l'elenco dei siti trovati dal Crawler e si fa una domanda: *"Aspetta, questo dominio è un sito generico o è un'enorme Wiki/Forum specializzato sul nostro argomento?"*. Se trova un "filone d'oro" (un sito molto denso), dirotta il flusso verso lo Spider.

#### 4. 🕸️ Il Site Spider (Lo Scavatore Profondo)
*   **Cosa fa:** Si attiva solo se autorizzato dal Detector. Entra nel sito "denso", legge la sua mappa (Sitemap) e inizia a cliccare su tutti i link interni utili, scaricando dozzine di pagine collegate. Invece di fermarsi alla superficie di Google, scava in profondità negli archivi.

#### 5. 🔬 L'Analyst (Il Minatore Locale)
*   **Chi è:** La tua scheda video (Llama 3.2 in esecuzione locale tramite Ollama).
*   **Cosa fa:** Prende le decine di documenti grezzi scaricati e li "spreme". Scarta tutto il blabla inutile, i menu di navigazione e i disclaimer, ed **estrae solo i blocchi di conoscenza purissima**: pezzi di codice, ricette, tabelle e nomi tecnici (le *Entità*).
*   **Sicurezza:** Salvando tutto nel tuo database locale SQLite (`research.db`), costruisce una memoria persistente a costo zero.
*   *Finito il suo lavoro, l'Analyst dice al direttore d'orchestra: "Siamo sazi?" Se sì, il ciclo si ferma.*

---

### FASE 2: La Stesura (`run_synthesizer.py`)
Una volta che il database è colmo di dati, interviene l'ultimo specialista. Puoi lanciare questa fase quando vuoi, anche il giorno dopo.

#### 6. ✍️ Il Synthesizer (L'Archivista Capo)
*   **Chi è:** Gemini 2.5 Flash.
*   **Cosa fa:** Apre il tuo database SQLite. Prende tutte le centinaia di "pepite d'oro" trovate dall'Analyst (snippet di codice, concetti) e le impagina in un gigantesco **Knowledge Dossier** in formato Markdown. 
*   **Risultato:** Non un riassuntino banale, ma un vero e proprio manuale enciclopedico, completo di fonti reali e pronto per essere studiato da te o indicizzato da altri sistemi di Intelligenza Artificiale.
