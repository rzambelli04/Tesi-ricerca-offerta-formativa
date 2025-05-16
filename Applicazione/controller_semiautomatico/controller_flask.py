from flask import Flask, request, jsonify
import json
import os
import sys
import requests
from threading import Thread
import time
from urllib.parse import quote_plus

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Scraping_web.scraper_Google_Diretto import ricerca_google
from Scraping_web.scraper_GCS_API import ricerca_custom_search
from Scraping_web.scraper_SerpAPI import serpapi_search

# Prompt
def genera_prompt_scraper(risultati):
    for i, item in enumerate(risultati):
        titolo = item["titolo"]
        url = item["link"]
        prompt = f"""Scrivi uno scraper in Python che utilizzi Playwright e playwright-stealth per visitare la seguente pagina:

{url}

Lo scraper deve:
- Navigare verso l'URL indicato.
- Salvare il codice HTML della pagina in un file chiamato `pagina.html`.
- Il file `pagina.html` deve essere salvato **nella stessa cartella in cui si trova questo script Python** (usa `os.path.dirname(__file__)`).
- Utilizzare un user-agent reale e la funzione `stealth_sync()` per evitare blocchi anti-bot.
- Il codice deve essere racchiuso in una funzione chiamata `esegui_scraper()`.
- NON aggiungere commenti, spiegazioni o testo extra.
- L'intera risposta deve essere un file `.py` eseguibile così com'è.

"""
        print(f"\n--- Prompt {i+1} ---")
        print(prompt)


app = Flask(__name__)

# Configurazione della ricerca
QUERY_DI_DEFAULT = "corso di laurea psicologia bari"
LINGUA_DI_DEFAULT = "it"
METODO_DI_DEFAULT = "custom"

risultati_memorizzati = []
PATH_SALVATAGGIO = os.path.join(os.path.dirname(__file__), "..", "Scraping_web", "ultimi_risultati.json")

@app.route("/search", methods=["GET"])
def search():
    global risultati_memorizzati

    query = request.args.get("query")
    lingua = request.args.get("lingua", "it")
    metodo = request.args.get("metodo", "direct")

    if not query:
        return jsonify({"error": "Parametro 'query' richiesto"}), 400

    if lingua not in ["it", "es"]:
        return jsonify({"error": "Lingua non supportata. Usa 'it' o 'es'."}), 400

    try:
        if metodo == "direct":
            risultati = ricerca_google(query, lingua)
        elif metodo == "custom":
            risultati = ricerca_custom_search(query, lingua)
        elif metodo == "serpapi":
            risultati = serpapi_search(query, lingua)
        else:
            return jsonify({"error": "Metodo non valido. Usa 'direct', 'custom' o 'serpapi'."}), 400

        risultati_memorizzati = risultati

        with open(PATH_SALVATAGGIO, "w", encoding="utf-8") as f:
            json.dump(risultati, f, indent=2, ensure_ascii=False)

        # Genera e mostra i prompt
        genera_prompt_scraper(risultati)

        # Attende che venga incollato il codice dello scraper GPT nel file .py
        input("\n[PAUSA] Incolla il codice generato da ChatGPT in 'scraper_GPT_download.py', poi premi INVIO per avviare lo scraping...")

        # Import dinamico del file generato e avvio dello scraper
        try:
            from Scraping_web import scraper_GPT_download
            scraper_GPT_download.esegui_scraper()
            print("Scraper eseguito correttamente.")
        except Exception as e:
            print(f"Errore durante l'esecuzione dello scraper: {e}")
            return jsonify({"error": str(e)}), 500

        # Conversione del file .html in .txt
        try:
            html_path = os.path.join(os.path.dirname(__file__), "..", "Scraping_web", "pagina.html")
            txt_path = html_path.replace(".html", ".txt")

            with open(html_path, "r", encoding="utf-8") as f_in:
                testo = f_in.read()

            with open(txt_path, "w", encoding="utf-8") as f_out:
                f_out.write(testo)

            os.remove(html_path)  #Rimuove il file HTML dopo la conversione

            print(f"File HTML convertito in TXT e originale rimosso: {txt_path}")
        except Exception as e:
            print(f"Errore nella conversione HTML -> TXT: {e}")

        return jsonify(risultati)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/results", methods=["GET"])
def get_saved_results():
    return jsonify(risultati_memorizzati)

def avvio_automatico():
    time.sleep(1)
    try:
        print("[INFO] Eseguo la richiesta automatica iniziale...")
        url_query = quote_plus(QUERY_DI_DEFAULT)
        url = f"http://127.0.0.1:5000/search?query={url_query}&lingua={LINGUA_DI_DEFAULT}&metodo={METODO_DI_DEFAULT}"
        requests.get(url)
    except Exception as e:
        print(f"[ERRORE] Errore nella chiamata automatica: {e}")

if __name__ == "__main__":
    Thread(target=avvio_automatico).start()
    app.run(debug=True, use_reloader=False)

