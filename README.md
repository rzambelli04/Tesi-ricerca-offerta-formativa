# Ricerca Opportunità Formative Universitarie

Questa è una web app sviluppata con Flask che consente di cercare e analizzare corsi universitari in Italia o Spagna. I risultati vengono ottenuti tramite scraping e analisi automatica del contenuto delle pagine.

## Requisiti

- Python 3.10+
- MongoDB Atlas (o un'istanza locale)
- Chiavi API per OpenAI e servizi di scraping (Google Custom Search e SerpAPI)

Il file `config_chiavi.py` non è presente all'interno del progetto

## Avvio dell'applicazione

1. Configura il file `config_chiavi.py` con le chiavi necessarie, seguendo come modello `config_chiavi_esempio.py`
2. Avvia l'applicazione con il comando
3. Nel browser vai all'indirizzo `http://127.0.0.1:5000`
4. Premi ctrl+C nel terminale per chiudere la connessione con Flask
