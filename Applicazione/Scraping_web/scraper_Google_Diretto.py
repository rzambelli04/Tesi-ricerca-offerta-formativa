from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import time

def ricerca_google(query, lingua='it'):
    risultati = []
    domini_visti = set()

    # Mappa lingua -> regione
    regione_map = {
        'it': 'IT',
        'es': 'ES'
    }

    #Imposta regione in base alla lingua
    regione = regione_map.get(lingua.lower(), 'IT')

    #Costruzione URL
    url = f'https://www.google.com/search?q={query.replace(" ", "+")}&hl={lingua}&gl={regione}'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(
            locale=f"{lingua}_{regione}",
            user_agent=f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
            extra_http_headers={
                "Accept-Language": lingua
            }
        )
        page = context.new_page()
        print(f"[INFO] Visitando: {url}")
        page.goto(url)

        time.sleep(10)

        #Accetta cookie se presenti
        try:
            if page.locator("text=Accetta tutto").is_visible():
                page.locator("text=Accetta tutto").click()
                print("[INFO] Cookie accettati.")
        except:
            pass

        #Gestione del CAPTCHA
        if page.locator("iframe[src*='recaptcha']").count() > 0:
            print("\n[INFO] CAPTCHA rilevato!")
            print("[PAUSA] Hai 30 secondi per risolverlo manualmente...")
            time.sleep(30)

        time.sleep(10)  #attesa extra per caricamento risultati

        links = page.locator("a:has(h3)")
        count = 0

        for i in range(links.count()):
            if count >= 10:
                break
            try:
                a_tag = links.nth(i)
                titolo = a_tag.locator("h3").inner_text()
                link = a_tag.get_attribute("href")
                if not link or not link.startswith("http"):
                    continue

                dominio = urlparse(link).netloc
                if dominio in domini_visti:
                    continue

                #Estrazione snippet
                snippet = ""
                parent = a_tag.locator("xpath=ancestor::div[contains(@class, 'tF2Cxc')]").first
                if parent.locator("div.VwiC3b").count() > 0:
                    snippet = parent.locator("div.VwiC3b").first.inner_text()
                elif parent.locator("div.IsZvec").count() > 0:
                    snippet = parent.locator("div.IsZvec").first.inner_text()
                elif parent.locator("div[data-sncf='1']").count() > 0:
                    snippet = parent.locator("div[data-sncf='1']").first.inner_text()

                risultati.append({
                    'titolo': titolo.strip(),
                    'link': link,
                    'snippet': snippet.strip()
                })
                domini_visti.add(dominio)
                count += 1
                time.sleep(1)

            except Exception as e:
                print(f"[WARNING] Errore durante l'analisi del risultato {i+1}: {e}")
                continue

        browser.close()
    return risultati
