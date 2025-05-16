import requests
from urllib.parse import urlparse

#Chiavi API e CSE ID per la selezione della lingua
from config_chiavi import GCS_KEY
CSE_ID_IT = "73a11c72525274179"   # Italia
CSE_ID_ES = "72a6bb8aa097a4427"   # Spagna

def get_domain(url):
    parsed = urlparse(url)
    return parsed.netloc

def google_search(query, lingua="it", num=10):
    """
    Effettua una ricerca su Google Custom Search API usando una lingua specifica.
    """
    if lingua == "it":
        cse_id = CSE_ID_IT
    elif lingua == "es":
        cse_id = CSE_ID_ES
    else:
        raise ValueError("Lingua non supportata. Usa 'it' o 'es'.")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GCS_KEY,
        "cx": cse_id,
        "q": query,
        "num": num
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print("Errore nella richiesta:", response.status_code)
        print(response.text)
        return []

    return response.json().get("items", [])

def ricerca_custom_search(query, lingua="it"):
    """
    Elabora i risultati della ricerca rimuovendo duplicati e sponsorizzati.
    """
    risultati = []
    risultati_raw = google_search(query, lingua=lingua)
    domini_visti = set()

    for item in risultati_raw:
        link = item.get("link")
        titolo = item.get("title")
        snippet = item.get("snippet")
        dominio = get_domain(link)

        if not link or dominio in domini_visti:
            continue

        #Esclusione di annunci sponsorizzati
        if "pagemap" in item and "metatags" in item["pagemap"]:
            metatags = item["pagemap"]["metatags"][0]
            if metatags.get("og:type") == "advertisement":
                continue

        risultati.append({
            "titolo": titolo,
            "link": link,
            "snippet": snippet
        })
        domini_visti.add(dominio)

    return risultati

