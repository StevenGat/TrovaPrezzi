import re, requests, time, os, traceback
from collections import defaultdict
from flask import Flask, jsonify, send_from_directory, Response
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder="static")
CORS(app)

FARMACI = [
    {"id":"1","nome":"Dailyvit B12 flaconcini",     "qty":4, "url":"https://www.trovaprezzi.it/prezzo_integratori-coadiuvanti_984984308.aspx"},
    {"id":"2","nome":"Collirio Plus 10ml",           "qty":5, "url":"https://www.trovaprezzi.it/prezzo_prodotti-salute_984158865.aspx"},
    {"id":"3","nome":"Alfa Collirio Idratante 10ml", "qty":5, "url":"https://www.trovaprezzi.it/prezzo_prodotti-salute_987055872.aspx"},
    {"id":"4","nome":"Norsan 120 Arktis",            "qty":5, "url":"https://www.trovaprezzi.it/prezzo_integratori-coadiuvanti_981499054.aspx"},
    {"id":"5","nome":"Dailyvit Senior",              "qty":5, "url":"https://www.trovaprezzi.it/prezzo_integratori-coadiuvanti_930629934.aspx"},
    {"id":"6","nome":"Essaven Gel 80g",              "qty":1, "url":"https://www.trovaprezzi.it/prezzo_farmaci-da-banco_036193023.aspx"},
    {"id":"7","nome":"Aximagnesio 20 bustine",       "qty":2, "url":"https://www.trovaprezzi.it/prezzo_integratori-coadiuvanti_972069633.aspx"},
    {"id":"8","nome":"Fluimucil 600mg bustine",      "qty":1, "url":"https://www.trovaprezzi.it/prezzo_farmaci-da-banco_034936169.aspx"},
    {"id":"9","nome":"Apropos Vita+ Mag+Pot",        "qty":2, "url":"https://www.trovaprezzi.it/prezzo_integratori-coadiuvanti_979043116.aspx"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/146.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_cache, _cache_time, CACHE_TTL = {}, {}, 600

def float_da_testo(t):
    t = t.replace("Tot.", "").replace("+ Sped.", "").replace("Sped.", "").strip()
    m = re.search(r"(\d+)[.,](\d{2})\s*\u20ac|\u20ac\s*(\d+)[.,](\d{2})", t)
    if not m: return 0.0
    a, b = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    return float(f"{a}.{b}")

def scarica_offerte(url):
    offerte = []
    log_lines = []
    for page_url in [url, url + "?page=2"]:
        try:
            log_lines.append(f"GET {page_url}")
            r = requests.get(page_url, headers=HEADERS, timeout=20)
            log_lines.append(f"  HTTP {r.status_code}  len={len(r.text)}")
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.find_all("li", class_="listing_item")
            log_lines.append(f"  listing_item trovati: {len(items)}")
            if not items: break
            for item in items:
                s  = item.find("span", class_="merchant_name")
                p  = item.find("div",  class_="item_basic_price")
                sh = item.find("div",  class_="item_delivery_price")
                b  = item.find("a",    href=lambda h: h and "/goto" in h)
                if not s or not p: continue
                prezzo = float_da_testo(p.get_text())
                sped   = float_da_testo(sh.get_text()) if sh else 0.0
                if prezzo == 0: continue
                offerte.append({
                    "shop": s.get_text(strip=True), "prezzo": prezzo,
                    "sped": sped, "totale": round(prezzo + sped, 2),
                    "url": ("https://www.trovaprezzi.it" + b["href"]) if b else "",
                })
            time.sleep(1.0)
        except Exception as e:
            log_lines.append(f"  ERRORE: {e}")
    seen_set, unici = set(), []
    for o in offerte:
        k = o["shop"].lower()
        if k not in seen_set:
            seen_set.add(k); unici.append(o)
    return sorted(unici, key=lambda x: x["totale"])[:40], log_lines

def get_offerte(fid):
    now = time.time()
    if fid not in _cache or (now - _cache_time.get(fid, 0)) >= CACHE_TTL:
        f = next((x for x in FARMACI if x["id"] == fid), None)
        if not f: return []
        offerte, _ = scarica_offerte(f["url"])
        _cache[fid] = offerte; _cache_time[fid] = now
    return _cache[fid]

# ── ROUTE STATICHE ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# ── DEBUG endpoint (apri /debug dal browser per vedere tutto) ───────────────

@app.route("/debug")
def debug():
    lines = ["=== DEBUG FARMACI SERVER ===", f"Ora: {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"Python: {os.popen('python3 --version').read().strip()}",""]
    # Test connettivita Trovaprezzi
    lines.append("--- TEST CONNETTIVITA TROVAPREZZI ---")
    test_url = FARMACI[8]["url"]  # Apropos (quello che hai gia testato)
    try:
        r = requests.get(test_url, headers=HEADERS, timeout=20)
        lines.append(f"URL: {test_url}")
        lines.append(f"HTTP Status: {r.status_code}")
        lines.append(f"Dimensione risposta: {len(r.text)} caratteri")
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.find_all("li", class_="listing_item")
        lines.append(f"listing_item trovati: {len(items)}")
        if items:
            s = items[0].find("span", class_="merchant_name")
            p = items[0].find("div",  class_="item_basic_price")
            lines.append(f"Primo shop: {s.get_text(strip=True) if s else 'N/A'}")
            lines.append(f"Primo prezzo: {p.get_text(strip=True) if p else 'N/A'}")
            lines.append("RISULTATO: OK - Scraping funziona!")
        else:
            lines.append("ATTENZIONE: Nessun listing_item trovato")
            lines.append("Possibile: IP bloccato da Trovaprezzi o struttura HTML cambiata")
            # Cerca altri elementi per diagnosi
            titolo = soup.find("title")
            lines.append(f"Titolo pagina: {titolo.get_text() if titolo else 'nessuno'}")
            iubenda = "iubenda" in r.text
            lines.append(f"Banner cookie iubenda: {iubenda}")
    except Exception as e:
        lines.append(f"ERRORE CONNESSIONE: {e}")
        lines.append(traceback.format_exc())
    lines.append("")
    lines.append("--- FARMACI CONFIGURATI ---")
    for f in FARMACI:
        lines.append(f"  [{f['id']}] {f['nome']}  qty={f['qty']}")
    lines.append("")
    lines.append("--- CACHE ---")
    lines.append(f"Elementi in cache: {len(_cache)}")
    for k, v in _cache.items():
        nome = next((f['nome'] for f in FARMACI if f['id']==k), k)
        lines.append(f"  [{k}] {nome}: {len(v)} offerte")
    return Response("\n".join(lines), mimetype="text/plain; charset=utf-8")

# ── API ─────────────────────────────────────────────────────────────────────

@app.route("/api/farmaci")
def api_farmaci():
    return jsonify([{"id":f["id"],"nome":f["nome"],"qty":f["qty"]} for f in FARMACI])

@app.route("/api/prezzi/<fid>")
def api_prezzi(fid):
    f = next((x for x in FARMACI if x["id"] == fid), None)
    if not f: return jsonify({"error":"non trovato"}), 404
    return jsonify({"farmaco":f["nome"],"qty":f["qty"],"offerte":get_offerte(fid)})

@app.route("/api/confronto")
def api_confronto():
    farmacie = defaultdict(lambda:{"totale":0.0,"trovati":0,"dettaglio":[]})
    for f in FARMACI:
        for o in get_offerte(f["id"]):
            farmacie[o["shop"]]["trovati"] += 1
            farmacie[o["shop"]]["totale"]  += round(o["totale"] * f["qty"], 2)
            farmacie[o["shop"]]["dettaglio"].append({
                "farmaco":f["nome"],"qty":f["qty"],"prezzo":o["prezzo"],
                "sped":o["sped"],"totale_qty":round(o["totale"]*f["qty"],2)})
    result = sorted([
        {"shop":k,"trovati":v["trovati"],"totale":round(v["totale"],2),"dettaglio":v["dettaglio"]}
        for k,v in farmacie.items()], key=lambda x:(-x["trovati"],x["totale"]))
    return jsonify(result)

@app.route("/ping")
def ping(): return jsonify({"status":"ok","farmaci":len(FARMACI)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
