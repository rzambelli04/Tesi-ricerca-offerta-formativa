import requests
from urllib.parse import urlparse

from config_chiavi import SERPAPI_KEY

def serpapi_search(query, lingua="it", num_results=10):
    """
    Ricerca con SerpApi, lingua e regione automatizzate:
    - 'it' → Italia
    - 'es' → Spagna
    """

    if lingua == "it":
        gl = "it"
        hl = "it"
    elif lingua == "es":
        gl = "es"
        hl = "es"
    else:
        raise ValueError("Lingua non supportata. Usa 'it' o 'es'.")

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "gl": gl,
        "hl": hl,
        "num": num_results
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print("Errore nella richiesta:", response.status_code)
        print(response.text)
        return []

    data = response.json()
    results = data.get("organic_results", [])

    risultati = []
    domini_visti = set()

    for result in results:
        link = result.get("link")
        titolo = result.get("title")
        snippet = result.get("snippet", "")

        if not link:
            continue

        dominio = urlparse(link).netloc

        if dominio in domini_visti:
            continue

        risultati.append({
            "titolo": titolo,
            "link": link,
            "snippet": snippet
        })

        domini_visti.add(dominio)

        if len(risultati) >= num_results:
            break

    return risultati