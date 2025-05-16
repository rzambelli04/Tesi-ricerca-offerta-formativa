from flask import Flask, request, render_template
import os
import sys
import json
import time
import importlib.util
from openai import OpenAI
from pymongo import MongoClient

from llama_index.core import Settings
from llama_index.core import SimpleDirectoryReader
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import VectorStoreIndex

from Scraping_web.scraper_Google_Diretto import ricerca_google
from Scraping_web.scraper_GCS_API import ricerca_custom_search
from Scraping_web.scraper_SerpAPI import serpapi_search

#Configurazione chiavi
from config_chiavi import OPENAI_KEY, MONGO_URI
os.environ["OPENAI_API_KEY"] = OPENAI_KEY
client = OpenAI(api_key=OPENAI_KEY)

#Connessione a MongoDB Atlas
client_mongo = MongoClient(MONGO_URI)

db = client_mongo["Tesi"]
collezione = db["risultati"]

#Percorsi
BASE_PATH = os.path.dirname(__file__)
SCRAPER_PATH = os.path.join(BASE_PATH, "Scraping_web")
os.makedirs(SCRAPER_PATH, exist_ok=True)
FILE_RISULTATI = os.path.join(SCRAPER_PATH, "ultimi_risultati.json")
HTML_PATH = os.path.join(SCRAPER_PATH, "pagina.html")
TXT_PATH = os.path.join(SCRAPER_PATH, "pagina.txt")
SCRAPER_TEMP = os.path.join(SCRAPER_PATH, "scraper_temp.py")

#Prompt GPT
PROMPT_SCRAPER_TEMPLATE = """Scrivi un file Python (.py) completo che funzioni da scraper per ottenere il codice HTML della seguente pagina web:

URL: {url}
Titolo: {titolo}

Requisiti:
- Usa Playwright in modalità sincrona (playwright.sync_api).
- Avvia il browser in modalità headless.
- Imposta un user-agent personalizzato.
- Dopo aver aperto la pagina, se è presente un popup per la gestione dei cookie, cerca un bottone che contenga il testo "Accetta" oppure "Accetta tutti" e clicca sul primo visibile. Usa un blocco try/except per gestire la sua eventuale assenza.
- Solo dopo la gestione dei cookie, attendi che un elemento significativo del contenuto principale venga caricato (usa page.wait_for_selector("main, #main-content, article, section, .content")).
- Dopo il caricamento, esegui uno scroll fino in fondo alla pagina con page.evaluate("window.scrollTo(0, document.body.scrollHeight)").
- Aggiungi un time.sleep(6) per assicurarti che tutto il contenuto dinamico venga visualizzato.
- va il contenuto HTML della pagina in un file chiamato 'pagina.html' nella cartella 'Scraping_web'.
- Il codice deve essere contenuto in una funzione chiamata esegui_scraper().
- NON includere spiegazioni, commenti o testo extra: fornisci **solo codice eseguibile**.
"""

PROMPT_ANALISI_IT = """Analizza il contenuto HTML (in formato .txt) di una pagina universitaria.

Il tuo compito è ricavare una **descrizione generale** del corso di laurea, ovvero qualunque testo che spieghi:

- Che cos’è il corso
- A chi è rivolto
- Quali competenze fornisce
- Quali sbocchi offre (lavorativi o accademici)

Ignora dettagli tecnici come piani di studio, elenchi di esami, crediti, orari o tabelle. Evita anche intestazioni, menu, footer o testi duplicati.

Se il contenuto rilevante è frammentato o disorganizzato, prova comunque a **ricostruire un paragrafo breve ma coerente**. Se trovi solo parti sparse, **uniscile tu** per ottenere almeno un paragrafo sensato.

Se proprio non riesci a trovare nessun contenuto utile (nemmeno singole frasi), scrivi esattamente:
**"Contenuto non disponibile nella pagina analizzata."**

**Scrivi nella lingua del testo originale.**  
Lunghezza ideale: da 4 a 10 righe.
"**

"""

PROMPT_ANALISI_ES = """Analiza el contenido HTML (en formato .txt) de una página web universitaria.

Intenta identificar una **descripción general** del grado universitario, es decir, cualquier texto que explique:

- Qué es el grado
- A quién está dirigido
- Qué competencias proporciona
- Qué salidas ofrece (profesionales o académicas)

No te centres en detalles técnicos como planes de estudio, listas de asignaturas, créditos, horarios o tablas. Ignora también encabezados, pies de página, accesos y contenido duplicado o decorativo.

Si el contenido relevante es parcial o está desordenado, intenta igualmente **reconstruir un párrafo fluido y coherente**, como si lo escribieras para una guía de orientación universitaria.

**Escribe en el idioma original del texto.**  
Extensión: entre 5 y 15 líneas.  
Si no encuentras nada útil, escribe exactamente:  
**"Contenido no disponible en la página analizada."**

"""

#Funzioni
def richiesta_gpt(prompt, max_tokens=1500):
    print("[GPT] Invio richiesta...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=max_tokens
    )
    print("[GPT] Risposta ricevuta.")
    return response.choices[0].message.content

def esegui_scraper_da_file(path):
    print("[SCRAPER] Esecuzione scraper generato...")
    spec = importlib.util.spec_from_file_location("scraper_temp", path)
    scraper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scraper)
    scraper.esegui_scraper()
    print("[SCRAPER] Completato.")

def converti_html_in_txt():
    print("[CONVERSIONE] Converto HTML in TXT...")
    with open(HTML_PATH, "r", encoding="utf-8") as f_in, open(TXT_PATH, "w", encoding="utf-8") as f_out:
        f_out.write(f_in.read())
    print("[CONVERSIONE] Completata.")

def ottieni_risultati(query, lingua, metodo):
    if os.path.exists(FILE_RISULTATI):
        os.remove(FILE_RISULTATI)
    print(f"[RICERCA] Metodo: {metodo}")
    if metodo == "custom":
        return ricerca_custom_search(query, lingua)
    elif metodo == "direct":
        return ricerca_google(query, lingua)
    elif metodo == "serpapi":
        return serpapi_search(query, lingua)
    else:
        raise ValueError("Metodo scraping non valido")
    
def salva_su_db(corso, citta, descrizioni):
    chiave = {"corso": corso.lower(), "citta": citta.lower()}
    nuovo_documento = {
        "corso": corso.lower(),
        "citta": citta.lower(),
        "risultati": descrizioni,
        "numero_risultati": len(descrizioni),
        "timestamp": time.time()
    }
    print(f"[DB] Salvataggio/aggiornamento: {corso.lower()} - {citta.lower()} con {len(descrizioni)} risultati.")
    collezione.replace_one(chiave, nuovo_documento, upsert=True)
    print("[DB] Dati salvati nel database.")

def recupera_da_db(corso, citta, numero_richiesto):
    print(f"[DB] Controllo presenza dati per: {corso.lower()} - {citta.lower()}")
    documento = collezione.find_one({
        "corso": corso.lower(),
        "citta": citta.lower()
    })

    if documento:
        risultati = documento.get("risultati", [])
        print(f"[DB] Documento trovato con {len(risultati)} risultati.")

        if any("Contenuto non disponibile" in r["descrizione"] for r in risultati):
            print("[DB] Caso 1: Descrizioni non valide trovate.")
            return None

        if len(risultati) < numero_richiesto:
            print(f"[DB] Caso 2: Richiesti {numero_richiesto}, ma disponibili solo {len(risultati)}.")
            return None

        print("[DB] Caso 3: Dati sufficienti e validi. Uso dati esistenti.")
        return risultati[:numero_richiesto]

    print("[DB] Caso 4: Nessun documento trovato. Procedo con scraping.")
    return None


#Flask app
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/esegui", methods=["POST"])
def esegui_pipeline():
    corso = request.form.get("corso").strip()
    citta = request.form.get("citta").strip()
    lingua = request.form.get("lingua")
    metodo = request.form.get("metodo")
    numero = int(request.form.get("numero"))
    query = f"corso di laurea {corso} {citta}"

    print(f"\nAvvio pipeline con QUERY='{query}', LINGUA={lingua}, METODO={metodo}, N={numero}")

    #Tenta di recuperare i risultati dal database
    print("[LOG] Verifico se esistono già risultati validi nel database...")
    risultati_salvati = recupera_da_db(corso, citta, numero)
    if risultati_salvati:
        print("[LOG] Uso dei risultati esistenti da MongoDB.")
        return render_template("index.html", risultati=risultati_salvati)

    print("[LOG] Nessun risultato valido nel database. Avvio scraping.")


    #Se non sono validi o non sufficienti, procede con la nuova elaborazione
    risultati = ottieni_risultati(query, lingua, metodo)[:numero]

    
    descrizioni = []

    with open(FILE_RISULTATI, "w", encoding="utf-8") as f_out:
        json.dump([], f_out)

    for i, item in enumerate(risultati):
        for file_path in [SCRAPER_TEMP, HTML_PATH, TXT_PATH]:
            if os.path.exists(file_path):
                os.remove(file_path)

        titolo = item.get("titolo")
        url = item.get("link")
        print(f"\n[{i+1}] Titolo: {titolo}")
        print(f"URL: {url}")

        try:
            codice_scraper = richiesta_gpt(PROMPT_SCRAPER_TEMPLATE.format(titolo=titolo, url=url)).strip()
            if codice_scraper.startswith("```python"):
                codice_scraper = codice_scraper.replace("```python", "", 1)
            if codice_scraper.startswith("```"):
                codice_scraper = codice_scraper.replace("```", "", 1)
            if codice_scraper.endswith("```"):
                codice_scraper = codice_scraper[:-3]

            with open(SCRAPER_TEMP, "w", encoding="utf-8") as f:
                f.write(codice_scraper)

            esegui_scraper_da_file(SCRAPER_TEMP)
            time.sleep(4)

            if not os.path.exists(HTML_PATH) or os.stat(HTML_PATH).st_size < 500:
                raise Exception("pagina.html non generato correttamente o troppo vuoto")

            converti_html_in_txt()

            documents = SimpleDirectoryReader(input_files=[TXT_PATH]).load_data()

            Settings.llm = LlamaOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=800)
            Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small", api_key=OPENAI_KEY)

            index = VectorStoreIndex.from_documents(documents)
            prompt_analisi = PROMPT_ANALISI_ES if lingua == "es" else PROMPT_ANALISI_IT
            descrizione = index.as_query_engine().query(prompt_analisi).response.strip()

            print(f"Descrizione ottenuta:\n{descrizione}\n")

            result = {"titolo": titolo, "link": url, "descrizione": descrizione}
            descrizioni.append(result)

            with open(FILE_RISULTATI, "r+", encoding="utf-8") as f:
                dati = json.load(f)
                dati.append(result)
                f.seek(0)
                json.dump(dati, f, indent=2, ensure_ascii=False)
                f.truncate()

        except Exception as e:
            print(f"Errore risultato {i+1}: {e}")
            continue

        for file_path in [SCRAPER_TEMP, HTML_PATH, TXT_PATH]:
            if os.path.exists(file_path):
                os.remove(file_path)

    print("\nPipeline completata. Risultati totali:", len(descrizioni))
    salva_su_db(corso, citta, descrizioni)
    return render_template("index.html", risultati=descrizioni)


if __name__ == "__main__":
    app.run()